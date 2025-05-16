import discord
from discord import Activity, ActivityType
from cogs.music import get_current_song  # Import the function directly

async def update_bot_presence(bot: discord.Client):
    """
    Update the bot's presence based on the currently playing song.

    Args:
        bot (discord.Client): The Discord bot instance.
    """
    try:
        song = await get_current_song()  # Await the async function
        if song:
            # Update presence to show the song is being played
            await bot.change_presence(activity=Activity(type=ActivityType.listening, name=song))
        else:
            # Clear presence if no song is playing
            await bot.change_presence(activity=None)
    except Exception as e:
        print(f"Error updating bot presence: {e}")  # Log any errors