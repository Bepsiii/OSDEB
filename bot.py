import discord
from discord.ext import commands, tasks
import config
import asyncio
import google.generativeai as genai

# --- Bot Setup ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(
    command_prefix="debbie ",
    intents=intents,
    help_command=None,
    owner_id=407648396828999681  # YOUR USER ID HERE
)

# --- Gemini API Setup ---
genai.configure(api_key=config.GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

@bot.event
async def on_ready():
    print(f'Bot connected as {bot.user}')
    update_presence.start()

@tasks.loop(seconds=10)
async def update_presence():
    try:
        music_cog = bot.get_cog('Music')
        if music_cog:
            current_song = music_cog.get_current_song(1182678980722167928)
            activity = discord.Activity(
                type=discord.ActivityType.listening,
                name=current_song if current_song else "silence"
            )
            await bot.change_presence(activity=activity)
    except Exception as e:
        print(f"Presence error: {e}")

async def load_extensions():
    extensions = ["cogs.music", "cogs.fun", "cogs.games", "cogs.voice", "cogs.voicekick", "cogs.store"]
    for ext in extensions:
        try:
            await bot.load_extension(ext)
            print(f"✅ Loaded: {ext}")
        except Exception as e:
            print(f"❌ Failed to load {ext}: {e}")

@bot.command(name='gemini')
async def gemini_command(ctx, *, prompt: str):
    await ctx.defer()
    try:
        response = model.generate_content(prompt)
        if text := response.text:
            chunks = [text[i:i+2000] for i in range(0, len(text), 2000)]
            for chunk in chunks:
                await ctx.send(chunk)
    except Exception as e:
        pass  # Silent failure

async def main():
    async with bot:
        await load_extensions()
        try:
            await bot.start(config.BOT_TOKEN)
        except discord.LoginFailure:
            print("❌ Invalid bot token!")

if __name__ == "__main__":
    asyncio.run(main())