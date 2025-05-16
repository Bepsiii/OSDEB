# cogs/music.py
"""
A cog for playing music in voice channels using yt-dlp and FFmpeg.
Supports queueing, playlists, skipping, looping, and more.
"""
import discord
from discord.ext import commands, tasks
import yt_dlp
import asyncio
import os
import logging
from typing import Dict, List, Optional, Any, Union
import functools

# Assuming your config.py is in the parent directory or accessible via your Python path
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config # Now it should find config.py

# --- Logger Setup ---
logger = logging.getLogger(__name__)

# --- Helper Classes ---
class Song:
    """Represents a song with its metadata."""
    def __init__(self, source_url: str, webpage_url: str, title: str, duration: int,
                 thumbnail: Optional[str] = None, requester: Optional[discord.Member] = None):
        self.source_url = source_url # Direct stream URL
        self.webpage_url = webpage_url # Original URL (e.g., YouTube page)
        self.title = title
        self.duration_seconds = duration
        self.thumbnail_url = thumbnail
        self.requester = requester

    @property
    def formatted_duration(self) -> str:
        """Returns duration in HH:MM:SS or MM:SS format."""
        if self.duration_seconds is None: return "N/A"
        minutes, seconds = divmod(self.duration_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

class GuildMusicState:
    """Manages music state for a specific guild."""
    def __init__(self, bot_loop: asyncio.AbstractEventLoop, guild_id: int):
        self.bot_loop = bot_loop
        self.guild_id = guild_id
        self.queue: asyncio.Queue[Song] = asyncio.Queue(maxsize=getattr(config, 'MUSIC_MAX_QUEUE_LENGTH', 50))
        self.current_song: Optional[Song] = None
        self.voice_client: Optional[discord.VoiceClient] = None
        self.text_channel: Optional[discord.TextChannel] = None # Channel for bot messages
        self.now_playing_message: Optional[discord.Message] = None
        self.is_looping_song: bool = False
        self.is_looping_queue: bool = False # Future: loop queue
        self.volume: float = getattr(config, 'MUSIC_DEFAULT_VOLUME', 0.5) # Volume between 0.0 and 2.0
        self.idle_disconnect_task: Optional[asyncio.Task] = None
        self.ytdl = yt_dlp.YoutubeDL(getattr(config, 'MUSIC_YTDL_OPTIONS', {})) # Each guild can have its own instance if needed

    def is_playing(self) -> bool:
        return self.voice_client is not None and self.voice_client.is_playing()

    async def clear_queue(self):
        # Draining an asyncio.Queue
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
                self.queue.task_done() # Important for join()
            except asyncio.QueueEmpty:
                break
        logger.info(f"Guild {self.guild_id}: Queue cleared.")

    async def cleanup(self):
        """Cleans up resources for this guild's music state."""
        logger.info(f"Guild {self.guild_id}: Cleaning up music state.")
        await self.clear_queue()
        self.current_song = None
        if self.voice_client and self.voice_client.is_connected():
            await self.voice_client.disconnect(force=True)
            logger.info(f"Guild {self.guild_id}: Disconnected voice client.")
        self.voice_client = None
        if self.idle_disconnect_task and not self.idle_disconnect_task.done():
            self.idle_disconnect_task.cancel()
            logger.info(f"Guild {self.guild_id}: Cancelled idle disconnect task.")
        self.idle_disconnect_task = None
        if self.now_playing_message:
            try:
                await self.now_playing_message.delete()
                logger.debug(f"Guild {self.guild_id}: Deleted 'Now Playing' message.")
            except discord.HTTPException:
                pass # Message might already be deleted
        self.now_playing_message = None


class MusicV2(commands.Cog, name="Music"): # Explicitly named for help command
    """Plays music from various sources like YouTube and SoundCloud."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.guild_states: Dict[int, GuildMusicState] = {}
        # Global YTDL instance if options are always the same, or per-guild as in GuildMusicState
        # self.ytdl = yt_dlp.YoutubeDL(getattr(config, 'MUSIC_YTDL_OPTIONS', {}))
        self.ffmpeg_options = getattr(config, 'MUSIC_FFMPEG_OPTIONS', {'options': '-vn -b:a 128k'})
        self.ffmpeg_before_options = getattr(config, 'MUSIC_FFMPEG_BEFORE_OPTIONS', {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'})
        self.intro_sound_path = getattr(config, 'MUSIC_INTRO_PATH', None)
        logger.info("Music Cog loaded.")

    def _get_guild_state(self, guild_id: int) -> GuildMusicState:
        """Retrieves or creates the music state for a guild."""
        if guild_id not in self.guild_states:
            logger.info(f"Creating new GuildMusicState for guild ID {guild_id}")
            self.guild_states[guild_id] = GuildMusicState(self.bot.loop, guild_id)
        return self.guild_states[guild_id]

    async def _ensure_voice_channel(self, ctx: commands.Context) -> bool:
        """Checks if the bot and user are in a suitable voice channel."""
        guild_state = self._get_guild_state(ctx.guild.id)

        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send(getattr(config, 'MUSIC_MSG_USER_NOT_IN_VC', "❌ You need to be in a voice channel to use this command!"))
            return False

        if guild_state.voice_client is None or not guild_state.voice_client.is_connected():
            try:
                guild_state.voice_client = await ctx.author.voice.channel.connect(timeout=getattr(config, 'MUSIC_VC_CONNECT_TIMEOUT', 10.0))
                guild_state.text_channel = ctx.channel # Store channel for notifications
                logger.info(f"Guild {ctx.guild.id}: Connected to voice channel '{ctx.author.voice.channel.name}'.")
                await self._play_intro_if_available(ctx)
            except asyncio.TimeoutError:
                await ctx.send(getattr(config, 'MUSIC_MSG_VC_CONNECT_TIMEOUT', "❌ Timed out trying to connect to the voice channel."))
                return False
            except Exception as e:
                await ctx.send(getattr(config, 'MUSIC_MSG_VC_CONNECT_FAIL', f"❌ Could not connect to voice channel: {e}"))
                logger.error(f"Guild {ctx.guild.id}: Failed to connect to VC: {e}", exc_info=True)
                return False
        elif guild_state.voice_client.channel != ctx.author.voice.channel:
            await ctx.send(getattr(config, 'MUSIC_MSG_BOT_IN_DIFFERENT_VC', "❌ I'm already in another voice channel!"))
            return False
        
        # Set volume on voice client if it exists and is connected
        if guild_state.voice_client and guild_state.voice_client.source:
            guild_state.voice_client.source.volume = guild_state.volume

        return True

    async def _play_intro_if_available(self, ctx: commands.Context):
        """Plays an intro sound if configured and available."""
        guild_state = self._get_guild_state(ctx.guild.id)
        if self.intro_sound_path and os.path.exists(self.intro_sound_path) and guild_state.voice_client:
            if guild_state.voice_client.is_playing(): # Don't interrupt if already playing something (e.g. on reconnect)
                return
            try:
                intro_source = discord.FFmpegOpusAudio(self.intro_sound_path, **self.ffmpeg_options)
                guild_state.voice_client.play(intro_source)
                logger.info(f"Guild {ctx.guild.id}: Playing intro sound from '{self.intro_sound_path}'.")
                # Wait for intro to finish before playing next song. This might need adjustment.
                # For now, we assume play_next_song will handle queue correctly.
            except Exception as e:
                logger.error(f"Guild {ctx.guild.id}: Failed to play intro sound: {e}", exc_info=True)


    async def _search_and_extract_song_info(self, query: str, guild_state: GuildMusicState, requester: discord.Member) -> Union[Song, List[Song], None]:
        """Searches for a song/playlist and extracts its information using yt-dlp."""
        try:
            # Run yt-dlp in an executor to avoid blocking the event loop
            partial_extract_info = functools.partial(guild_state.ytdl.extract_info, query, download=False)
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, partial_extract_info)
        except yt_dlp.utils.DownloadError as e:
            logger.warning(f"Guild {guild_state.guild_id}: yt-dlp DownloadError for query '{query}': {e}")
            # Check for common error messages
            if "is not available" in str(e) or "Video unavailable" in str(e):
                raise commands.CommandError(getattr(config, 'MUSIC_MSG_SONG_UNAVAILABLE', "❌ This song is unavailable or private."))
            elif "Unsupported URL" in str(e):
                raise commands.CommandError(getattr(config, 'MUSIC_MSG_UNSUPPORTED_URL', "❌ This URL is not supported."))
            else:
                raise commands.CommandError(getattr(config, 'MUSIC_MSG_YTDL_GENERIC_ERROR', f"❌ Error fetching song: {e}"))
        except Exception as e:
            logger.error(f"Guild {guild_state.guild_id}: Unexpected error during YTDL extraction for '{query}': {e}", exc_info=True)
            raise commands.CommandError(getattr(config, 'MUSIC_MSG_YTDL_UNEXPECTED_ERROR', "❌ An unexpected error occurred while searching for the song."))


        if not info:
            logger.warning(f"Guild {guild_state.guild_id}: No info found for query '{query}'.")
            return None

        songs_to_add = []
        if 'entries' in info:  # Playlist
            if not getattr(config, 'MUSIC_ALLOW_PLAYLISTS', True):
                raise commands.CommandError(getattr(config, 'MUSIC_MSG_PLAYLISTS_DISABLED', "❌ Playlists are currently disabled."))
            
            max_playlist_length = getattr(config, 'MUSIC_MAX_PLAYLIST_LENGTH', 25)
            entries_to_process = info['entries'][:max_playlist_length]
            
            for entry in entries_to_process:
                if not entry: continue
                song = Song(
                    source_url=entry.get('url'), # This is often the direct stream URL for each playlist item
                    webpage_url=entry.get('webpage_url', query),
                    title=entry.get('title', 'Unknown Title'),
                    duration=entry.get('duration'),
                    thumbnail=entry.get('thumbnail'),
                    requester=requester
                )
                songs_to_add.append(song)
            if not songs_to_add: return None
            return songs_to_add
        else:  # Single track
            # Check duration limit for single songs
            max_duration = getattr(config, 'MUSIC_MAX_SONG_DURATION_SECONDS', 600) # Default 10 mins
            if info.get('duration') and info['duration'] > max_duration:
                raise commands.CommandError(getattr(config, 'MUSIC_MSG_SONG_TOO_LONG', f"❌ Song is too long! Maximum duration is {max_duration // 60} minutes."))

            return Song(
                source_url=info.get('url'), # Direct stream URL
                webpage_url=info.get('webpage_url', query),
                title=info.get('title', 'Unknown Title'),
                duration=info.get('duration'),
                thumbnail=info.get('thumbnail'),
                requester=requester
            )

    async def _add_to_queue(self, ctx: commands.Context, song_or_list: Union[Song, List[Song]]):
        """Adds a song or list of songs to the guild's queue."""
        guild_state = self._get_guild_state(ctx.guild.id)
        added_count = 0

        if isinstance(song_or_list, list): # Playlist
            for song in song_or_list:
                try:
                    guild_state.queue.put_nowait(song)
                    added_count += 1
                except asyncio.QueueFull:
                    await ctx.send(getattr(config, 'MUSIC_MSG_QUEUE_FULL_PLAYLIST', f"🎧 Added {added_count} songs from the playlist. Queue is full!").format(added_count=added_count))
                    logger.warning(f"Guild {ctx.guild.id}: Queue full while adding playlist.")
                    break
            if added_count > 0 and added_count == len(song_or_list):
                await ctx.send(getattr(config, 'MUSIC_MSG_PLAYLIST_ADDED', "🎧 Added **{count}** songs to the queue from the playlist!").format(count=added_count))
            elif added_count > 0: # Partial add due to queue full
                 pass # Message already sent
            else: # No songs added (e.g. empty playlist result)
                await ctx.send(getattr(config, 'MUSIC_MSG_PLAYLIST_EMPTY_OR_FAILED', "❓ Couldn't add any songs from the playlist."))

        else: # Single song
            song = song_or_list
            try:
                guild_state.queue.put_nowait(song)
                await ctx.send(getattr(config, 'MUSIC_MSG_SONG_ADDED', "🎧 Added to queue: **{title}** ({duration})").format(title=song.title, duration=song.formatted_duration))
                added_count = 1
            except asyncio.QueueFull:
                await ctx.send(getattr(config, 'MUSIC_MSG_QUEUE_FULL_SINGLE', "❌ Queue is full! Cannot add **{title}**.").format(title=song.title))
                logger.warning(f"Guild {ctx.guild.id}: Queue full when adding single song '{song.title}'.")
        
        if added_count > 0 and not guild_state.is_playing():
            await self._play_next_song(ctx.guild.id)


    async def _play_next_song(self, guild_id: int):
        """Plays the next song in the queue for the given guild."""
        guild_state = self._get_guild_state(guild_id)

        if guild_state.is_playing(): # Should not happen if called correctly from `after_callback`
            logger.warning(f"Guild {guild_id}: _play_next_song called while already playing.")
            return

        if guild_state.idle_disconnect_task: # Cancel previous idle task
            guild_state.idle_disconnect_task.cancel()
            guild_state.idle_disconnect_task = None

        song_to_play: Optional[Song] = None

        if guild_state.is_looping_song and guild_state.current_song:
            song_to_play = guild_state.current_song # Replay current song
        else:
            if guild_state.queue.empty():
                guild_state.current_song = None
                if guild_state.text_channel: # Check if text_channel is set
                    await guild_state.text_channel.send(getattr(config, 'MUSIC_MSG_QUEUE_EMPTY_DISCONNECT', "⏹ Queue finished. I'll leave the voice channel shortly if I'm idle."))
                logger.info(f"Guild {guild_id}: Queue is empty.")
                # Start idle disconnect task
                idle_timeout = getattr(config, 'MUSIC_IDLE_DISCONNECT_SECONDS', 300)
                guild_state.idle_disconnect_task = self.bot.loop.create_task(self._auto_disconnect_if_idle(guild_id, idle_timeout))
                return
            
            song_to_play = await guild_state.queue.get()
            guild_state.queue.task_done()
            guild_state.current_song = song_to_play


        if not song_to_play or not guild_state.voice_client or not guild_state.voice_client.is_connected():
            logger.warning(f"Guild {guild_id}: Cannot play next song. No song, or VC not connected.")
            if guild_state.voice_client and not guild_state.voice_client.is_connected():
                 await guild_state.cleanup() # Attempt to clean up if VC died
            return

        try:
            # Re-fetch stream URL if it's not the direct source_url or if it might expire
            # For simplicity, we assume song.source_url is the direct stream_url from initial extraction
            if not song_to_play.source_url: # Fallback if direct URL wasn't populated
                logger.info(f"Guild {guild_id}: Re-extracting stream URL for '{song_to_play.title}' as source_url is missing.")
                info = await self.bot.loop.run_in_executor(None, lambda: guild_state.ytdl.extract_info(song_to_play.webpage_url, download=False))
                song_to_play.source_url = info.get('url') if info else None

            if not song_to_play.source_url:
                logger.error(f"Guild {guild_id}: Failed to get source URL for '{song_to_play.title}'. Skipping.")
                if guild_state.text_channel:
                    await guild_state.text_channel.send(getattr(config, 'MUSIC_MSG_STREAM_URL_FAIL', "❌ Could not get a playable link for **{title}**. Skipping.").format(title=song_to_play.title))
                self.bot.loop.create_task(self._play_next_song(guild_id)) # Try next one
                return

            audio_source = discord.FFmpegOpusAudio(song_to_play.source_url, **self.ffmpeg_before_options, **self.ffmpeg_options)
            transformed_source = discord.PCMVolumeTransformer(audio_source, volume=guild_state.volume)
            
            # Define the after_playing callback
            def after_playing_callback(error):
                if error:
                    logger.error(f"Guild {guild_id}: Player error for '{song_to_play.title}': {error}", exc_info=error)
                # Schedule _play_next_song to run in the bot's event loop
                self.bot.loop.create_task(self._play_next_song(guild_id))

            guild_state.voice_client.play(transformed_source, after=after_playing_callback)
            logger.info(f"Guild {guild_id}: Now playing '{song_to_play.title}'.")

            if guild_state.text_channel: # Send "Now Playing" message
                if guild_state.now_playing_message: # Delete old one
                    try: await guild_state.now_playing_message.delete()
                    except discord.HTTPException: pass
                
                embed = self._create_now_playing_embed(song_to_play, guild_state)
                guild_state.now_playing_message = await guild_state.text_channel.send(embed=embed)

        except Exception as e:
            logger.error(f"Guild {guild_id}: Error streaming song '{song_to_play.title}': {e}", exc_info=True)
            if guild_state.text_channel:
                await guild_state.text_channel.send(getattr(config, 'MUSIC_MSG_PLAYBACK_ERROR', "❌ An error occurred while trying to play **{title}**. Skipping.").format(title=song_to_play.title))
            self.bot.loop.create_task(self._play_next_song(guild_id)) # Try next song

    def _create_now_playing_embed(self, song: Song, guild_state: GuildMusicState) -> discord.Embed:
        """Helper to create the 'Now Playing' embed."""
        embed_color = getattr(config, 'MUSIC_NOW_PLAYING_EMBED_COLOR', discord.Color.blue())
        embed = discord.Embed(title=f"{getattr(config, 'MUSIC_EMOJI_PLAYING', '🎶')} Now Playing", description=f"**[{song.title}]({song.webpage_url})**", color=embed_color)
        if song.thumbnail_url:
            embed.set_thumbnail(url=song.thumbnail_url)
        if song.requester:
            embed.add_field(name="Requested by", value=song.requester.mention, inline=True)
        embed.add_field(name="Duration", value=song.formatted_duration, inline=True)
        embed.add_field(name="Volume", value=f"{int(guild_state.volume * 100)}%", inline=True)
        if guild_state.is_looping_song:
            embed.set_footer(text=f"{getattr(config, 'MUSIC_EMOJI_LOOP', '🔁')} Song loop is ON")
        return embed

    async def _auto_disconnect_if_idle(self, guild_id: int, timeout: int):
        """Task to automatically disconnect if the bot is idle in a voice channel."""
        await asyncio.sleep(timeout)
        guild_state = self._get_guild_state(guild_id)
        if guild_state.voice_client and guild_state.voice_client.is_connected() and not guild_state.is_playing() and guild_state.queue.empty():
            logger.info(f"Guild {guild_id}: Idle timeout reached. Disconnecting.")
            if guild_state.text_channel:
                await guild_state.text_channel.send(getattr(config, 'MUSIC_MSG_IDLE_DISCONNECTED', "👋 Disconnected due to inactivity."))
            await guild_state.cleanup() # Full cleanup
            if guild_id in self.guild_states: # Remove state if fully cleaned up
                del self.guild_states[guild_id]


    # --- Commands ---
    @commands.command(name="join", aliases=['connect'], help="Joins your current voice channel.")
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def join(self, ctx: commands.Context):
        if await self._ensure_voice_channel(ctx):
            await ctx.send(getattr(config, 'MUSIC_MSG_JOINED_VC', "👋 Joined **{channel_name}**!").format(channel_name=ctx.author.voice.channel.name))

    @commands.command(name="leave", aliases=['disconnect', 'dc'], help="Leaves the voice channel and clears the queue.")
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def leave(self, ctx: commands.Context):
        guild_state = self._get_guild_state(ctx.guild.id)
        if guild_state.voice_client and guild_state.voice_client.is_connected():
            await guild_state.cleanup()
            if ctx.guild.id in self.guild_states: # Remove state
                del self.guild_states[ctx.guild.id]
            await ctx.send(getattr(config, 'MUSIC_MSG_LEFT_VC', "👋 Left the voice channel and cleared the queue."))
        else:
            await ctx.send(getattr(config, 'MUSIC_MSG_NOT_IN_VC', "❌ I'm not currently in a voice channel."))

    @commands.command(name="play", aliases=['p'], help="Plays a song or adds it/playlist to the queue. Usage: !play <song name or URL>")
    @commands.cooldown(1, getattr(config, 'MUSIC_PLAY_COOLDOWN_SECONDS', 3), commands.BucketType.user)
    async def play(self, ctx: commands.Context, *, query: str):
        guild_state = self._get_guild_state(ctx.guild.id)
        guild_state.text_channel = ctx.channel # Ensure text channel is set for notifications

        if not await self._ensure_voice_channel(ctx):
            return

        async with ctx.typing(): # Show "Bot is typing..."
            try:
                song_or_list = await self._search_and_extract_song_info(query, guild_state, ctx.author)
            except commands.CommandError as e: # Catch errors from _search_and_extract_song_info
                await ctx.send(str(e))
                return
            except Exception as e: # Catch any other unexpected errors
                logger.error(f"Guild {ctx.guild.id}: Unexpected error in play command for query '{query}': {e}", exc_info=True)
                await ctx.send(getattr(config, 'MUSIC_MSG_PLAY_CMD_UNEXPECTED_ERROR', "❌ An unexpected error occurred."))
                return

        if song_or_list:
            await self._add_to_queue(ctx, song_or_list)
        else:
            await ctx.send(getattr(config, 'MUSIC_MSG_NO_SONG_FOUND', "❓ Couldn't find anything for your query: `{query}`").format(query=query))


    @commands.command(name="skip", aliases=['s'], help="Skips the current song.")
    @commands.cooldown(1, getattr(config, 'MUSIC_SKIP_COOLDOWN_SECONDS', 2), commands.BucketType.guild)
    async def skip(self, ctx: commands.Context):
        guild_state = self._get_guild_state(ctx.guild.id)
        if not guild_state.voice_client or not guild_state.voice_client.is_connected():
            return await ctx.send(getattr(config, 'MUSIC_MSG_NOT_PLAYING_SKIP', "❌ I'm not playing anything to skip!"))
        if not guild_state.current_song:
             return await ctx.send(getattr(config, 'MUSIC_MSG_NOTHING_TO_SKIP', "❌ There's nothing to skip!"))


        # Vote skip logic could be added here
        guild_state.is_looping_song = False # Turn off loop if skipping
        guild_state.voice_client.stop() # This will trigger the `after_playing_callback`
        await ctx.send(getattr(config, 'MUSIC_MSG_SONG_SKIPPED', "⏭ Skipped **{title}**.").format(title=guild_state.current_song.title))
        logger.info(f"Guild {ctx.guild.id}: Song '{guild_state.current_song.title}' skipped by {ctx.author.name}.")
        # _play_next_song will be called by the `after` callback of the stopped song.

    @commands.command(name="stop", help="Stops playback, clears queue, and leaves the voice channel.")
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def stop(self, ctx: commands.Context):
        guild_state = self._get_guild_state(ctx.guild.id)
        if guild_state.voice_client:
            await guild_state.cleanup()
            if ctx.guild.id in self.guild_states: # Remove state
                del self.guild_states[ctx.guild.id]
            await ctx.send(getattr(config, 'MUSIC_MSG_PLAYER_STOPPED', "⏹ Playback stopped, queue cleared, and I've left the voice channel."))
            logger.info(f"Guild {ctx.guild.id}: Player stopped and cleaned up by {ctx.author.name}.")
        else:
            await ctx.send(getattr(config, 'MUSIC_MSG_NOT_IN_VC_STOP', "❌ I'm not in a voice channel to stop!"))


    @commands.command(name="queue", aliases=['q', 'playlist'], help="Shows the current song queue.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def queue_command(self, ctx: commands.Context): # Renamed to avoid conflict with queue attribute
        guild_state = self._get_guild_state(ctx.guild.id)
        
        if not guild_state.current_song and guild_state.queue.empty():
            return await ctx.send(getattr(config, 'MUSIC_MSG_QUEUE_IS_EMPTY', "텅 빈 대기열 (The queue is empty!)"))

        embed_color = getattr(config, 'MUSIC_QUEUE_EMBED_COLOR', discord.Color.purple())
        embed = discord.Embed(title=f"{getattr(config, 'MUSIC_EMOJI_QUEUE', '📜')} Music Queue", color=embed_color)

        if guild_state.current_song:
            cs_text = f"**[{guild_state.current_song.title}]({guild_state.current_song.webpage_url})**\n" \
                      f"Duration: {guild_state.current_song.formatted_duration} | Requested by: {guild_state.current_song.requester.mention if guild_state.current_song.requester else 'Unknown'}"
            embed.add_field(name=f"{getattr(config, 'MUSIC_EMOJI_PLAYING', '🎶')} Now Playing", value=cs_text, inline=False)

        if not guild_state.queue.empty():
            queue_list_str = []
            # Accessing items in asyncio.Queue directly is tricky for display. We convert to list for display.
            temp_queue_list = list(guild_state.queue._queue)[:getattr(config, 'MUSIC_QUEUE_DISPLAY_LIMIT', 10)]

            for i, song in enumerate(temp_queue_list):
                queue_list_str.append(f"`{i + 1}.` **[{song.title}]({song.webpage_url})** ({song.formatted_duration}) - Req: {song.requester.mention if song.requester else 'Unknown'}")
            
            if queue_list_str:
                embed.add_field(name="Up Next", value="\n".join(queue_list_str), inline=False)
            
            if guild_state.queue.qsize() > len(temp_queue_list):
                embed.set_footer(text=f"...and {guild_state.queue.qsize() - len(temp_queue_list)} more song(s).")
        
        await ctx.send(embed=embed)

    @commands.command(name="nowplaying", aliases=['np', 'current'], help="Shows the currently playing song.")
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def nowplaying(self, ctx: commands.Context):
        guild_state = self._get_guild_state(ctx.guild.id)
        if guild_state.current_song and guild_state.is_playing():
            embed = self._create_now_playing_embed(guild_state.current_song, guild_state)
            await ctx.send(embed=embed)
        else:
            await ctx.send(getattr(config, 'MUSIC_MSG_NOTHING_PLAYING', "❌ Nothing is currently playing."))


    @commands.command(name="loop", help="Toggles looping for the current song.")
    @commands.cooldown(1, 2, commands.BucketType.guild)
    async def loop(self, ctx: commands.Context):
        guild_state = self._get_guild_state(ctx.guild.id)
        if not guild_state.current_song:
            return await ctx.send(getattr(config, 'MUSIC_MSG_LOOP_NO_SONG', "❌ There's no song currently playing to loop."))

        guild_state.is_looping_song = not guild_state.is_looping_song
        status_msg = getattr(config, 'MUSIC_MSG_LOOP_ENABLED', "🔁 Song loop **enabled** for **{title}**.") if guild_state.is_looping_song \
            else getattr(config, 'MUSIC_MSG_LOOP_DISABLED', "🔁 Song loop **disabled**.")
        await ctx.send(status_msg.format(title=guild_state.current_song.title))
        logger.info(f"Guild {ctx.guild.id}: Song loop set to {guild_state.is_looping_song} by {ctx.author.name}.")

    @commands.command(name="remove", aliases=['rm'], help="Removes a song from the queue by its position. Usage: !remove <number>")
    @commands.cooldown(1, 2, commands.BucketType.user)
    async def remove(self, ctx: commands.Context, position: int):
        guild_state = self._get_guild_state(ctx.guild.id)
        if guild_state.queue.empty():
            return await ctx.send(getattr(config, 'MUSIC_MSG_QUEUE_EMPTY_REMOVE', "❌ The queue is empty, nothing to remove."))
        if position <= 0:
            return await ctx.send(getattr(config, 'MUSIC_MSG_REMOVE_INVALID_POS_TOO_LOW', "❌ Invalid position. Please use a number greater than 0."))

        # To remove from asyncio.Queue by index, we have to reconstruct it (or part of it)
        temp_list = []
        removed_song: Optional[Song] = None
        
        # Drain the queue into a temporary list
        while not guild_state.queue.empty():
            temp_list.append(await guild_state.queue.get())
            guild_state.queue.task_done()

        if position > len(temp_list):
             # Re-add items to queue
            for item in temp_list: await guild_state.queue.put(item)
            return await ctx.send(getattr(config, 'MUSIC_MSG_REMOVE_INVALID_POS_TOO_HIGH', "❌ Invalid position. Number is too high for the current queue size."))

        removed_song = temp_list.pop(position - 1) # Adjust for 0-based index

        # Re-add items to queue
        for item in temp_list:
            try:
                guild_state.queue.put_nowait(item)
            except asyncio.QueueFull: # Should not happen if maxsize is reasonable
                logger.error(f"Guild {ctx.guild.id}: Queue became full unexpectedly during remove operation.")
                break 
        
        if removed_song:
            await ctx.send(getattr(config, 'MUSIC_MSG_SONG_REMOVED', "🗑 Removed **{title}** from the queue.").format(title=removed_song.title))
            logger.info(f"Guild {ctx.guild.id}: Song '{removed_song.title}' removed by {ctx.author.name}.")
        else: # Should not happen if position validation is correct
            await ctx.send(getattr(config, 'MUSIC_MSG_REMOVE_FAIL', "❓ Could not remove song at that position."))


    @commands.command(name="volume", aliases=['vol'], help="Sets the player volume (0-200). Usage: !volume <number>")
    @commands.cooldown(1, 2, commands.BucketType.user)
    async def volume(self, ctx: commands.Context, volume_percent: int):
        guild_state = self._get_guild_state(ctx.guild.id)
        min_vol = getattr(config, 'MUSIC_VOLUME_MIN', 0)
        max_vol = getattr(config, 'MUSIC_VOLUME_MAX', 200)

        if not (min_vol <= volume_percent <= max_vol):
            return await ctx.send(getattr(config, 'MUSIC_MSG_VOLUME_OUT_OF_RANGE', "❌ Volume must be between {min_vol}% and {max_vol}%.").format(min_vol=min_vol, max_vol=max_vol))

        guild_state.volume = volume_percent / 100.0
        if guild_state.voice_client and guild_state.voice_client.source:
            guild_state.voice_client.source.volume = guild_state.volume
        
        await ctx.send(getattr(config, 'MUSIC_MSG_VOLUME_SET', "{emoji_volume} Volume set to **{volume}%**.").format(emoji_volume=getattr(config, 'MUSIC_EMOJI_VOLUME', '🔊'), volume=volume_percent))
        logger.info(f"Guild {ctx.guild.id}: Volume set to {volume_percent}% by {ctx.author.name}.")


    # --- Utility for other cogs/presence ---
    def get_current_song_details(self, guild_id: int) -> Optional[Song]:
        """Returns the Song object of the currently playing song, or None."""
        if guild_id in self.guild_states:
            return self.guild_states[guild_id].current_song
        return None

    # --- Cog Listeners ---
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Listener for voice state changes, e.g., bot disconnected by admin."""
        if member.id == self.bot.user.id and before.channel is not None and after.channel is None:
            # Bot was disconnected from a voice channel
            guild_id = before.channel.guild.id
            guild_state = self._get_guild_state(guild_id)
            logger.info(f"Guild {guild_id}: Bot was disconnected from voice channel '{before.channel.name}'. Cleaning up.")
            await guild_state.cleanup()
            if guild_id in self.guild_states: # Remove state
                del self.guild_states[guild_id]

    # --- Error Handling for Music Commands ---
    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """Generic error handler for music cog commands."""
        if isinstance(error, commands.CommandNotFound):
            return # Let main bot handler deal with this or ignore
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(getattr(config, 'MUSIC_MSG_MISSING_ARG', "❌ You're missing an argument: `{argument}`. Check `!help {command}`.").format(argument=error.param.name, command=ctx.command.qualified_name))
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(getattr(config, 'MUSIC_MSG_COOLDOWN', "⏳ This command is on cooldown. Please try again in **{cooldown:.2f}s**.").format(cooldown=error.retry_after))
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send(getattr(config, 'MUSIC_MSG_GUILD_ONLY', "🎶 Music commands only work in servers, not DMs."))
        elif isinstance(error, commands.CheckFailure): # Generic check failure
             await ctx.send(getattr(config, 'MUSIC_MSG_CHECK_FAILURE', "🚫 You don't have permission to use this command or a check failed."))
        elif isinstance(error, commands.CommandError): # Catch specific CommandErrors raised within commands
            await ctx.send(str(error)) # Send the custom message from the raised error
        else:
            logger.error(f"Unhandled error in music command '{ctx.command.qualified_name}': {error}", exc_info=True)
            await ctx.send(getattr(config, 'MUSIC_MSG_UNEXPECTED_CMD_ERROR', "❗ An unexpected error occurred with that music command."))


async def setup(bot: commands.Bot):
    """Sets up the MusicV2 cog."""
    # Ensure necessary directories/files from config exist if needed
    intro_path = getattr(config, 'MUSIC_INTRO_PATH', None)
    if intro_path and not os.path.exists(intro_path):
        logger.warning(f"Music intro sound file not found at configured path: {intro_path}")
    
    cookie_file = getattr(config, 'MUSIC_YTDL_OPTIONS', {}).get('cookiefile')
    if cookie_file and not os.path.exists(cookie_file):
         logger.warning(f"YTDL cookie file not found at: {cookie_file}")

    ffmpeg_executable = getattr(config, 'MUSIC_FFMPEG_EXECUTABLE_PATH', None)
    if ffmpeg_executable: # If user specified a path, ensure discord.py uses it
        # This is a global setting for discord.py's FFmpegPCMAudio/OpusAudio
        # It's tricky to set per-cog if multiple cogs use FFmpeg differently.
        # For now, assume it's either in PATH or this global is fine.
        # discord.opus.FFMPEG_PATH = ffmpeg_executable # This was for older discord.py
        # For modern discord.py, FFmpegOpusAudio takes `executable` kwarg.
        # We'd need to pass this to FFmpegOpusAudio if set.
        # The current structure passes **self.ffmpeg_options which could include `executable`.
        logger.info(f"Music cog will attempt to use FFmpeg executable: {ffmpeg_executable} if provided in FFMPEG_OPTIONS.")


    await bot.add_cog(MusicV2(bot))
    logger.info("MusicV2 cog has been setup and added to the bot.")

