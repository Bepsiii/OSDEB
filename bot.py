# bot.py
"""
Main file for the Discord Bot.
Handles bot setup, event listeners, command loading, and core functionality including presence updates.
"""
import discord
from discord.ext import commands, tasks
import asyncio
import logging
import os 
import sys 

# Import configurations and services
import config # This is how config.py is imported
from gemini_service import GeminiService # Import the GeminiService class

# --- Logger Setup ---
# logging.basicConfig will be called in the __main__ block before main() runs.
logger = logging.getLogger(__name__)

class MyBot(commands.Bot):
    """Custom Bot class to encapsulate bot-specific attributes and methods."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize services here
        self.gemini_service = GeminiService()
        # If EconomyManager is initialized here, ensure GamesCog doesn't re-initialize
        # Or ensure GamesCog initializes it and attaches to self.bot as self.bot.economy_manager
        # For now, assuming GamesCog handles attaching self.bot.economy_manager

    async def setup_hook(self):
        """
        Asynchronous setup that is called when the bot is logged in but before it has connected to Discord.
        This is the ideal place to load extensions (cogs) and start background tasks.
        """
        logger.info("Running setup_hook...")
        await self.load_all_extensions()

        # Start background tasks after extensions are loaded
        if hasattr(config, 'PRESENCE_UPDATE_INTERVAL_SECONDS'): # Check if config var exists
            if not update_bot_status_task.is_running():
                update_bot_status_task.start()
        else:
            logger.warning("PRESENCE_UPDATE_INTERVAL_SECONDS not found in config. Presence task not started.")

    async def load_all_extensions(self):
        """Loads all cogs specified in the config file."""
        if not hasattr(config, 'COGS_TO_LOAD') or not config.COGS_TO_LOAD:
            logger.warning("COGS_TO_LOAD is not defined or is empty in config.py. No cogs will be loaded.")
            return
            
        logger.info(f"Attempting to load {len(config.COGS_TO_LOAD)} cogs...")
        for extension_path in config.COGS_TO_LOAD:
            try:
                await self.load_extension(extension_path)
                logger.info(f"✅ Successfully loaded extension: {extension_path}")
            except commands.ExtensionNotFound:
                logger.error(f"❌ Extension not found: {extension_path}. Make sure the file '{extension_path.replace('.', '/')}.py' exists and the path in COGS_TO_LOAD is correct (e.g., 'cogs.music').")
            except commands.ExtensionAlreadyLoaded:
                logger.warning(f"⚠️ Extension already loaded: {extension_path}.")
            except commands.NoEntryPointError:
                logger.error(f"❌ Extension '{extension_path}' has no setup function. Ensure it has an `async def setup(bot):` function.")
            except commands.ExtensionFailed as e:
                logger.error(f"❌ Failed to load extension {extension_path} (Error during its setup function): {e.original if hasattr(e, 'original') else e}", exc_info=True)
            except Exception as e: 
                logger.error(f"❌ An unexpected error occurred while loading {extension_path}: {e}", exc_info=True)

    async def on_ready(self):
        """Called when the bot is done preparing the data received from Discord."""
        logger.info(f"Logged in as {self.user.name} (ID: {self.user.id})")
        logger.info(f"Command Prefix: \"{getattr(config, 'COMMAND_PREFIX', '!')}\"") # Use getattr for safety
        if hasattr(config, 'OWNER_ID') and config.OWNER_ID:
            logger.info(f"Owner ID: {config.OWNER_ID}")
        logger.info(f"discord.py version: {discord.__version__}")
        logger.info(f"Python version: {sys.version.split(' ')[0]}") # sys is used here
        logger.info(f"Successfully logged in and bot is ready!")
        logger.info(f"Bot is in {len(self.guilds)} server(s).")
        # You can print a list of servers the bot is in for debugging if needed:
        # for guild in self.guilds:
        #     logger.debug(f" - {guild.name} (ID: {guild.id})")

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """
        Global command error handler.
        This is a fallback for errors not handled by cog-specific error handlers.
        """
        prefix = getattr(config, 'COMMAND_PREFIX', '!')

        if isinstance(error, commands.CommandNotFound):
            # logger.debug(f"Command not found: {ctx.message.content}") # Optional: log for debugging
            return # Often best to silently ignore CommandNotFound
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"You're missing a required argument: `{error.param.name}`. "
                           f"Use `{prefix}help {ctx.command.qualified_name}` for more info.")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"This command is on cooldown. Please try again in {error.retry_after:.2f} seconds.")
        elif isinstance(error, commands.CheckFailure): # Covers MissingPermissions, bot_has_permissions, NoPrivateMessage (if not handled by cog), etc.
            # More specific messages could be added here by checking error type further
            await ctx.send("You do not have the permission to use this command here, or a check failed.")
        elif isinstance(error, commands.UserInputError): # Broader category for input issues like BadArgument
             await ctx.send(f"Invalid input: {error}. Please check the command usage with `{prefix}help {ctx.command.qualified_name}`.")
        else:
            command_name = ctx.command.qualified_name if ctx.command else "Unknown Command"
            logger.error(f"Unhandled command error in '{command_name}' invoked by '{ctx.author}': {error}", exc_info=True)
            await ctx.send("An unexpected error occurred while running that command. The bot owner has been notified.")

# --- Bot Intents Setup ---
intents = discord.Intents.default()
intents.message_content = True  
intents.members = True          
intents.voice_states = True     
# intents.presences = False # Enable if needed for presence updates, requires enabling in Dev Portal & Bot settings

# --- Bot Instance ---
owner_id_val = None
if hasattr(config, 'OWNER_ID'):
    try:
        owner_id_val = int(config.OWNER_ID)
    except (ValueError, TypeError): # Catch TypeError if OWNER_ID is None or wrong type
        logger.error("OWNER_ID in config.py is not a valid integer. Owner-specific commands may not work.")

bot = MyBot(
    command_prefix=commands.when_mentioned_or(getattr(config, 'COMMAND_PREFIX', '!')), 
    intents=intents,
    help_command=None,  # Assuming a custom help command in a cog (e.g., cogs.help)
    owner_id=owner_id_val 
)

# --- Presence Update Task ---
@tasks.loop(seconds=getattr(config, 'PRESENCE_UPDATE_INTERVAL_SECONDS', 30))
async def update_bot_status_task():
    """Periodically updates the bot's presence."""
    default_activity_name = f"{getattr(config, 'COMMAND_PREFIX', '!')}help"
    activity_name = getattr(config, 'DEFAULT_PRESENCE_NAME', default_activity_name)
    activity_type_str = getattr(config, 'DEFAULT_PRESENCE_ACTIVITY_TYPE', "listening").lower()
    
    activity_type_map = {
        "playing": discord.ActivityType.playing, "streaming": discord.ActivityType.streaming,
        "listening": discord.ActivityType.listening, "watching": discord.ActivityType.watching,
        "competing": discord.ActivityType.competing,
    }
    selected_activity_type = activity_type_map.get(activity_type_str, discord.ActivityType.listening) # Default to listening

    song_title = None
    target_guild_id_for_presence = getattr(config, 'TARGET_GUILD_ID_FOR_PRESENCE', 0)

    if target_guild_id_for_presence and target_guild_id_for_presence != 0:
        music_cog = bot.get_cog("Music") # Assumes MusicV2 cog is named "Music"
        if music_cog and hasattr(music_cog, 'get_current_song_details'):
            try:
                current_song_obj = music_cog.get_current_song_details(target_guild_id_for_presence)
                if current_song_obj: song_title = current_song_obj.title
            except Exception as e: # Catch broad exceptions to prevent task crashing
                logger.error(f"Error fetching current song for presence: {e}", exc_info=False) # Log less verbosely

    if song_title:
        name_prefix = f"{getattr(config, 'MUSIC_PRESENCE_EMOJI', '🎶')} " if hasattr(config, 'MUSIC_PRESENCE_EMOJI') and config.MUSIC_PRESENCE_EMOJI else ""
        activity_name = f"{name_prefix}{song_title}"
        music_activity_type_str = getattr(config, 'MUSIC_PRESENCE_ACTIVITY_TYPE', "listening").lower()
        selected_activity_type = activity_type_map.get(music_activity_type_str, discord.ActivityType.listening)
    else: # Default presence
        name_prefix = f"{getattr(config, 'DEFAULT_PRESENCE_EMOJI', '🎧')} " if hasattr(config, 'DEFAULT_PRESENCE_EMOJI') and config.DEFAULT_PRESENCE_EMOJI else ""
        activity_name = f"{name_prefix}{getattr(config, 'DEFAULT_PRESENCE_NAME', default_activity_name)}"

    activity_name = activity_name[:128] # Ensure within Discord's character limits

    try:
        current_activity = bot.activity
        # Only change presence if it's different to avoid unnecessary API calls
        if not current_activity or current_activity.name != activity_name or current_activity.type != selected_activity_type:
            new_activity = discord.Activity(type=selected_activity_type, name=activity_name)
            # Add stream_url if activity type is streaming and URL is configured
            if selected_activity_type == discord.ActivityType.streaming and hasattr(config, 'STREAMING_URL_FOR_PRESENCE'):
                new_activity.url = config.STREAMING_URL_FOR_PRESENCE
            await bot.change_presence(activity=new_activity)
            logger.debug(f"Presence updated: {selected_activity_type.name} {activity_name}")
    except Exception as e:
        logger.error(f"Failed to update bot presence: {e}", exc_info=False) # Log less verbosely for task errors

@update_bot_status_task.before_loop
async def before_update_bot_status_task():
    """Ensures the bot is ready before starting the presence update loop."""
    await bot.wait_until_ready()
    logger.info("Bot presence update loop is starting.")


# --- Gemini Command (Defined globally) ---
@bot.command(name='gemini', help="Ask a question or give a prompt to the Gemini AI.")
@commands.cooldown(1, getattr(config, 'GEMINI_COMMAND_COOLDOWN_SECONDS', 10), commands.BucketType.user)
async def gemini_command(ctx: commands.Context, *, prompt: str):
    """Command to interact with the Gemini AI model."""
    if not bot.gemini_service or not bot.gemini_service.model:
        await ctx.send(getattr(config, 'GEMINI_ERROR_MESSAGE', "Sorry, Gemini AI is currently unavailable."))
        logger.warning(f"Gemini command used by {ctx.author} but service is not available or model not loaded.")
        return

    if not prompt.strip(): # Check if prompt is empty or just whitespace
        await ctx.send("Please provide a prompt or question for Gemini!")
        return

    async with ctx.typing(): # Show "Bot is typing..."
        try:
            logger.info(f"Gemini command invoked by {ctx.author} with prompt (first 50 chars): '{prompt[:50]}...'")
            response_text = await bot.gemini_service.generate_content(prompt)

            if response_text:
                max_len = getattr(config, 'DISCORD_MESSAGE_MAX_LENGTH', 2000)
                for i in range(0, len(response_text), max_len):
                    chunk = response_text[i:i + max_len]
                    await ctx.send(chunk)
                    if len(response_text) > max_len and i + max_len < len(response_text):
                        await asyncio.sleep(0.5) # Small delay between chunks to avoid local rate limits/spam
            else:
                await ctx.send(getattr(config, 'GEMINI_ERROR_MESSAGE', "Sorry, I couldn't get a response from Gemini for that prompt."))
                logger.warning(f"Gemini returned no content for prompt by {ctx.author}.")

        except Exception as e:
            logger.error(f"Error in Gemini command for {ctx.author}: {e}", exc_info=True)
            await ctx.send(getattr(config, 'GEMINI_ERROR_MESSAGE', "Sorry, an error occurred while processing your request with Gemini."))


# --- Main Execution ---
async def main():
    """Main function to start the bot."""
    bot_token = getattr(config, 'BOT_TOKEN', None)
    if not bot_token or bot_token == "YOUR_DISCORD_BOT_TOKEN": # Placeholder check
        logger.critical("❌ BOT TOKEN IS NOT SET or is the placeholder value in config.py! The bot cannot start.")
        print("CRITICAL: BOT TOKEN IS NOT SET or is the placeholder value in config.py! The bot cannot start.")
        return
    if len(bot_token) < 50: # Basic sanity check for token length
        logger.critical(f"❌ BOT TOKEN in config.py appears to be too short (Length: {len(bot_token)}). Please ensure it's correct.")
        print(f"CRITICAL: BOT TOKEN in config.py appears to be too short. Length: {len(bot_token)}")
        return

    # Removed the explicit token print for cleanup, relying on logs.
    # logger.info(f"Attempting to start with token prefix: '{bot_token[:10]}' and suffix: '{bot_token[-10:]}'")

    logger.info("Attempting to start the bot...")
    try:
        # The bot.start() method will internally call setup_hook before connecting to gateway.
        await bot.start(bot_token)
    except discord.LoginFailure:
        logger.critical("❌ Invalid Discord Bot Token! Discord rejected the token. Please double-check it in your config.py and ensure it's freshly copied from the Developer Portal.")
        print("CRITICAL: Invalid Discord Bot Token! Discord rejected the token.")
    except discord.PrivilegedIntentsRequired as e:
        logger.critical(f"❌ Privileged Intents (e.g., Members, Presence) are required but not enabled for this bot in the Discord Developer Portal. Details: {e}")
        print(f"CRITICAL: Privileged Intents required but not enabled. Details: {e}")
    except Exception as e:
        logger.critical(f"❌ An unexpected error occurred during bot startup: {e}", exc_info=True)
        print(f"CRITICAL: An unexpected error occurred during bot startup: {e}")

if __name__ == "__main__":
    # Configure basic logging. This will show logs from discord.py and your bot.
    log_level_str = getattr(config, 'LOG_LEVEL', "INFO").upper()
    # Ensure log_level_str is a valid level name for logging.getLevelName
    try:
        numeric_level = logging.getLevelName(log_level_str)
        if not isinstance(numeric_level, int): # Fallback if getLevelName returns string for invalid level
            logger.warning(f"Invalid LOG_LEVEL '{log_level_str}' in config.py. Defaulting to INFO.")
            numeric_level = logging.INFO
    except ValueError: # If getLevelName raises ValueError for an unknown level string
        logger.warning(f"Unknown LOG_LEVEL string '{log_level_str}' in config.py. Defaulting to INFO.")
        numeric_level = logging.INFO
    
    # Setup for console logging
    console_handler = logging.StreamHandler(sys.stdout) # Explicitly use stdout
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] [%(name)s] %(message)s', # Added [%(name)s]
        '%Y-%m-%d %H:%M:%S'
    ))
    
    # Setup for file logging (optional, but good for persistence)
    log_dir = "logs" # Relative to where bot.py is run
    file_handler = None
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir)
        except OSError as e:
            print(f"Warning: Could not create log directory '{log_dir}': {e}. File logging will be disabled.")
            log_dir = None 
    
    if log_dir:
        try:
            file_handler = logging.FileHandler(filename=os.path.join(log_dir, 'bot.log'), encoding='utf-8', mode='a') # Use 'a' to append
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s [%(levelname)s] [%(name)s] %(message)s', # Added [%(name)s]
                '%Y-%m-%d %H:%M:%S'
            ))
        except Exception as e:
            print(f"Warning: Could not create file handler for logging: {e}. File logging may be disabled.")
            file_handler = None

    handlers_list = [console_handler]
    if file_handler:
        handlers_list.append(file_handler)
        
    logging.basicConfig(level=numeric_level, handlers=handlers_list)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested via KeyboardInterrupt.")
    except Exception as e: 
        logger.critical(f"❌ Critical error during asyncio.run(main()): {e}", exc_info=True)
    finally:
        logger.info("Bot process has been shut down.")
