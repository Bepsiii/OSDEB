import discord
from discord.ext import commands
import random
import os
from typing import Optional

class Fun(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command()
    async def escort(self, ctx: commands.Context):
        """Send a location link."""
        await ctx.send("cum find me here xx https://maps.app.goo.gl/GPqc6AfCEDakW93p7")

    @commands.command()
    async def cum(self, ctx: commands.Context):
        """Correct the user with a humorous message."""
        await ctx.send("tom you fucking retard, it's play, not cum to play music")

    @commands.command()
    async def tom(self, ctx: commands.Context):
        """Send a humorous message about Tom."""
        await ctx.send("BALDY BALDY OVER THERE, WHAT'S IT LIKE TO HAVE NO HAIR, IS IT HOT OR IS IT COLD, I DON'T KNOW CAUSE I'M NOT BALD")

    @commands.command()
    async def joke(self, ctx: commands.Context):
        """Tell a random joke."""
        jokes = [
            "Why did the scarecrow win an award? Because he was outstanding in his field!",
            "What do you call fake spaghetti? An impasta!",
            "How do you organize a space party? You planet!",
            "What do you call a retard? Cody Wade!"
        ]
        await ctx.send(random.choice(jokes))

    @commands.command()
    async def snap(self, ctx: commands.Context):
        """Send a random image or video from the Images folder."""
        media_folder = "./Images"  # Path to the folder containing media files

        if not os.path.exists(media_folder):
            await ctx.send("The 'Images' folder does not exist in the bot's directory.")
            return

        supported_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.mp4', '.mov', '.avi', '.mkv')
        media_files = [f for f in os.listdir(media_folder) if f.lower().endswith(supported_extensions)]

        if not media_files:
            await ctx.send("The 'Images' folder is empty or contains unsupported files.")
            return

        random_media = random.choice(media_files)
        file_path = os.path.join(media_folder, random_media)

        try:
            with open(file_path, "rb") as media:
                await ctx.send(file=discord.File(media, filename=random_media))
        except Exception as e:
            await ctx.send(f"Error sending file: {e}")

    @commands.command()
    async def fish(self, ctx: commands.Context, user: discord.Member):
        """Send a random fishing image to a user with a message."""
        fish_folder = "./fish"

        if not os.path.exists(fish_folder) or not os.listdir(fish_folder):
            await ctx.send("No fish images found.")
            return

        fish_image = random.choice(os.listdir(fish_folder))
        file_path = os.path.join(fish_folder, fish_image)

        try:
            await user.send("Get fished, idiot!", file=discord.File(file_path))
            await ctx.send(f"{user.mention} just got fished!")
        except discord.Forbidden:
            await ctx.send("I can't send messages to this user.")
        except discord.HTTPException as e:
            await ctx.send(f"An error occurred while sending the fish: {e}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred: {e}")

    @commands.command()
    async def say(self, ctx: commands.Context, *, message_to_say: str):
        """
        Make the bot say a message and delete the command message.
        Usage: debbie say <message>
        """
        try:
            await ctx.message.delete()  # Delete the command message
        except discord.Forbidden:
            await ctx.send("I don't have permission to delete messages here, but I'll still say the message.", delete_after=10)
        except discord.NotFound:
            await ctx.send("The command message was already deleted, but I'll still say the message.", delete_after=10)
        except discord.HTTPException as e:
            await ctx.send(f"Failed to delete the command message: {e}. I'll still say the message.", delete_after=10)

        await ctx.send(message_to_say)  # Send the user's message

# Async setup function to add the cog
async def setup(bot: commands.Bot):
    await bot.add_cog(Fun(bot))