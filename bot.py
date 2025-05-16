# main_bot.py
"""
Main file for the Discord Bot.
Handles bot setup, event listeners, command loading, and core functionality including presence updates.
"""
import discord
from discord.ext import commands, tasks
import asyncio
import logging

# Import configurations and services
import config
# Assuming GeminiService is still relevant from previous refactors
from gemini_service import GeminiService

# Assuming MusicV2 cog is in cogs.music
from cogs.music import MusicV2 # This import might not be needed directly here if using bot.get_cog

# --- Logger Setup ---
logging.basicConfig(level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
                    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)


class MyBot(commands.Bot):
    """
    Custom Bot class to encapsulate bot-specific attributes and methods.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gemini_service = GeminiService() # If using Gemini
        # Other services can be initialized here

    async def setup_hook(self):
        """
        Asynchronous setup that is called when the bot is logged in but before it has connected to Discord.
        """
        logger.info("Running setup_hook...")
        await self.load_all_extensions()
        # Start tasks after extensions are loaded, especially if tasks depend on cogs
        if not update_bot_status_task.is_running():
             update_bot_status_task.start()


    async def load_all_extensions(self):
        """Loads all cogs specified in the config file."""
        logger.info(f"Attempting to load {len(config.COGS_TO_LOAD)} cogs...")
        for extension_path in config.COGS_TO_LOAD:
            try:
                await self.load_extension(extension_path)
                logger.info(f"✅ Successfully loaded extension: {extension_path}")
            except Exception as e:
                logger.error(f"❌ Failed to load extension {extension_path}: {e}", exc_info=True)


    async def on_ready(self):
        """Called when the bot is done preparing the data received from Discord."""
        logger.info(f'Bot connected as {self.user} (ID: {self.user.id})')
        logger.info(f'Command Prefix: "{config.COMMAND_PREFIX}"')
        logger.info(f'Owner ID: {config.OWNER_ID}')
        logger.info(f'discord.py version: {discord.__version__}')
        logger.info('Bot is ready and online!')
        # Moved task start to setup_hook to ensure cogs are loaded first.
        # if not update_bot_status_task.is_running():
        #    update_bot_status_task.start()

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """Global command error handler."""
        # Basic error handling, can be expanded
        if isinstance(error, commands.CommandNotFound):
            # logger.warning(f"Command not found: {ctx.message.content} by {ctx.author}")
            return # Often best to silently ignore
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"You're missing a required argument: `{error.param.name}`. "
                           f"Use `{config.COMMAND_PREFIX}help {ctx.command.qualified_name}` for more info.")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"This command is on cooldown. Please try again in {error.retry_after:.2f} seconds.")
        elif isinstance(error, commands.CheckFailure):
            await ctx.send("You do not have the permission to use this command or a check failed.")
        else:
            logger.error(f"Unhandled command error in '{ctx.command}' invoked by '{ctx.author}': {error}", exc_info=True)
            await ctx.send("An unexpected error occurred while running that command.")


# --- Bot Intents Setup ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True # Essential for music cog and presence updates based on voice

# --- Bot Instance ---
bot = MyBot(
    command_prefix=commands.when_mentioned_or(config.COMMAND_PREFIX),
    intents=intents,
    help_command=None, # Assuming custom help or cog-based help
    owner_id=config.OWNER_ID
)

# --- Presence Update Task ---
@tasks.loop(seconds=config.PRESENCE_UPDATE_INTERVAL_SECONDS)
async def update_bot_status_task():
    """Periodically updates the bot's presence."""
    activity_name = config.DEFAULT_PRESENCE_NAME
    activity_type_str = config.DEFAULT_PRESENCE_ACTIVITY_TYPE.lower()
    
    activity_type_map = {
        "playing": discord.ActivityType.playing,
        "streaming": discord.ActivityType.streaming, # Needs stream_url if used
        "listening": discord.ActivityType.listening,
        "watching": discord.ActivityType.watching,
        "competing": discord.ActivityType.competing,
    }
    selected_activity_type = activity_type_map.get(activity_type_str, discord.ActivityType.playing)

    song_title = None
    
    # Try to get music cog and current song if a target guild is set
    if config.TARGET_GUILD_ID_FOR_PRESENCE and config.TARGET_GUILD_ID_FOR_PRESENCE != 0:
        music_cog = bot.get_cog("Music") # Assumes your music cog class is named "Music" (as in MusicV2 refactor)
        if music_cog and hasattr(music_cog, 'get_current_song_details'):
            try:
                # The get_current_song_details method should exist in your MusicV2 cog
                current_song_obj = music_cog.get_current_song_details(config.TARGET_GUILD_ID_FOR_PRESENCE)
                if current_song_obj:
                    song_title = current_song_obj.title
            except Exception as e:
                logger.error(f"Error fetching current song for presence: {e}", exc_info=False) # Log less verbosely for task errors

    if song_title:
        name_prefix = f"{config.MUSIC_PRESENCE_EMOJI} " if hasattr(config, 'MUSIC_PRESENCE_EMOJI') and config.MUSIC_PRESENCE_EMOJI else ""
        activity_name = f"{name_prefix}{song_title}"
        music_activity_type_str = config.MUSIC_PRESENCE_ACTIVITY_TYPE.lower()
        selected_activity_type = activity_type_map.get(music_activity_type_str, discord.ActivityType.listening)
    else:
        name_prefix = f"{config.DEFAULT_PRESENCE_EMOJI} " if hasattr(config, 'DEFAULT_PRESENCE_EMOJI') and config.DEFAULT_PRESENCE_EMOJI else ""
        activity_name = f"{name_prefix}{config.DEFAULT_PRESENCE_NAME}"

    # Ensure activity name is within Discord's limits (usually 128 characters)
    activity_name = activity_name[:128]

    try:
        current_activity = bot.activity
        # Only change presence if it's different to avoid unnecessary API calls
        if not current_activity or current_activity.name != activity_name or current_activity.type != selected_activity_type:
            new_activity = discord.Activity(type=selected_activity_type, name=activity_name)
            await bot.change_presence(activity=new_activity)
            logger.debug(f"Presence updated: {selected_activity_type.name} {activity_name}")
        else:
            logger.debug(f"Presence unchanged: {selected_activity_type.name} {activity_name}")
    except Exception as e:
        logger.error(f"Failed to update bot presence: {e}", exc_info=False)


@update_bot_status_task.before_loop
async def before_update_bot_status_task():
    """Ensures the bot is ready before starting the presence update loop."""
    await bot.wait_until_ready()
    logger.info("Bot presence update loop is starting.")

# --- Main Execution ---
async def main():
    """Main function to start the bot."""
    if not config.BOT_TOKEN or config.BOT_TOKEN == "YOUR_DISCORD_BOT_TOKEN":
        logger.critical("❌ BOT TOKEN IS NOT SET in config.py! The bot cannot start.")
        return

    logger.info("Starting bot...")
    try:
        async with bot: # Use async context manager for bot
            await bot.start(config.BOT_TOKEN)
    except discord.LoginFailure:
        logger.critical("❌ Invalid Discord Bot Token! Please check your config.py.")
    except Exception as e:
        logger.critical(f"❌ An unexpected error occurred during bot startup: {e}", exc_info=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested via KeyboardInterrupt.")
    finally:
        logger.info("Bot has been shut down.")

