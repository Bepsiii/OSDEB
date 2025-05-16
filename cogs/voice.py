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
from typing import Optional # <--- IMPORT ADDED HERE

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
        sound_dir = os.path.dirname(self.interrupt_sound_path)
        if sound_dir and not os.path.exists(sound_dir): # Check if sound_dir is not empty (e.g. for root path)
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
    @commands.has_permissions(manage_guild=getattr(config, 'VOICE_SET_TARGET_ADMIN_ONLY', True)) # Configurable admin only
    @commands.cooldown(1, getattr(config, 'VOICE_SET_TARGET_COOLDOWN', 10), commands.BucketType.guild)
    async def set_target_user(self, ctx: commands.Context, target: discord.Member):
        """Sets the target user for voice interruptions in the current guild."""
        self.target_user_id = target.id
        self.target_guild_id = ctx.guild.id # Track which guild this target is for
        
        # If a previous task for a different target/guild was running, cancel it.
        if self.check_interrupt_task and not self.check_interrupt_task.done():
            self.check_interrupt_task.cancel()
            logger.info(f"Cancelled previous interrupt check task for guild {self.target_guild_id}.") # Should be old guild ID if it changed
        if self.interrupt_voice_client and self.interrupt_voice_client.is_connected():
            # Check if the VC is in the same guild as the new target. If not, or if target changes, disconnect.
            if self.interrupt_voice_client.guild.id != ctx.guild.id:
                 await self.interrupt_voice_client.disconnect(force=True)
                 logger.info(f"Disconnected from previous voice channel in guild {self.interrupt_voice_client.guild.id}.")
                 self.interrupt_voice_client = None
            elif self.target_user_id != target.id and self.interrupt_voice_client.guild.id == ctx.guild.id : # if target changes in same guild
                 await self.interrupt_voice_client.disconnect(force=True)
                 logger.info(f"Disconnected from voice channel in guild {ctx.guild.id} due to target change.")
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
            # self.target_guild_id = None # Keep this to know which guild's target was cleared, or clear it if only one global target
            
            if self.check_interrupt_task and not self.check_interrupt_task.done():
                self.check_interrupt_task.cancel()
            if self.interrupt_voice_client and self.interrupt_voice_client.is_connected() and self.interrupt_voice_client.guild.id == ctx.guild.id:
                await self.interrupt_voice_client.disconnect(force=True)
                self.interrupt_voice_client = None # Clear it after disconnect

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
            logger.info(f"Target user {member.name} joined voice channel {after.channel.name} in guild {member.guild.id}.")
            if self.interrupt_voice_client and self.interrupt_voice_client.is_connected():
                if self.interrupt_voice_client.channel != after.channel:
                    logger.info(f"Bot is already in VC {self.interrupt_voice_client.channel.name}, moving to {after.channel.name}.")
                    try:
                        await self.interrupt_voice_client.move_to(after.channel)
                    except Exception as e:
                        logger.error(f"Error moving voice client to {after.channel.name}: {e}", exc_info=True)
                        # Attempt to disconnect and reconnect as a fallback
                        await self.interrupt_voice_client.disconnect(force=True)
                        self.interrupt_voice_client = None 
                        # Fall through to connect logic below
            
            if not self.interrupt_voice_client or not self.interrupt_voice_client.is_connected(): # If not connected or move failed
                try:
                    bot_member = member.guild.me
                    permissions = after.channel.permissions_for(bot_member)
                    if not permissions.connect:
                        logger.warning(f"Bot lacks 'Connect' permission for VC '{after.channel.name}' in guild {member.guild.id}.")
                        return
                    # Speak permission checked before playing in the task

                    self.interrupt_voice_client = await after.channel.connect(timeout=10.0, reconnect=True)
                    logger.info(f"Connected to voice channel {after.channel.name} to monitor {member.name}.")
                except asyncio.TimeoutError:
                    logger.error(f"Timeout connecting to {after.channel.name} for target {member.name}.")
                    self.interrupt_voice_client = None
                    return
                except discord.ClientException as e: 
                    logger.error(f"ClientException connecting to {after.channel.name}: {e}. Bot might be in another VC.")
                    self.interrupt_voice_client = None
                    return
                except Exception as e:
                    logger.error(f"Failed to connect to {after.channel.name} for target {member.name}: {e}", exc_info=True)
                    self.interrupt_voice_client = None
                    return

            # Start or restart the checking task
            if self.check_interrupt_task and not self.check_interrupt_task.done():
                self.check_interrupt_task.cancel()
            if self.interrupt_voice_client: 
                self.check_interrupt_task = self.bot.loop.create_task(self._check_and_interrupt_task(member))
                logger.info(f"Started interrupt check task for {member.name} in {after.channel.name}.")

        # Target user left the specific voice channel the bot was in for them, or any VC if bot wasn't specifically in theirs
        elif before.channel is not None and after.channel is None:
            logger.info(f"Target user {member.name} left voice channel {before.channel.name} in guild {member.guild.id}.")
            # Only disconnect if the bot is in a channel AND (it's the channel the target left OR target left all VCs)
            if self.interrupt_voice_client and self.interrupt_voice_client.is_connected() and \
               (self.interrupt_voice_client.channel == before.channel or not member.voice): # Disconnect if target left our channel or any channel
                if self.check_interrupt_task and not self.check_interrupt_task.done():
                    self.check_interrupt_task.cancel()
                    logger.info(f"Cancelled interrupt check task for {member.name} as they left VC.")
                self.check_interrupt_task = None
                await self.interrupt_voice_client.disconnect(force=True)
                logger.info(f"Disconnected from voice channel in guild {member.guild.id} as target left.")
                self.interrupt_voice_client = None
        
        # Target user moved to a different channel
        elif before.channel is not None and after.channel is not None and before.channel != after.channel:
            logger.info(f"Target user {member.name} moved from {before.channel.name} to {after.channel.name}.")
            if self.interrupt_voice_client and self.interrupt_voice_client.is_connected():
                try:
                    await self.interrupt_voice_client.move_to(after.channel)
                    logger.info(f"Moved with target user {member.name} to {after.channel.name}.")
                    # Task should continue or be restarted if necessary
                    if self.check_interrupt_task and not self.check_interrupt_task.done():
                        self.check_interrupt_task.cancel()
                    self.check_interrupt_task = self.bot.loop.create_task(self._check_and_interrupt_task(member)) # Restart task for new channel context
                except Exception as e:
                    logger.error(f"Error moving voice client to {after.channel.name} with target: {e}", exc_info=True)
                    # Fallback: disconnect and try to reconnect
                    await self.interrupt_voice_client.disconnect(force=True)
                    self.interrupt_voice_client = None
                    # Trigger the "joined a channel" logic again
                    await self.on_voice_state_update(member, discord.VoiceState(channel=None), member.voice) # Simulate a fresh join
            else: # Bot wasn't connected, but target moved. Treat as a join to the new channel.
                 await self.on_voice_state_update(member, discord.VoiceState(channel=None), member.voice)


    async def _check_and_interrupt_task(self, member: discord.Member):
        """Periodically checks if the target member is unmuted and plays an interrupt sound."""
        try:
            await asyncio.sleep(getattr(config, 'VOICE_INTERRUPT_INITIAL_DELAY_SECONDS', 1.5)) 

            while True:
                if not self.interrupt_voice_client or not self.interrupt_voice_client.is_connected():
                    logger.debug(f"Interrupt task (vc check): Voice client disconnected for {member.name}. Stopping task.")
                    break
                if not member.voice or member.voice.channel != self.interrupt_voice_client.channel:
                    logger.debug(f"Interrupt task (member channel check): Target {member.name} not in monitored VC. Stopping task.")
                    # Disconnect if the bot is still in a channel but the target isn't there.
                    if self.interrupt_voice_client.is_connected():
                        await self.interrupt_voice_client.disconnect(force=True)
                        self.interrupt_voice_client = None
                    break
                
                # Refresh member object to get latest voice state
                try:
                    current_guild = self.bot.get_guild(member.guild.id)
                    if not current_guild: break # Guild not found
                    refreshed_member = current_guild.get_member(member.id)
                    if not refreshed_member or not refreshed_member.voice: break # Member left guild or VC
                    member_voice_state = refreshed_member.voice
                except Exception as e:
                    logger.warning(f"Could not refresh member voice state for {member.name}: {e}")
                    await asyncio.sleep(getattr(config, 'VOICE_INTERRUPT_CHECK_INTERVAL_SECONDS', 1.0))
                    continue


                is_speakable = not member_voice_state.self_mute and not member_voice_state.self_deaf

                if is_speakable and self.interrupt_voice_client and not self.interrupt_voice_client.is_playing():
                    if os.path.exists(self.interrupt_sound_path):
                        try:
                            bot_guild_member = member.guild.me
                            if not self.interrupt_voice_client.channel.permissions_for(bot_guild_member).speak:
                                logger.warning(f"Bot lacks 'Speak' permission in VC '{self.interrupt_voice_client.channel.name}'. Cannot play interrupt.")
                                await asyncio.sleep(getattr(config, 'VOICE_INTERRUPT_CHECK_INTERVAL_SECONDS', 1.0))
                                continue

                            audio_source = discord.FFmpegOpusAudio(self.interrupt_sound_path, **self.ffmpeg_options)
                            self.interrupt_voice_client.play(audio_source, after=lambda e: self._handle_play_error(e, member.guild.id))
                            logger.info(f"Playing interrupt sound for {member.name} in {self.interrupt_voice_client.channel.name}.")
                        except Exception as e:
                            logger.error(f"Error playing interrupt sound for {member.name}: {e}", exc_info=True)
                    else:
                        logger.warning(f"Interrupt sound file '{self.interrupt_sound_path}' not found when trying to play for {member.name}.")
                        # Stop the task if sound file is missing to avoid spamming logs
                        # await ctx.send to a log channel or admin could be useful here
                        # For now, it will keep trying if the file appears later.

                await asyncio.sleep(getattr(config, 'VOICE_INTERRUPT_CHECK_INTERVAL_SECONDS', 0.75))
        except asyncio.CancelledError:
            logger.info(f"Interrupt check task for {member.name} was cancelled.")
        except Exception as e:
            logger.error(f"Unexpected error in interrupt check task for {member.name}: {e}", exc_info=True)
        finally:
            logger.debug(f"Interrupt check task for {member.name} concluded.")
            # Ensure cleanup if task ends but bot is connected and target_user_id matches
            if member.id == self.target_user_id and self.interrupt_voice_client and self.interrupt_voice_client.is_connected():
                # This check helps ensure that only the task for the *current* target triggers a disconnect here.
                # However, on_voice_state_update should be the primary handler for disconnects.
                # If the target leaves, on_voice_state_update cancels this task AND disconnects.
                # If the target is cleared, the command cancels this task AND disconnects.
                pass


    def _handle_play_error(self, error: Optional[Exception], guild_id: int):
        if error:
            logger.error(f"Error after playing interrupt sound in guild {guild_id}: {error}", exc_info=error)

    async def cog_unload(self):
        """Cog cleanup when unloaded."""
        logger.info("VoiceInterruptCog unloading. Cleaning up tasks and voice clients.")
        if self.check_interrupt_task and not self.check_interrupt_task.done():
            self.check_interrupt_task.cancel()
            # Wait for task to actually cancel
            try:
                await self.check_interrupt_task
            except asyncio.CancelledError:
                logger.info("Interrupt check task successfully cancelled during cog unload.")
            except Exception as e:
                logger.error(f"Error awaiting cancelled interrupt task: {e}")


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
    sound_path = getattr(config, 'VOICE_INTERRUPT_SOUND_PATH', './sounds/interrupt.mp3')
    sound_dir = os.path.dirname(sound_path)
    if sound_dir and not os.path.exists(sound_dir):
        try:
            os.makedirs(sound_dir, exist_ok=True)
            logger.info(f"Created directory for interrupt sound: {sound_dir}")
        except OSError as e:
            logger.error(f"Could not create directory {sound_dir} for interrupt sound: {e}")

    await bot.add_cog(VoiceInterruptCog(bot))
    logger.info("VoiceInterruptCog has been setup and added to the bot.")

