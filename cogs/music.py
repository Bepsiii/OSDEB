import discord
from discord.ext import commands
from discord import FFmpegOpusAudio
import yt_dlp as youtube_dl
import asyncio
import os
from typing import Dict, List, Optional

# Constants
INTRO_PATH = "./music/intro.mp3"
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'cookiefile': 'cookies.txt'  # Optional cookie file for restricted content
}

class Song:
    def __init__(self, title: str, url: str, source_url: str):
        self.title = title
        self.url = url
        self.source_url = source_url

class GuildMusicState:
    def __init__(self):
        self.queue: List[Song] = []
        self.current_song: Optional[Song] = None
        self.loop = False

class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.guild_states: Dict[int, GuildMusicState] = {}
        self.ydl = youtube_dl.YoutubeDL(YTDL_OPTIONS)

    def get_guild_state(self, guild_id: int) -> GuildMusicState:
        if guild_id not in self.guild_states:
            self.guild_states[guild_id] = GuildMusicState()
        return self.guild_states[guild_id]

    async def play_intro(self, ctx: commands.Context):
        """Play intro music if available"""
        if os.path.exists(INTRO_PATH):
            vc = ctx.voice_client
            intro_source = FFmpegOpusAudio(INTRO_PATH)
            vc.play(intro_source, after=lambda e: None)
            await ctx.send("🎵 Playing intro...")
            while vc.is_playing():
                await asyncio.sleep(0.1)

    async def stream_song(self, ctx: commands.Context, song: Song):
        """Stream audio directly from URL"""
        guild_state = self.get_guild_state(ctx.guild.id)

        # Extract direct stream URL using yt-dlp
        try:
            info = self.ydl.extract_info(song.url, download=False)
            if 'entries' in info:
                info = info['entries'][0]
            song.source_url = info['url']
        except Exception as e:
            await ctx.send(f"❌ Error extracting stream URL: {e}")
            return

        ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn -b:a 128k'
        }

        source = FFmpegOpusAudio(
            song.source_url,
            **ffmpeg_options
        )

        def after_playing(error):
            if error:
                print(f'Player error: {error}')
            asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop)

        ctx.voice_client.play(source, after=after_playing)
        guild_state.current_song = song
        await ctx.send(f"🎶 Now playing: **{song.title}**")

    async def play_next(self, ctx: commands.Context):
        """Play next song in queue"""
        guild_state = self.get_guild_state(ctx.guild.id)

        if guild_state.loop and guild_state.current_song:
            await self.stream_song(ctx, guild_state.current_song)
            return

        if guild_state.queue:
            next_song = guild_state.queue.pop(0)
            await self.stream_song(ctx, next_song)
        else:
            guild_state.current_song = None
            await ctx.voice_client.disconnect()
            await ctx.send("⏹ Queue finished. Disconnecting...")

    @commands.command()
    async def play(self, ctx: commands.Context, *, query: str):
        """Play music from YouTube or SoundCloud"""
        if not ctx.author.voice:
            return await ctx.send("❌ You need to be in a voice channel!")

        try:
            info = self.ydl.extract_info(query, download=False)
            if 'entries' in info:  # Playlist
                entries = info['entries']
                for entry in entries:
                    song = Song(
                        title=entry.get('title', 'Unknown Title'),
                        url=entry['webpage_url'],
                        source_url=entry['url']
                    )
                    self.get_guild_state(ctx.guild.id).queue.append(song)
                await ctx.send(f"🎧 Added {len(entries)} songs to queue")
            else:  # Single track
                song = Song(
                    title=info.get('title', 'Unknown Title'),
                    url=info['webpage_url'],
                    source_url=info['url']
                )
                self.get_guild_state(ctx.guild.id).queue.append(song)
                await ctx.send(f"🎧 Added to queue: **{song.title}**")
        except Exception as e:
            return await ctx.send(f"❌ Error: {str(e)}")

        if not ctx.voice_client:
            vc = await ctx.author.voice.channel.connect()
            await self.play_intro(ctx)
            await self.play_next(ctx)

    @commands.command()
    async def skip(self, ctx: commands.Context):
        """Skip current song"""
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await ctx.send("⏭ Skipped current song")

    @commands.command()
    async def queue(self, ctx: commands.Context):
        """Show current queue"""
        guild_state = self.get_guild_state(ctx.guild.id)
        queue = guild_state.queue

        if not queue and not guild_state.current_song:
            return await ctx.send("❌ Queue is empty")

        embed = discord.Embed(title="Music Queue", color=0x00ff00)

        if guild_state.current_song:
            embed.add_field(
                name="Now Playing",
                value=f"🎶 **{guild_state.current_song.title}**",
                inline=False
            )

        if queue:
            queue_list = "\n".join(
                [f"{i+1}. {song.title}" for i, song in enumerate(queue[:10])]
            )
            embed.add_field(
                name="Up Next",
                value=queue_list,
                inline=False
            )

        await ctx.send(embed=embed)

    @commands.command()
    async def stop(self, ctx: commands.Context):
        """Stop music and clear queue"""
        guild_state = self.get_guild_state(ctx.guild.id)
        guild_state.queue.clear()

        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.send("⏹ Stopped player and cleared queue")

    @commands.command()
    async def loop(self, ctx: commands.Context):
        """Toggle loop current song"""
        guild_state = self.get_guild_state(ctx.guild.id)
        guild_state.loop = not guild_state.loop
        status = "🔁 Enabled" if guild_state.loop else "🔁 Disabled"
        await ctx.send(f"{status} song looping")

    @commands.command()
    async def remove(self, ctx: commands.Context, index: int):
        """Remove song from queue by position"""
        guild_state = self.get_guild_state(ctx.guild.id)
        try:
            removed = guild_state.queue.pop(index - 1)
            await ctx.send(f"❌ Removed: {removed.title}")
        except IndexError:
            await ctx.send("❌ Invalid queue position")

    def get_current_song(self, guild_id: int) -> Optional[str]:
        """Returns the title of the currently playing song, or None if nothing is playing."""
        guild_state = self.get_guild_state(guild_id)
        if guild_state.current_song:
            return guild_state.current_song.title
        return None

# Corrected setup function (make it async and await add_cog)
async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))