# cogs/voice.py
"""
A cog that allows setting a target user. When this user joins a voice channel,
the bot will join and play an interrupt sound when the target is unmuted.
"""
import discord
from discord.ext import commands, tasks
import asyncio
import os
import logging
from typing import Optional # <--- IMPORT ENSURED HERE

# Assuming your config.py is in the parent directory or accessible via your Python path
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

# --- Logger Setup ---
logger = logging.getLogger(__name__)

class VoiceInterruptCog(commands.Cog, name="VoiceInterrupt"):
    """Cog for voice channel interruptions based on a target user."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.target_user_id: Optional[int] = None
        self.target_guild_id: Optional[int] = None 
        self.interrupt_voice_client: Optional[discord.VoiceClient] = None
        self.check_interrupt_task: Optional[asyncio.Task] = None
        self.interrupt_sound_path: str = getattr(config, 'VOICE_INTERRUPT_SOUND_PATH', './sounds/interrupt.mp3')
        self.ffmpeg_options: dict = getattr(config, 'VOICE_INTERRUPT_FFMPEG_OPTIONS', {'options': '-vn'})
        
        sound_dir = os.path.dirname(self.interrupt_sound_path)
        if sound_dir and not os.path.exists(sound_dir):
            try:
                os.makedirs(sound_dir, exist_ok=True)
                logger.info(f"Created directory for interrupt sound: {sound_dir}")
            except OSError as e:
                logger.error(f"Could not create directory {sound_dir} for interrupt sound: {e}")

        if not os.path.exists(self.interrupt_sound_path):
            logger.warning(
                f"Interrupt sound file not found at configured path: {self.interrupt_sound_path}. "
                "The interrupt feature will not play sound."
            )

    @commands.command(name='setinterrupttarget', aliases=['settarget'], help='Sets a target user to be interrupted.')
    @commands.has_permissions(manage_guild=getattr(config, 'VOICE_SET_TARGET_ADMIN_ONLY', True)) 
    @commands.cooldown(1, getattr(config, 'VOICE_SET_TARGET_COOLDOWN', 10), commands.BucketType.guild)
    async def set_target_user(self, ctx: commands.Context, target: discord.Member):
        """Sets the target user for voice interruptions in the current guild."""
        
        # Clear any existing target and associated resources if target is changing or being set in a new guild
        if self.target_user_id is not None or self.target_guild_id is not None:
            if self.check_interrupt_task and not self.check_interrupt_task.done():
                self.check_interrupt_task.cancel()
                logger.info(f"Cancelled previous interrupt check task (guild: {self.target_guild_id}, target: {self.target_user_id}).")
            if self.interrupt_voice_client and self.interrupt_voice_client.is_connected():
                await self.interrupt_voice_client.disconnect(force=True)
                logger.info(f"Disconnected from previous voice channel (guild: {self.interrupt_voice_client.guild.id}).")
            self.interrupt_voice_client = None
            self.check_interrupt_task = None # Ensure task is cleared

        self.target_user_id = target.id
        self.target_guild_id = ctx.guild.id 

        success_msg = getattr(config, 'VOICE_MSG_TARGET_SET', "🎯 Target user for interruption set to **{target_name}** in this server.")
        await ctx.send(success_msg.format(target_name=target.display_name))
        logger.info(f"Interrupt target set to {target.name} ({target.id}) in guild {ctx.guild.id} by {ctx.author.name}.")

    @commands.command(name='clearinterrupttarget', help='Clears the interrupt target user.')
    @commands.has_permissions(manage_guild=getattr(config, 'VOICE_SET_TARGET_ADMIN_ONLY', True))
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def clear_target_user(self, ctx: commands.Context):
        """Clears the currently set target user for voice interruptions in this guild."""
        if self.target_user_id and self.target_guild_id == ctx.guild.id:
            old_target_id = self.target_user_id
            self.target_user_id = None
            # self.target_guild_id = None # Keep this to know which guild's target was cleared, or clear it for global effect
            
            if self.check_interrupt_task and not self.check_interrupt_task.done():
                self.check_interrupt_task.cancel()
            if self.interrupt_voice_client and self.interrupt_voice_client.is_connected() and self.interrupt_voice_client.guild.id == ctx.guild.id:
                await self.interrupt_voice_client.disconnect(force=True)
            
            self.interrupt_voice_client = None # Ensure it's cleared
            self.check_interrupt_task = None # Ensure task is cleared

            await ctx.send(getattr(config, 'VOICE_MSG_TARGET_CLEARED', "🎯 Interrupt target has been cleared."))
            logger.info(f"Interrupt target {old_target_id} cleared for guild {ctx.guild.id} by {ctx.author.name}.")
        else:
            await ctx.send(getattr(config, 'VOICE_MSG_NO_TARGET_TO_CLEAR', "ℹ️ No interrupt target is currently set for this server."))


    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Handles voice state changes for the target user."""
        if member.id != self.target_user_id or member.guild.id != self.target_guild_id:
            return

        # Target user joined a voice channel
        if before.channel is None and after.channel is not None:
            logger.info(f"Target user {member.name} joined voice channel {after.channel.name} in guild {member.guild.id}.")
            
            # Clean up existing VC client if it exists, to prepare for new connection or move
            if self.interrupt_voice_client and self.interrupt_voice_client.is_connected():
                if self.interrupt_voice_client.channel == after.channel: # Already in the correct channel
                    logger.debug(f"Bot already in target's channel: {after.channel.name}.")
                else: # Bot in a different channel, move it
                    logger.info(f"Bot is in VC {self.interrupt_voice_client.channel.name}, moving to {after.channel.name}.")
                    try:
                        await self.interrupt_voice_client.move_to(after.channel)
                    except Exception as e:
                        logger.error(f"Error moving voice client to {after.channel.name}: {e}", exc_info=True)
                        await self.interrupt_voice_client.disconnect(force=True) # Disconnect if move fails
                        self.interrupt_voice_client = None # Force reconnect below
            
            if not self.interrupt_voice_client or not self.interrupt_voice_client.is_connected():
                try:
                    bot_member = member.guild.me
                    permissions = after.channel.permissions_for(bot_member)
                    if not permissions.connect:
                        logger.warning(f"Bot lacks 'Connect' permission for VC '{after.channel.name}'.")
                        return
                    self.interrupt_voice_client = await after.channel.connect(timeout=10.0, reconnect=True)
                    logger.info(f"Connected to voice channel {after.channel.name} to monitor {member.name}.")
                except Exception as e: # Catch broad exceptions for connection issues
                    logger.error(f"Failed to connect/reconnect to {after.channel.name} for target {member.name}: {e}", exc_info=True)
                    self.interrupt_voice_client = None # Ensure client is None if connection fails
                    return # Stop further processing if connection fails

            # Start or restart the checking task
            if self.check_interrupt_task and not self.check_interrupt_task.done():
                self.check_interrupt_task.cancel()
            if self.interrupt_voice_client: # Only start if connection was successful
                self.check_interrupt_task = self.bot.loop.create_task(self._check_and_interrupt_task(member))
                logger.info(f"Started/Restarted interrupt check task for {member.name} in {after.channel.name}.")

        # Target user left the voice channel the bot is in for them, or any VC if target left all VCs
        elif before.channel is not None and after.channel is None:
            logger.info(f"Target user {member.name} left voice channel {before.channel.name}.")
            if self.interrupt_voice_client and self.interrupt_voice_client.is_connected() and \
               self.interrupt_voice_client.channel == before.channel:
                if self.check_interrupt_task and not self.check_interrupt_task.done():
                    self.check_interrupt_task.cancel()
                    logger.info(f"Cancelled interrupt check task for {member.name} as they left VC.")
                self.check_interrupt_task = None
                await self.interrupt_voice_client.disconnect(force=True)
                logger.info(f"Disconnected from {before.channel.name} as target left.")
                self.interrupt_voice_client = None
        
        # Target user moved to a different channel
        elif before.channel is not None and after.channel is not None and before.channel != after.channel:
            logger.info(f"Target user {member.name} moved from {before.channel.name} to {after.channel.name}.")
            if self.interrupt_voice_client and self.interrupt_voice_client.is_connected():
                try:
                    await self.interrupt_voice_client.move_to(after.channel)
                    logger.info(f"Moved with target user {member.name} to {after.channel.name}.")
                    if self.check_interrupt_task and not self.check_interrupt_task.done(): # Restart task for new channel context
                        self.check_interrupt_task.cancel()
                    self.check_interrupt_task = self.bot.loop.create_task(self._check_and_interrupt_task(member))
                except Exception as e:
                    logger.error(f"Error moving voice client to {after.channel.name} with target: {e}", exc_info=True)
                    # Fallback: disconnect and let join logic handle reconnect if target is still in a VC
                    await self.interrupt_voice_client.disconnect(force=True)
                    self.interrupt_voice_client = None
                    # Simulate a fresh join to the new channel if the target is still in a VC
                    if member.voice and member.voice.channel: # Ensure target is still in a voice channel
                         await self.on_voice_state_update(member, discord.VoiceState(channel=None, session_id=before.session_id, deaf=before.deaf, mute=before.mute, self_deaf=before.self_deaf, self_mute=before.self_mute, self_stream=before.self_stream, self_video=before.self_video, suppress=before.suppress, requested_to_speak=before.requested_to_speak), member.voice)
            elif member.voice and member.voice.channel: # Bot wasn't connected, but target moved. Treat as a join to the new channel.
                 await self.on_voice_state_update(member, discord.VoiceState(channel=None, session_id=before.session_id, deaf=before.deaf, mute=before.mute, self_deaf=before.self_deaf, self_mute=before.self_mute, self_stream=before.self_stream, self_video=before.self_video, suppress=before.suppress, requested_to_speak=before.requested_to_speak), member.voice)


    async def _check_and_interrupt_task(self, member: discord.Member):
        """Periodically checks if the target member is unmuted and plays an interrupt sound."""
        try:
            await asyncio.sleep(getattr(config, 'VOICE_INTERRUPT_INITIAL_DELAY_SECONDS', 1.5)) 

            while True:
                if not self.interrupt_voice_client or not self.interrupt_voice_client.is_connected():
                    logger.debug(f"Interrupt task: Voice client disconnected for {member.name}. Stopping task.")
                    break
                
                # Fetch fresh member and voice_state objects
                current_guild = self.bot.get_guild(member.guild.id)
                if not current_guild: logger.warning(f"Interrupt task: Guild {member.guild.id} not found."); break
                
                refreshed_member = current_guild.get_member(member.id)
                if not refreshed_member or not refreshed_member.voice or refreshed_member.voice.channel != self.interrupt_voice_client.channel:
                    logger.debug(f"Interrupt task: Target {member.name} no longer in monitored VC or not found. Stopping task.")
                    if self.interrupt_voice_client.is_connected(): # Disconnect if target left monitored channel
                        await self.interrupt_voice_client.disconnect(force=True)
                        self.interrupt_voice_client = None
                    break
                
                member_voice_state = refreshed_member.voice
                is_speakable = not member_voice_state.self_mute and not member_voice_state.self_deaf

                if is_speakable and self.interrupt_voice_client and not self.interrupt_voice_client.is_playing():
                    if os.path.exists(self.interrupt_sound_path):
                        try:
                            bot_guild_member = current_guild.me
                            if not self.interrupt_voice_client.channel.permissions_for(bot_guild_member).speak:
                                logger.warning(f"Bot lacks 'Speak' permission in VC '{self.interrupt_voice_client.channel.name}'. Cannot play interrupt.")
                                await asyncio.sleep(getattr(config, 'VOICE_INTERRUPT_CHECK_INTERVAL_SECONDS', 0.75))
                                continue

                            audio_source = discord.FFmpegOpusAudio(self.interrupt_sound_path, **self.ffmpeg_options)
                            self.interrupt_voice_client.play(audio_source, after=lambda e: self._handle_play_error(e, member.guild.id))
                            logger.info(f"Playing interrupt sound for {member.name} in {self.interrupt_voice_client.channel.name}.")
                        except Exception as e:
                            logger.error(f"Error playing interrupt sound for {member.name}: {e}", exc_info=True)
                    else:
                        logger.warning(f"Interrupt sound file '{self.interrupt_sound_path}' not found when trying to play for {member.name}.")
                await asyncio.sleep(getattr(config, 'VOICE_INTERRUPT_CHECK_INTERVAL_SECONDS', 0.75))
        except asyncio.CancelledError:
            logger.info(f"Interrupt check task for {member.name} was cancelled.")
        except Exception as e:
            logger.error(f"Unexpected error in interrupt check task for {member.name}: {e}", exc_info=True)
        finally:
            logger.debug(f"Interrupt check task for {member.name} concluded.")
            # If task ends for any reason other than cancellation by target leaving/clearing,
            # and bot is still connected to target's channel, disconnect.
            if (not (self.check_interrupt_task and self.check_interrupt_task.cancelled()) and
                self.interrupt_voice_client and self.interrupt_voice_client.is_connected() and
                member.voice and self.interrupt_voice_client.channel == member.voice.channel and
                member.id == self.target_user_id): # Ensure it's still the current target
                logger.info(f"Interrupt task ended unexpectedly for {member.name}; disconnecting from VC.")
                await self.interrupt_voice_client.disconnect(force=True)
                self.interrupt_voice_client = None


    def _handle_play_error(self, error: Optional[Exception], guild_id: int):
        if error:
            logger.error(f"Error after playing interrupt sound in guild {guild_id}: {error}", exc_info=error)

    async def cog_unload(self):
        logger.info("VoiceInterruptCog unloading. Cleaning up tasks and voice clients.")
        if self.check_interrupt_task and not self.check_interrupt_task.done():
            self.check_interrupt_task.cancel()
            try: await self.check_interrupt_task
            except asyncio.CancelledError: logger.info("Interrupt check task successfully cancelled during cog unload.")
            except Exception as e: logger.error(f"Error awaiting cancelled interrupt task: {e}")

        if self.interrupt_voice_client and self.interrupt_voice_client.is_connected():
            await self.interrupt_voice_client.disconnect(force=True)
        
        self.target_user_id = None
        self.target_guild_id = None
        self.interrupt_voice_client = None
        self.check_interrupt_task = None
        logger.info("VoiceInterruptCog unloaded successfully.")

    @set_target_user.error
    @clear_target_user.error
    async def on_target_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(getattr(config, 'VOICE_MSG_NO_PERMISSION_TARGET_CMD', "❌ You don't have permission to manage interrupt targets."))
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing argument: `{error.param.name}`. Please specify a user.")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send(f"❌ Could not find a member named: `{error.argument}`.")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ This command is on cooldown. Please try again in {error.retry_after:.2f}s.")
        else:
            logger.error(f"Error in target command '{ctx.command.name}': {error}", exc_info=True)
            await ctx.send(getattr(config, 'VOICE_MSG_GENERIC_CMD_ERROR', "❗ An unexpected error occurred."))

async def setup(bot: commands.Bot):
    sound_path = getattr(config, 'VOICE_INTERRUPT_SOUND_PATH', './sounds/interrupt.mp3')
    sound_dir = os.path.dirname(sound_path)
    if sound_dir and not os.path.exists(sound_dir): # Check if sound_dir is not empty (e.g. for root path)
        try:
            os.makedirs(sound_dir, exist_ok=True)
            logger.info(f"Created directory for interrupt sound: {sound_dir}")
        except OSError as e:
            logger.error(f"Could not create directory {sound_dir} for interrupt sound: {e}")
    await bot.add_cog(VoiceInterruptCog(bot))
    logger.info("VoiceInterruptCog has been setup and added to the bot.")
