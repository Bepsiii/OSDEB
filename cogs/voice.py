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
        self.target_guild_id: Optional[int] = None # Store guild ID where target was set
        self.interrupt_voice_client: Optional[discord.VoiceClient] = None
        self.check_interrupt_task: Optional[asyncio.Task] = None
        self.interrupt_sound_path: str = getattr(config, 'VOICE_INTERRUPT_SOUND_PATH', './sounds/interrupt.mp3')
        self.ffmpeg_options: dict = getattr(config, 'VOICE_INTERRUPT_FFMPEG_OPTIONS', {'options': '-vn'})
        
        # Ensure the directory for the interrupt sound exists if it's a relative path from a 'sounds' folder
        if self.interrupt_sound_path.startswith('./sounds/') and not os.path.exists('./sounds'):
            try:
                os.makedirs('./sounds', exist_ok=True)
                logger.info("Created './sounds/' directory for interrupt sound.")
            except OSError as e:
                logger.error(f"Could not create './sounds/' directory: {e}")

        if not os.path.exists(self.interrupt_sound_path):
            logger.warning(
                f"Interrupt sound file not found at configured path: {self.interrupt_sound_path}. "
                "The interrupt feature will not play sound."
            )

    @commands.command(name='setinterrupttarget', aliases=['settarget'], help='Sets a target user to be interrupted.')
    @commands.has_permissions(manage_guild=getattr(config, 'VOICE_SET_TARGET_ADMIN_ONLY', True)) # Configurable admin only
    @commands.cooldown(1, getattr(config, 'VOICE_SET_TARGET_COOLDOWN', 10), commands.BucketType.guild)
    async def set_target_user(self, ctx: commands.Context, target: discord.Member):
        """Sets the target user for voice interruptions in the current guild."""
        self.target_user_id = target.id
        self.target_guild_id = ctx.guild.id # Track which guild this target is for
        
        # If a previous task for a different target/guild was running, cancel it.
        if self.check_interrupt_task and not self.check_interrupt_task.done():
            self.check_interrupt_task.cancel()
            logger.info(f"Cancelled previous interrupt check task for guild {self.target_guild_id}.")
        if self.interrupt_voice_client and self.interrupt_voice_client.is_connected():
            await self.interrupt_voice_client.disconnect(force=True)
            logger.info(f"Disconnected from previous voice channel in guild {self.target_guild_id}.")
        self.interrupt_voice_client = None

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
            self.target_guild_id = None
            if self.check_interrupt_task and not self.check_interrupt_task.done():
                self.check_interrupt_task.cancel()
            if self.interrupt_voice_client and self.interrupt_voice_client.is_connected():
                await self.interrupt_voice_client.disconnect(force=True)
            self.interrupt_voice_client = None
            await ctx.send(getattr(config, 'VOICE_MSG_TARGET_CLEARED', "🎯 Interrupt target has been cleared."))
            logger.info(f"Interrupt target {old_target_id} cleared for guild {ctx.guild.id} by {ctx.author.name}.")
        else:
            await ctx.send(getattr(config, 'VOICE_MSG_NO_TARGET_TO_CLEAR', "ℹ️ No interrupt target is currently set for this server."))


    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Handles voice state changes for the target user."""
        if member.id != self.target_user_id or member.guild.id != self.target_guild_id:
            return # Not the target user or not in the targeted guild

        # Target user joined a voice channel
        if before.channel is None and after.channel is not None:
            if self.interrupt_voice_client and self.interrupt_voice_client.is_connected():
                # Bot is already connected, possibly to another channel or for this user.
                # If it's not the same channel, move or decide policy. For now, let's assume it should move.
                if self.interrupt_voice_client.channel != after.channel:
                    await self.interrupt_voice_client.move_to(after.channel)
                    logger.info(f"Moved to {member.name}'s new voice channel: {after.channel.name} in guild {member.guild.id}.")
            else:
                try:
                    # Check bot permissions for the target channel
                    bot_member = member.guild.me
                    permissions = after.channel.permissions_for(bot_member)
                    if not permissions.connect:
                        logger.warning(f"Bot lacks 'Connect' permission for VC '{after.channel.name}' in guild {member.guild.id}.")
                        # Optionally send a message to a configured log channel or the user who set the target.
                        return
                    if not permissions.speak:
                         logger.warning(f"Bot lacks 'Speak' permission for VC '{after.channel.name}' in guild {member.guild.id}.")
                        # return # Bot can still join, but won't be able to play sound.

                    self.interrupt_voice_client = await after.channel.connect(timeout=10.0, reconnect=True)
                    logger.info(f"Connected to voice channel {after.channel.name} in guild {member.guild.id} to monitor {member.name}.")
                except asyncio.TimeoutError:
                    logger.error(f"Timeout connecting to {after.channel.name} for target {member.name}.")
                    self.interrupt_voice_client = None
                    return
                except discord.ClientException as e: # e.g. already connected elsewhere in guild by another part of bot
                    logger.error(f"ClientException connecting to {after.channel.name}: {e}. The bot might be in another VC in this guild.")
                    # If bot is already connected to a different VC in the same guild, it can't join another.
                    # This cog assumes it has priority or is the only voice user.
                    # A more complex bot would need a central voice manager.
                    # For now, if it fails to connect, it just logs.
                    self.interrupt_voice_client = None
                    return
                except Exception as e:
                    logger.error(f"Failed to connect to {after.channel.name} for target {member.name}: {e}", exc_info=True)
                    self.interrupt_voice_client = None
                    return

            # Start or restart the checking task
            if self.check_interrupt_task and not self.check_interrupt_task.done():
                self.check_interrupt_task.cancel()
            if self.interrupt_voice_client: # Only start if connection was successful
                self.check_interrupt_task = self.bot.loop.create_task(self._check_and_interrupt_task(member))
                logger.info(f"Started interrupt check task for {member.name} in {after.channel.name}.")

        # Target user left a voice channel (or moved, which is handled by join logic first)
        elif before.channel is not None and after.channel is None:
            logger.info(f"Target user {member.name} left voice channel {before.channel.name} in guild {member.guild.id}.")
            if self.check_interrupt_task and not self.check_interrupt_task.done():
                self.check_interrupt_task.cancel()
                logger.info(f"Cancelled interrupt check task for {member.name}.")
            self.check_interrupt_task = None
            if self.interrupt_voice_client and self.interrupt_voice_client.is_connected():
                await self.interrupt_voice_client.disconnect(force=True)
                logger.info(f"Disconnected from voice channel in guild {member.guild.id} as target left.")
            self.interrupt_voice_client = None

    async def _check_and_interrupt_task(self, member: discord.Member):
        """Periodically checks if the target member is unmuted and plays an interrupt sound."""
        try:
            await asyncio.sleep(getattr(config, 'VOICE_INTERRUPT_INITIAL_DELAY_SECONDS', 2.0)) # Initial delay

            while True:
                if not self.interrupt_voice_client or not self.interrupt_voice_client.is_connected():
                    logger.info(f"Interrupt task: Voice client disconnected or not available for {member.name}. Stopping task.")
                    break
                if not member.voice or member.voice.channel != self.interrupt_voice_client.channel:
                    logger.info(f"Interrupt task: Target {member.name} is no longer in the monitored voice channel. Stopping task.")
                    # This case should ideally be handled by on_voice_state_update leading to task cancellation.
                    # If it reaches here, it's a fallback.
                    if self.interrupt_voice_client.is_connected():
                        await self.interrupt_voice_client.disconnect(force=True)
                    self.interrupt_voice_client = None
                    break

                # Check if member is "speakable" (not self-muted or self-deafened)
                is_speakable = not member.voice.self_mute and not member.voice.self_deaf

                if is_speakable and not self.interrupt_voice_client.is_playing():
                    if os.path.exists(self.interrupt_sound_path):
                        try:
                            # Ensure bot has speak permissions before trying to play
                            bot_member = member.guild.me
                            if not self.interrupt_voice_client.channel.permissions_for(bot_member).speak:
                                logger.warning(f"Bot lacks 'Speak' permission in VC '{self.interrupt_voice_client.channel.name}' for guild {member.guild.id}. Cannot play interrupt sound.")
                                await asyncio.sleep(getattr(config, 'VOICE_INTERRUPT_CHECK_INTERVAL_SECONDS', 1.0))
                                continue

                            audio_source = discord.FFmpegOpusAudio(self.interrupt_sound_path, **self.ffmpeg_options)
                            self.interrupt_voice_client.play(audio_source, after=lambda e: self._handle_play_error(e, member.guild.id))
                            logger.info(f"Playing interrupt sound for {member.name} in {self.interrupt_voice_client.channel.name}.")
                        except Exception as e:
                            logger.error(f"Error playing interrupt sound for {member.name}: {e}", exc_info=True)
                    else:
                        logger.warning(f"Interrupt sound file not found at '{self.interrupt_sound_path}' when trying to play for {member.name}.")
                        # Consider stopping the task or notifying if sound is persistently missing
                        # For now, it will just keep checking.

                await asyncio.sleep(getattr(config, 'VOICE_INTERRUPT_CHECK_INTERVAL_SECONDS', 1.0))
        except asyncio.CancelledError:
            logger.info(f"Interrupt check task for {member.name} was cancelled.")
        except Exception as e:
            logger.error(f"Unexpected error in interrupt check task for {member.name}: {e}", exc_info=True)
        finally:
            logger.info(f"Interrupt check task for {member.name} concluded.")
            # Ensure cleanup if task ends unexpectedly but bot is still connected
            if self.interrupt_voice_client and self.interrupt_voice_client.is_connected() and member.id == self.target_user_id:
                # Only disconnect if this task was the one responsible for this specific target
                # This check is a bit redundant if on_voice_state_update handles all exits.
                pass


    def _handle_play_error(self, error: Optional[Exception], guild_id: int):
        if error:
            logger.error(f"Error after playing interrupt sound in guild {guild_id}: {error}", exc_info=error)
        # else:
            # logger.debug(f"Interrupt sound finished playing in guild {guild_id}.")

    async def cog_unload(self):
        """Cog cleanup when unloaded."""
        logger.info("VoiceInterruptCog unloading. Cleaning up tasks and voice clients.")
        if self.check_interrupt_task and not self.check_interrupt_task.done():
            self.check_interrupt_task.cancel()
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
    """Sets up the VoiceInterruptCog."""
    # Ensure the directory for the interrupt sound exists if specified in config
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

