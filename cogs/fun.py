# cogs/fun.py
"""
A cog for fun and miscellaneous commands for the Discord bot.
"""
import discord
from discord.ext import commands
import random
import os
import logging
from typing import Optional

# Assuming your config.py is in the parent directory or accessible via your Python path
# If main_bot.py and config.py are in the root, and cogs is a subdirectory:
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config # Now it should find config.py

# --- Logger Setup ---
logger = logging.getLogger(__name__)

# --- Constants ---
SUPPORTED_MEDIA_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.gif', '.mp4', '.mov', '.avi', '.mkv', '.webp')

class Fun(commands.Cog):
    """
    Cog containing fun commands like jokes, random media, and more.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        logger.info("Fun Cog loaded.")

        # Validate paths from config
        self._validate_path("SNAP_MEDIA_FOLDER", getattr(config, 'SNAP_MEDIA_FOLDER', './Images'))
        self._validate_path("FISH_IMAGES_FOLDER", getattr(config, 'FISH_IMAGES_FOLDER', './fish'))

    def _validate_path(self, config_name: str, path: str):
        """Helper to check if a configured path exists."""
        if not os.path.isdir(path):
            logger.warning(
                f"Path for {config_name} ('{path}') in config.py does not exist or is not a directory. "
                f"Commands relying on this path may not function correctly."
            )
            # Optionally, create the directory if it doesn't exist
            # try:
            #     os.makedirs(path, exist_ok=True)
            #     logger.info(f"Created directory: {path}")
            # except OSError as e:
            #     logger.error(f"Could not create directory {path}: {e}")


    @commands.command(name="example_command", help="A simple example command.")
    async def example_command(self, ctx: commands.Context):
        """
        Sends a predefined example message.
        This serves as a template or test for a basic command.
        """
        await ctx.send("This is an example of a custom command in the Fun cog!")
        logger.info(f"Example command used by {ctx.author.name} in {ctx.guild.name if ctx.guild else 'DM'}.")

    @commands.command(name="joke", help="Tells a random joke.")
    @commands.cooldown(1, 5, commands.BucketType.user) # 1 use per 5 seconds per user
    async def joke(self, ctx: commands.Context):
        """
        Sends a random joke from a predefined list in config.py.
        """
        jokes_list = getattr(config, 'JOKES_LIST', [])
        if not jokes_list:
            await ctx.send("I'm all out of jokes at the moment! Please ask my owner to add some.")
            logger.warning("Joke command used, but JOKES_LIST is empty or not found in config.")
            return

        await ctx.send(random.choice(jokes_list))
        logger.info(f"Joke command used by {ctx.author.name}.")

    @commands.command(name="snap", help="Sends a random image or video from the configured media folder.")
    @commands.cooldown(1, 10, commands.BucketType.channel) # 1 use per 10 seconds per channel
    async def snap(self, ctx: commands.Context):
        """
        Sends a random media file (image/video) from the folder specified by SNAP_MEDIA_FOLDER in config.py.
        """
        media_folder = getattr(config, 'SNAP_MEDIA_FOLDER', './Images') # Default if not in config

        if not os.path.exists(media_folder) or not os.path.isdir(media_folder):
            await ctx.send(f"The media folder ('{media_folder}') seems to be missing. Please tell my owner!")
            logger.error(f"Snap command: Media folder '{media_folder}' not found or not a directory.")
            return

        try:
            media_files = [
                f for f in os.listdir(media_folder)
                if os.path.isfile(os.path.join(media_folder, f)) and f.lower().endswith(SUPPORTED_MEDIA_EXTENSIONS)
            ]
        except OSError as e:
            await ctx.send("I had trouble accessing the media folder. Please try again later.")
            logger.error(f"Snap command: OSError when listing files in '{media_folder}': {e}")
            return


        if not media_files:
            await ctx.send(f"The media folder ('{media_folder}') is empty or has no supported files "
                           f"({', '.join(SUPPORTED_MEDIA_EXTENSIONS)}).")
            logger.warning(f"Snap command: No suitable media files found in '{media_folder}'.")
            return

        random_media_filename = random.choice(media_files)
        file_path = os.path.join(media_folder, random_media_filename)

        try:
            async with ctx.typing(): # Show "Bot is typing..."
                with open(file_path, "rb") as media_file_obj:
                    discord_file = discord.File(media_file_obj, filename=random_media_filename)
                    await ctx.send(file=discord_file)
            logger.info(f"Snap command: Sent '{random_media_filename}' to {ctx.author.name}.")
        except discord.HTTPException as e:
            await ctx.send("I couldn't send the media. It might be too large or there was a Discord issue.")
            logger.error(f"Snap command: Discord HTTPException while sending '{file_path}': {e}")
        except FileNotFoundError:
            await ctx.send("Oops! The selected media file seems to have vanished. Please try again.")
            logger.error(f"Snap command: FileNotFoundError for '{file_path}'. This shouldn't happen if listing worked.")
        except Exception as e:
            await ctx.send("An unexpected error occurred while trying to send the media.")
            logger.error(f"Snap command: Unexpected error sending '{file_path}': {e}", exc_info=True)

    @commands.command(name="fish", help="Sends a random fishing-related image to a user via DM.")
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def fish(self, ctx: commands.Context, user: discord.Member):
        """
        Sends a random image from the FISH_IMAGES_FOLDER (configured in config.py)
        to the specified user via DM, along with a friendly message in the channel.
        """
        if user.bot:
            await ctx.send("You can't fish for bots!")
            return
        if user == ctx.author:
            await ctx.send("You can't fish for yourself! Try fishing for someone else.")
            return

        fish_images_folder = getattr(config, 'FISH_IMAGES_FOLDER', './fish') # Default if not in config

        if not os.path.exists(fish_images_folder) or not os.path.isdir(fish_images_folder):
            await ctx.send(f"The fish images folder ('{fish_images_folder}') is missing. My owner needs to fix this!")
            logger.error(f"Fish command: Fish images folder '{fish_images_folder}' not found.")
            return

        try:
            fish_image_files = [
                f for f in os.listdir(fish_images_folder)
                if os.path.isfile(os.path.join(fish_images_folder, f)) and f.lower().endswith(SUPPORTED_MEDIA_EXTENSIONS)
            ]
        except OSError as e:
            await ctx.send("I had trouble finding a fish picture. Please try again later.")
            logger.error(f"Fish command: OSError when listing files in '{fish_images_folder}': {e}")
            return

        if not fish_image_files:
            await ctx.send(f"I couldn't find any fish pictures in '{fish_images_folder}'. Looks like they all swam away!")
            logger.warning(f"Fish command: No suitable fish images found in '{fish_images_folder}'.")
            return

        random_fish_image_filename = random.choice(fish_image_files)
        file_path = os.path.join(fish_images_folder, random_fish_image_filename)

        dm_message = getattr(config, 'FISH_DM_MESSAGE', "You've been fished! Hope you like this catch! 🎣")
        channel_confirm_message = getattr(config, 'FISH_CHANNEL_CONFIRM_MESSAGE', "{user_mention} just got a surprise fish in their DMs!")

        try:
            async with ctx.typing():
                with open(file_path, "rb") as fish_file_obj:
                    discord_file = discord.File(fish_file_obj, filename=random_fish_image_filename)
                    await user.send(dm_message, file=discord_file)
            await ctx.send(channel_confirm_message.format(user_mention=user.mention))
            logger.info(f"Fish command: Sent '{random_fish_image_filename}' to {user.name} (DM'd by {ctx.author.name}).")
        except discord.Forbidden:
            await ctx.send(f"I can't send DMs to {user.mention}. They might have DMs disabled or have blocked me.")
            logger.warning(f"Fish command: Forbidden to DM {user.name} ({user.id}).")
        except discord.HTTPException as e:
            await ctx.send("An error occurred while trying to send the fish. It might be too big or Discord had an issue.")
            logger.error(f"Fish command: Discord HTTPException while sending fish to {user.name}: {e}")
        except FileNotFoundError:
            await ctx.send("Oh no! The fish picture swam away just as I was about to send it. Try again!")
            logger.error(f"Fish command: FileNotFoundError for '{file_path}'.")
        except Exception as e:
            await ctx.send("An unexpected error occurred while trying to send the fish.")
            logger.error(f"Fish command: Unexpected error sending fish to {user.name}: {e}", exc_info=True)

    @commands.command(name="say", help="Makes the bot say a message and deletes the command invocation.")
    @commands.has_permissions(manage_messages=True) # Optional: restrict to users who can manage messages
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def say(self, ctx: commands.Context, *, message_to_say: str):
        """
        The bot repeats the message provided by the user.
        The original command message is deleted if the bot has permission.

        Usage: !say <your message here>
        """
        if not message_to_say:
            await ctx.send("What should I say? Please provide a message.", delete_after=10)
            return

        try:
            await ctx.message.delete()
        except discord.Forbidden:
            logger.warning(f"Say command: Bot lacks 'Manage Messages' permission in '{ctx.channel.name}' of '{ctx.guild.name if ctx.guild else 'DM'}' to delete {ctx.author.name}'s message.")
            # Optionally send a quiet notification if deletion fails, or just log it.
            # await ctx.send("I couldn't delete your command message (missing permissions), but here's your message:", delete_after=10)
        except discord.NotFound:
            logger.info("Say command: Original message already deleted.")
        except discord.HTTPException as e:
            logger.error(f"Say command: Failed to delete original message due to HTTPException: {e}")

        await ctx.send(message_to_say)
        logger.info(f"Say command: {ctx.author.name} made bot say: '{message_to_say[:50]}...'")

    @say.error
    async def say_error(self, ctx: commands.Context, error: commands.CommandError):
        """Error handler specific to the 'say' command."""
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You don't have the necessary permissions (Manage Messages) to use this command here.", delete_after=10)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"You forgot to tell me what to say! Usage: `{ctx.prefix}say <message>`", delete_after=10)
        else:
            logger.error(f"Error in 'say' command by {ctx.author}: {error}", exc_info=True)
            await ctx.send("Something went wrong with the say command.", delete_after=10)


# Async setup function to add the cog to the bot
async def setup(bot: commands.Bot):
    """
    This function is called by discord.py when loading the cog.
    It's essential for the cog to be registered with the bot.
    """
    # Create an instance of the Fun cog and add it to the bot
    await bot.add_cog(Fun(bot))
    logger.info("Fun cog has been setup and added to the bot.")

