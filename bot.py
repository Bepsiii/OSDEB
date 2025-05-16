# bot.py
"""
Main file for the Discord Bot.
Handles bot setup, event listeners, command loading, and core functionality including presence updates.
"""
import discord
from discord.ext import commands, tasks
import asyncio
import logging

# Import configurations and services
import config # This is how config.py is imported
# ... (other imports like GeminiService, MusicV2 if directly imported) ...

# --- Logger Setup ---
# Note: BasicConfig will be called in the __main__ block before main() runs.
logger = logging.getLogger(__name__)


class MyBot(commands.Bot):
    # ... (your MyBot class definition from the previous version) ...
    async def setup_hook(self):
        logger.info("Running setup_hook...")
        await self.load_all_extensions()

    async def load_all_extensions(self):
        logger.info(f"Attempting to load {len(config.COGS_TO_LOAD)} cogs...")
        for extension_path in config.COGS_TO_LOAD:
            try:
                await self.load_extension(extension_path)
                logger.info(f"✅ Successfully loaded extension: {extension_path}")
            except commands.ExtensionNotFound:
                logger.error(f"❌ Extension not found: {extension_path}. Make sure the file exists and the path in COGS_TO_LOAD is correct (e.g., 'cogs.music').")
            except commands.ExtensionAlreadyLoaded:
                logger.warning(f"⚠️ Extension already loaded: {extension_path}.")
            except commands.NoEntryPointError:
                logger.error(f"❌ Extension has no setup function: {extension_path}. Make sure it has an `async def setup(bot):` function.")
            except commands.ExtensionFailed as e:
                logger.error(f"❌ Failed to load extension {extension_path} (Error during setup): {e.__cause__ or e}", exc_info=True)
            except Exception as e:
                logger.error(f"❌ An unexpected error occurred while loading {extension_path}: {e}", exc_info=True)

    async def on_ready(self):
        logger.info(f'Bot connected as {self.user} (ID: {self.user.id})')
        logger.info(f'Command Prefix: "{config.COMMAND_PREFIX}"')
        logger.info(f'Owner ID: {config.OWNER_ID}')
        logger.info(f'discord.py version: {discord.__version__}')
        logger.info('Bot is ready and online!')

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"You're missing a required argument: `{error.param.name}`. "
                           f"Use `{config.COMMAND_PREFIX}help {ctx.command.qualified_name}` for more info.")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"This command is on cooldown. Please try again in {error.retry_after:.2f} seconds.")
        elif isinstance(error, commands.CheckFailure):
            await ctx.send("You do not have the permission to use this command, or a check failed.")
        else:
            logger.error(f"Unhandled command error in '{ctx.command.qualified_name if ctx.command else 'Unknown Command'}' "
                         f"invoked by '{ctx.author}': {error}", exc_info=True)
            await ctx.send("An unexpected error occurred while running that command. Please try again later.")

# --- Bot Intents Setup ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True


# --- Bot Instance ---
bot = MyBot(
    command_prefix=commands.when_mentioned_or(config.COMMAND_PREFIX),
    intents=intents,
    help_command=None,
    owner_id=config.OWNER_ID
)

# --- Main Execution ---
async def main():
    """Main function to start the bot."""
    if not config.BOT_TOKEN or config.BOT_TOKEN == "YOUR_DISCORD_BOT_TOKEN":
        # This logger.critical might not show if basicConfig hasn't run yet for this specific log call,
        # but the print below it will.
        logger.critical("❌ BOT TOKEN IS NOT SET or is the placeholder value in config.py! The bot cannot start.")
        print("CRITICAL: BOT TOKEN IS NOT SET or is the placeholder value in config.py! The bot cannot start.")
        return
    if len(config.BOT_TOKEN) < 50: # Basic sanity check for token length
        logger.critical(f"❌ BOT TOKEN in config.py appears to be too short. Please ensure it's correct. Length: {len(config.BOT_TOKEN)}")
        print(f"CRITICAL: BOT TOKEN in config.py appears to be too short. Length: {len(config.BOT_TOKEN)}")
        return

    # --- !!! MODIFIED DEBUGGING LINE !!! ---
    # Using print() to ensure it shows up regardless of logging config state at this exact point.
    print(f"[DEBUG TOKEN CHECK] Attempting to start with token prefix: '{config.BOT_TOKEN[:10]}' and suffix: '{config.BOT_TOKEN[-10:]}'")
    # --- !!! END OF MODIFIED DEBUGGING LINE !!! ---

    logger.info("Starting bot...")
    try:
        async with bot:
            await bot.start(config.BOT_TOKEN)
    except discord.LoginFailure:
        logger.critical("❌ Invalid Discord Bot Token! Discord rejected the token. Please double-check it in your config.py and ensure it's freshly copied from the Developer Portal.")
        print("CRITICAL: Invalid Discord Bot Token! Discord rejected the token.") # Also print this
    except discord.PrivilegedIntentsRequired:
        logger.critical("❌ Privileged Intents (like Members or Presence) are required but not enabled for this bot in the Discord Developer Portal.")
        print("CRITICAL: Privileged Intents (like Members or Presence) are required but not enabled.")
    except Exception as e:
        logger.critical(f"❌ An unexpected error occurred during bot startup: {e}", exc_info=True)
        print(f"CRITICAL: An unexpected error occurred during bot startup: {e}")

if __name__ == "__main__":
    # --- MOVED LOGGING CONFIG TO THE TOP OF THIS BLOCK ---
    log_level_str = getattr(config, 'LOG_LEVEL', "INFO").upper()
    numeric_level = getattr(logging, log_level_str, logging.INFO)
    logging.basicConfig(level=numeric_level,
                        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    # --- END OF MOVED LOGGING CONFIG ---

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested via KeyboardInterrupt.")
    except Exception as e:
        logger.critical(f"❌ Critical error during asyncio.run(main()): {e}", exc_info=True)
    finally:
        logger.info("Bot process has been shut down.")

