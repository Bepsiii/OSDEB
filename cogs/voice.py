import discord
from discord.ext import commands
import asyncio

class Voice(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.target_user_id = None  # Initialize target user ID
        self.voice_client = None  # Store the voice client
        self.check_speaking_task = None  # Task to check if the user is speaking

    @commands.command(name='settarget', help='Set the target user to interrupt when they join a voice channel')
    async def set_target(self, ctx, target: discord.Member):
        """Set the target user to interrupt."""
        self.target_user_id = target.id
        await ctx.send(f"Target user set to {target.display_name}")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        # Check if the target user joined a voice channel
        if member.id == self.target_user_id:
            if before.channel is None and after.channel is not None:
                # Get the voice channel the target user joined
                voice_channel = after.channel

                # Connect to the voice channel
                self.voice_client = await voice_channel.connect()

                # Start the task to check if the user is speaking
                self.check_speaking_task = self.bot.loop.create_task(self.check_if_speaking(member))

            elif before.channel is not None and after.channel is None:
                # Disconnect if the target user leaves the voice channel
                if self.voice_client:
                    await self.voice_client.disconnect()
                    self.voice_client = None

                # Cancel the task to check if the user is speaking
                if self.check_speaking_task:
                    self.check_speaking_task.cancel()
                    self.check_speaking_task = None

    async def check_if_speaking(self, member: discord.Member):
        """Check if the user is speaking and play the audio if they are."""
        while self.voice_client and self.voice_client.is_connected():
            voice_state = member.guild.voice_client
            if voice_state and voice_state.channel and member in voice_state.channel.members:
                if not member.voice.self_mute and not member.voice.self_deaf and member.voice.channel:
                    if not self.voice_client.is_playing():
                        # Play the intro audio file (make sure the file exists)
                        audio_source = discord.FFmpegPCMAudio('./music/intro.mp3')
                        self.voice_client.play(audio_source)
            await asyncio.sleep(1)  # Check every second

# Async setup function to add the cog
async def setup(bot: commands.Bot):
    await bot.add_cog(Voice(bot))