# config.py
"""
Configuration file for the Discord Bot.
All sensitive information and bot settings should be stored here.
"""

# --- Discord Bot Configuration ---
BOT_TOKEN = "YOUR_DISCORD_BOT_TOKEN"  # Replace with your actual bot token
COMMAND_PREFIX = "!"
OWNER_ID =   # Replace with your Discord User ID
PRESENCE_UPDATE_INTERVAL_SECONDS = 10  # How often to update the bot's presence
TARGET_GUILD_ID_FOR_PRESENCE =  # Guild ID for music presence, make None if not needed or dynamic

# --- Gemini API Configuration ---
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"  # Replace with your actual Gemini API key
GEMINI_MODEL_NAME = "gemini-1.5-flash-latest"  # Or "gemini-pro", "gemini-1.0-pro", etc.
GEMINI_MAX_OUTPUT_TOKENS = 2000 # Maximum tokens for Gemini response
GEMINI_TEMPERATURE = 0.7 # Controls randomness (0.0 to 1.0)
GEMINI_TOP_P = 1.0 # Nucleus sampling
GEMINI_TOP_K = 1 # Top-k sampling






# --- Bot Presence Configuration ---
PRESENCE_UPDATE_INTERVAL_SECONDS = 30  # How often to update the bot's presence (e.g., every 30 seconds)

# Target guild ID for music presence. If None, a default global presence will be used.
# Replace 0 with your actual target guild ID if you want music presence from a specific server.
TARGET_GUILD_ID_FOR_PRESENCE = 0 # Example: 123456789012345678 (Your Server's ID)

# Default presence if no song is playing in the target guild or if no target guild is set.
DEFAULT_PRESENCE_ACTIVITY_TYPE = "listening"  # "playing", "watching", "listening", "competing"
DEFAULT_PRESENCE_NAME = "!help for commands" # e.g., "silence", "your commands", "the server"
DEFAULT_PRESENCE_EMOJI = "🎧" # Optional emoji for default presence

# Music presence specific settings
MUSIC_PRESENCE_ACTIVITY_TYPE = "listening" # "listening" is most common for music
MUSIC_PRESENCE_EMOJI = "🎶" # Optional emoji for music presence







# --- Voice Interrupt Cog Configuration ---
VOICE_INTERRUPT_SOUND_PATH = "./sounds/interrupt_sound.mp3"  # Path to the sound file played for interruption
                                                          # Ensure this file exists or the feature won't play sound.
                                                          # Example: create a 'sounds' folder in your bot's root.
VOICE_INTERRUPT_FFMPEG_OPTIONS = {
    'options': '-vn -b:a 128k', # No video, audio bitrate 128k
    # 'executable': "ffmpeg" # Optional: if ffmpeg is not in PATH, specify full path
}
VOICE_INTERRUPT_INITIAL_DELAY_SECONDS = 1.5 # How long to wait after bot joins before first check
VOICE_INTERRUPT_CHECK_INTERVAL_SECONDS = 0.75 # How often to check if the target is unmuted

VOICE_SET_TARGET_ADMIN_ONLY = True # If True, only users with 'Manage Guild' can use set/clear target commands
VOICE_SET_TARGET_COOLDOWN = 10 # Seconds cooldown for settarget/cleartarget commands per guild

# --- Voice Interrupt Cog: Messages ---
VOICE_MSG_TARGET_SET = "🎯 Target user for interruption set to **{target_name}** in this server."
VOICE_MSG_TARGET_CLEARED = "🎯 Interrupt target has been cleared for this server."
VOICE_MSG_NO_TARGET_TO_CLEAR = "ℹ️ No interrupt target is currently set for this server."
VOICE_MSG_NO_PERMISSION_TARGET_CMD = "❌ You don't have the required permissions (Manage Guild) to set or clear interrupt targets."
VOICE_MSG_GENERIC_CMD_ERROR = "❗ An unexpected error occurred with that command."





# --- Cogs Configuration ---
# List of cogs to load. Assumes they are in a 'cogs' directory.
# For example, "cogs.music" will load 'cogs/music.py'
COGS_TO_LOAD = [
    "cogs.music",
    "cogs.fun",
    "cogs.games",
    "cogs.voice",
    "cogs.store",
    # Add more cogs here as needed
]

# --- Logging Configuration ---
LOG_LEVEL = "INFO" # Set to "DEBUG" for more detailed logs

# --- Message Configuration ---
DISCORD_MESSAGE_MAX_LENGTH = 2000 # Discord's character limit per message
GEMINI_ERROR_MESSAGE = "Sorry, I encountered an error trying to process your request with Gemini."






# --- Fun Cog: Jokes Configuration ---
JOKES_LIST = [
    "Why did the scarecrow win an award? Because he was outstanding in his field!",
    "What do you call fake spaghetti? An impasta!",
    "How do you organize a space party? You planet!",
    "Why don't programmers like nature? It has too many bugs.",
    "What did the zero say to the eight? Nice belt!",
    "Why was the math book sad? Because it had too many problems.",
    # Add more jokes here
]

# --- Fun Cog: Snap Command Configuration ---
# Path to the folder containing media files for the !snap command
# Use an absolute path or a path relative to where your main_bot.py runs
SNAP_MEDIA_FOLDER = "./Images"  # Example: "C:/Users/YourUser/DiscordBot/Media/Snaps" or "/home/user/discord_bot/media/snaps"

# --- Fun Cog: Fish Command Configuration ---
# Path to the folder containing fish images for the !fish command
FISH_IMAGES_FOLDER = "./fish" # Example: "./assets/fish_pics"

# Customizable messages for the !fish command
FISH_DM_MESSAGE = "You've been fished! Hope you like this catch! 🎣"
FISH_CHANNEL_CONFIRM_MESSAGE = "{user_mention} just got a surprise fish in their DMs! 🐟"







# --- Fun Cog: Meme Command Configuration ---

# --- Economy Configuration ---
ECONOMY_FILE_PATH = "data/economy.json"  # Path to the JSON file storing user balances (ensure 'data' directory exists or is writable)
ECONOMY_DEFAULT_BALANCE = 100  # Default balance for new users

# --- General Game Settings ---
ALLOW_GAMES_IN_DMS = False # Whether game commands can be used in DMs
GAMES_MIN_BET_MESSAGE = "Minimum bet is {min_bet} coins."
GAMES_INSUFFICIENT_FUNDS_MESSAGE = "You don't have enough coins! Your current balance: {balance} coins."
GAMES_OPPONENT_INSUFFICIENT_FUNDS_MESSAGE = "{opponent_name} doesn't have enough coins to accept the bet (Their balance: {opponent_balance})."
GAMES_BALANCE_MESSAGE = "{user_mention}'s balance: **{balance}** coins."

# --- Connect 4 Configuration ---
CONNECT4_MIN_BET = 1
CONNECT4_GAME_TIMEOUT_SECONDS = 300.0  # 5 minutes
CONNECT4_COOLDOWN_SECONDS = 30 # Cooldown per channel for starting a new game
CONNECT4_EMBED_COLOR = 0x8A2BE2 # Discord color (integer) or discord.Color.purple()
CONNECT4_PLAYER1_EMOJI = "🔴"
CONNECT4_PLAYER2_EMOJI = "🔵"
CONNECT4_EMPTY_EMOJI = "⚪" # Or "⚫" for a black background effect
CONNECT4_CANNOT_PLAY_SELF_MESSAGE = "You can't play Connect 4 against yourself!"
CONNECT4_CANNOT_PLAY_BOT_MESSAGE = "You can't challenge a bot to Connect 4!"

# --- Blackjack Configuration ---
BLACKJACK_MIN_BET = 5
BLACKJACK_GAME_TIMEOUT_SECONDS = 180.0  # 3 minutes
BLACKJACK_COOLDOWN_SECONDS = 10 # Cooldown per user
BLACKJACK_EMBED_COLOR = 0x2ECC71 # discord.Color.green()
BLACKJACK_CARD_RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
BLACKJACK_CARD_SUITS = ["♠️", "♣️", "♥️", "♦️"] # Emojis for suits
BLACKJACK_HIDDEN_CARD_EMOJI = "❓" # Emoji for the dealer's hidden card
BLACKJACK_NATURAL_PAYOUT_MULTIPLIER = 2.5 # e.g., bet 10, win 25 (15 profit + 10 bet back)
BLACKJACK_WIN_PAYOUT_MULTIPLIER = 2.0     # e.g., bet 10, win 20 (10 profit + 10 bet back)

# --- Roulette Configuration ---
ROULETTE_MIN_BET = 10
ROULETTE_GAME_TIMEOUT_SECONDS = 180.0  # 3 minutes
ROULETTE_MODAL_TIMEOUT_SECONDS = 120.0 # Timeout for the number input modal
ROULETTE_COOLDOWN_SECONDS = 15 # Cooldown per user
ROULETTE_GIF_PATH = "assets/gifs/roulette_spin.gif"  # Relative path to your roulette spinning GIF (ensure 'assets/gifs' directory and file exist)
ROULETTE_SPIN_DURATION_SECONDS = 5 # How long the "spinning" animation/message lasts
ROULETTE_PAYOUT_NUMBER = 35  # Payout multiplier for a correct number bet (e.g., 35x bet amount)
ROULETTE_PAYOUT_COLOR = 2    # Payout multiplier for a correct color bet (e.g., 2x bet amount)
ROULETTE_PAYOUT_GREEN = 35   # Payout for betting on green (0)
ROULETTE_INITIAL_EMBED_COLOR = 0xFFD700 # discord.Color.gold()
ROULETTE_SPIN_EMBED_COLOR = 0xFFAC33 # Orange-ish gold
ROULETTE_RESULT_EMBED_COLOR = None # Set to None to use dynamic color based on win/loss, or specify a discord.Color
ROULETTE_PLACE_BET_MESSAGE = "Place your bet by choosing an option below! What will it be?"
ROULETTE_SPINNING_MESSAGE = "No more bets! The wheel is spinning... 🎡"
ROULETTE_WIN_MESSAGE = "🎉 Lady Luck smiles upon you! You win **{payout_amount}** coins!"
ROULETTE_LOSS_MESSAGE = "💔 Better luck next time! The house takes your bet."
ROULETTE_TIMEOUT_MESSAGE = "Roulette game timed out. Your bet was not processed and has been voided."






# --- Music Cog Configuration ---




MUSIC_INTRO_PATH = "./assets/music_intros/default_intro.mp3"  # Path to an optional intro sound played when bot joins VC. Set to None to disable.
MUSIC_YTDL_OPTIONS = {
    'format': 'bestaudio/best', # Choose best audio quality
    'outtmpl': 'downloads/music/%(extractor)s-%(id)s-%(title)s.%(ext)s', # Template for downloaded files (if downloading)
    'restrictfilenames': True,
    'noplaylist': False, # Allow playlists by default
    'nocheckcertificate': True,
    'ignoreerrors': False, # Handle errors in code
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto', # ytsearch: for YouTube search
    'source_address': '0.0.0.0',  # Bind to all IP addresses (useful in some environments)
    # 'cookiefile': 'cookies.txt', # Optional: Path to a cookies file for accessing restricted content (e.g., YouTube Premium)
    'extract_flat': 'in_playlist', # Speeds up playlist loading by not fetching individual video info until played
    'lazy_playlist': True,
    'geo_bypass': True, # Attempt to bypass geographic restrictions
    # 'verbose': True, # For debugging yt-dlp issues
}
MUSIC_FFMPEG_EXECUTABLE_PATH = "ffmpeg" # Path to FFmpeg executable if not in system PATH.
MUSIC_FFMPEG_BEFORE_OPTIONS = { # Options passed before the -i input
    'reconnect': 1,
    'reconnect_streamed': 1,
    'reconnect_delay_max': 5,
}
MUSIC_FFMPEG_OPTIONS = { # Options passed after the -i input
    'options': '-vn -b:a 192k', # No video, audio bitrate 192k
    'executable': MUSIC_FFMPEG_EXECUTABLE_PATH, # Pass executable path here
}

MUSIC_DEFAULT_VOLUME = 0.5  # Default volume (0.0 to 2.0, where 1.0 is 100%)
MUSIC_VOLUME_MIN = 0        # Minimum volume percentage (e.g., 0 for 0%)
MUSIC_VOLUME_MAX = 200      # Maximum volume percentage (e.g., 200 for 200%)
MUSIC_MAX_QUEUE_LENGTH = 50
MUSIC_QUEUE_DISPLAY_LIMIT = 10 # How many songs to show in the !queue command
MUSIC_MAX_SONG_DURATION_SECONDS = 7200  # Max song length in seconds (e.g., 7200s = 2 hours). Set to 0 or None for no limit.
MUSIC_ALLOW_PLAYLISTS = True
MUSIC_MAX_PLAYLIST_LENGTH = 50 # Max number of songs to add from a single playlist
MUSIC_VC_CONNECT_TIMEOUT = 15.0 # Seconds to wait for voice channel connection
MUSIC_IDLE_DISCONNECT_SECONDS = 300 # 5 minutes: Time to wait before disconnecting if idle and queue is empty
MUSIC_PLAY_COOLDOWN_SECONDS = 3
MUSIC_SKIP_COOLDOWN_SECONDS = 2

# --- Music Cog: Emojis ---
MUSIC_EMOJI_PLAYING = "🎶"
MUSIC_EMOJI_QUEUE = "📜"
MUSIC_EMOJI_LOOP = "🔁"
MUSIC_EMOJI_VOLUME = "🔊"
MUSIC_EMOJI_ERROR = "❌"
MUSIC_EMOJI_SUCCESS = "✅"
MUSIC_EMOJI_INFO = "ℹ️"
MUSIC_EMOJI_SEARCH = "🔎"

# --- Music Cog: Embed Colors ---
MUSIC_NOW_PLAYING_EMBED_COLOR = 0x3498DB # Blue
MUSIC_QUEUE_EMBED_COLOR = 0x9B59B6       # Purple
MUSIC_ERROR_EMBED_COLOR = 0xE74C3C       # Red
MUSIC_SUCCESS_EMBED_COLOR = 0x2ECC71    # Green

# --- Music Cog: Messages (Examples - customize as you like) ---
MUSIC_MSG_USER_NOT_IN_VC = f"{MUSIC_EMOJI_ERROR} You need to be in a voice channel to use this command!"
MUSIC_MSG_VC_CONNECT_TIMEOUT = f"{MUSIC_EMOJI_ERROR} Timed out trying to connect to the voice channel."
MUSIC_MSG_VC_CONNECT_FAIL = f"{MUSIC_EMOJI_ERROR} Could not connect to your voice channel. Please check my permissions."
MUSIC_MSG_BOT_IN_DIFFERENT_VC = f"{MUSIC_EMOJI_ERROR} I'm already playing music in another voice channel on this server!"
MUSIC_MSG_JOINED_VC = "{emoji_success} Joined **{channel_name}**!"
MUSIC_MSG_LEFT_VC = "👋 Left the voice channel."
MUSIC_MSG_NOT_IN_VC = f"{MUSIC_EMOJI_ERROR} I'm not currently in a voice channel."
MUSIC_MSG_NOT_IN_VC_STOP = f"{MUSIC_EMOJI_ERROR} I'm not in a voice channel to stop!"

MUSIC_MSG_SONG_UNAVAILABLE = f"{MUSIC_EMOJI_ERROR} This song is unavailable or private."
MUSIC_MSG_UNSUPPORTED_URL = f"{MUSIC_EMOJI_ERROR} This URL or platform is not supported."
MUSIC_MSG_YTDL_GENERIC_ERROR = f"{MUSIC_EMOJI_ERROR} Error fetching song information. The video might be region-locked or removed."
MUSIC_MSG_YTDL_UNEXPECTED_ERROR = f"{MUSIC_EMOJI_ERROR} An unexpected error occurred while searching for the song."
MUSIC_MSG_PLAY_CMD_UNEXPECTED_ERROR = f"{MUSIC_EMOJI_ERROR} An unexpected error occurred while trying to play your request."
MUSIC_MSG_NO_SONG_FOUND = "❓ Couldn't find anything for your query: `{query}`"
MUSIC_MSG_SONG_TOO_LONG = f"{MUSIC_EMOJI_ERROR} Song is too long! Maximum duration is {{max_duration_minutes}} minutes." # Placeholder for dynamic filling

MUSIC_MSG_QUEUE_FULL_PLAYLIST = "{emoji_info} Added **{added_count}** songs. The queue is now full!"
MUSIC_MSG_PLAYLIST_ADDED = "{emoji_success} Added **{count}** songs to the queue from the playlist!"
MUSIC_MSG_PLAYLIST_EMPTY_OR_FAILED = f"{MUSIC_EMOJI_INFO} Couldn't add any songs from the playlist. It might be empty or private."
MUSIC_MSG_PLAYLISTS_DISABLED = f"{MUSIC_EMOJI_ERROR} Playlists are currently disabled by the bot owner."
MUSIC_MSG_SONG_ADDED = "{emoji_success} Added to queue: **{title}** ({duration})"
MUSIC_MSG_QUEUE_FULL_SINGLE = f"{MUSIC_EMOJI_ERROR} The queue is full! Cannot add **{{title}}**."

MUSIC_MSG_STREAM_URL_FAIL = f"{MUSIC_EMOJI_ERROR} Could not get a playable link for **{{title}}**. Skipping."
MUSIC_MSG_PLAYBACK_ERROR = f"{MUSIC_EMOJI_ERROR} An error occurred while trying to play **{{title}}**. Skipping."
MUSIC_MSG_QUEUE_EMPTY_DISCONNECT = "⏹ Queue finished. I'll leave the voice channel shortly if I remain idle."
MUSIC_MSG_IDLE_DISCONNECTED = "👋 Disconnected due to inactivity."

MUSIC_MSG_NOT_PLAYING_SKIP = f"{MUSIC_EMOJI_ERROR} I'm not playing anything to skip!"
MUSIC_MSG_NOTHING_TO_SKIP = f"{MUSIC_EMOJI_ERROR} There's nothing in the queue to skip to!"
MUSIC_MSG_SONG_SKIPPED = "⏭ Skipped **{title}**."
MUSIC_MSG_PLAYER_STOPPED = "⏹ Playback stopped, queue cleared, and I've left the voice channel."

MUSIC_MSG_QUEUE_IS_EMPTY = "텅 빈 대기열 (The queue is empty!)" # Example with Korean
MUSIC_MSG_NOTHING_PLAYING = f"{MUSIC_EMOJI_INFO} Nothing is currently playing."

MUSIC_MSG_LOOP_NO_SONG = f"{MUSIC_EMOJI_ERROR} There's no song currently playing to loop."
MUSIC_MSG_LOOP_ENABLED = "{emoji_loop} Song loop **enabled** for **{title}**."
MUSIC_MSG_LOOP_DISABLED = "{emoji_loop} Song loop **disabled**."

MUSIC_MSG_QUEUE_EMPTY_REMOVE = f"{MUSIC_EMOJI_ERROR} The queue is empty, nothing to remove."
MUSIC_MSG_REMOVE_INVALID_POS_TOO_LOW = f"{MUSIC_EMOJI_ERROR} Invalid position. Please use a number greater than 0."
MUSIC_MSG_REMOVE_INVALID_POS_TOO_HIGH = f"{MUSIC_EMOJI_ERROR} Invalid position. That number is too high for the current queue size."
MUSIC_MSG_SONG_REMOVED = "🗑 Removed **{title}** from the queue."
MUSIC_MSG_REMOVE_FAIL = f"{MUSIC_EMOJI_ERROR} Could not remove song at that position. Please check the queue number."

MUSIC_MSG_VOLUME_OUT_OF_RANGE = "{emoji_error} Volume must be between **{min_vol}%** and **{max_vol}%**."
MUSIC_MSG_VOLUME_SET = "{emoji_volume} Volume set to **{volume}%**."

MUSIC_MSG_MISSING_ARG = f"{MUSIC_EMOJI_ERROR} You're missing an argument: `{{argument}}`. Check `{{prefix}}help {{command}}`."
MUSIC_MSG_COOLDOWN = "⏳ This command is on cooldown. Please try again in **{cooldown:.2f}s**."
MUSIC_MSG_GUILD_ONLY = "🎶 Music commands only work in servers, not DMs."
MUSIC_MSG_CHECK_FAILURE = f"{MUSIC_EMOJI_ERROR} You don't have the required permissions or a check failed for this command."
MUSIC_MSG_UNEXPECTED_CMD_ERROR = f"{MUSIC_EMOJI_ERROR} An unexpected error occurred with that music command. The bot owner has been notified."









# --- Store Cog Configuration ---






STORE_FILE_PATH = "data/store.json"  # Path to the JSON file storing store items
STORE_ITEMS_PER_PAGE = 5             # Number of items to display per page in the !store command
STORE_VIEW_TIMEOUT = 300.0           # Timeout for the main store view (seconds)
STORE_NICKNAME_MODAL_TIMEOUT = 180.0 # Timeout for the nickname change modal
STORE_ADD_ITEM_MODAL_TIMEOUT = 300.0 # Timeout for the add item modal

# Define item types and their properties
# 'requires_data': bool - If true, the 'Item Data' field in AddItemModal is mandatory.
# 'data_prompt': str - A hint for what data is expected.
STORE_ITEM_TYPES = {
    "role": {"description": "Assigns a pre-defined role.", "requires_data": True, "data_prompt": "Enter the Role ID."},
    "color": {"description": "Assigns a custom color role.", "requires_data": True, "data_prompt": "Enter Hex Color (e.g., #RRGGBB)."},
    "badge": {"description": "Grants a visual badge (requires profile system).", "requires_data": True, "data_prompt": "Enter Image URL for the badge."},
    "nickname": {"description": "Allows user to change their nickname.", "requires_data": False}
}

# --- Store Cog: Emojis ---
STORE_EMOJI_TITLE = "🛍️"
STORE_EMOJI_BUY = "🛒"
STORE_EMOJI_ERROR = "❌"
STORE_EMOJI_SUCCESS = "✅"
STORE_EMOJI_INFO = "ℹ️"

# --- Store Cog: Embed Colors ---
STORE_EMBED_COLOR = 0xFFD700 # Gold
STORE_ITEM_PURCHASE_SUCCESS_COLOR = 0x2ECC71 # Green
STORE_ITEM_PURCHASE_ERROR_COLOR = 0xE74C3C   # Red

# --- Store Cog: Messages ---
STORE_MSG_BALANCE_CHECK = "{user_mention}'s balance: **{balance}** {currency}."
STORE_MSG_EMPTY = "The store is currently empty. Admins can add items using `!addstoreitem`."
STORE_MSG_ITEM_NOT_FOUND = f"{STORE_EMOJI_ERROR} This item is no longer available or the ID is incorrect."
STORE_MSG_INSUFFICIENT_FUNDS = f"{STORE_EMOJI_ERROR} You don't have enough {{currency}} to buy **{{item_name}}**."
STORE_MSG_ITEM_PURCHASED = "{emoji_success} You successfully purchased **{item_name}**!"
STORE_MSG_ITEM_ADDED = "{emoji_success} Item **{name}** (ID: {id}) added to the store!"
STORE_MSG_ITEM_REMOVED = "🗑 Item **{item_name}** (ID: {id}) has been removed from the store."
STORE_MSG_ITEM_ID_NOT_FOUND_REMOVE = f"{STORE_EMOJI_ERROR} No item found with ID `{{id}}`."

STORE_MSG_NICKNAME_CHANGED = "{emoji_success} Your nickname has been changed to **{nickname}**!"
STORE_MSG_NICKNAME_FORBIDDEN = f"{STORE_EMOJI_ERROR} I don't have permission to change your nickname. Please check my role hierarchy."
STORE_MSG_NICKNAME_ERROR = f"{STORE_EMOJI_ERROR} An error occurred while trying to change your nickname."

STORE_MSG_ROLE_ALREADY_HAS = f"{STORE_EMOJI_INFO} You already have the **{{role_name}}** role."
STORE_MSG_ROLE_NOT_FOUND_EFFECT = f"{STORE_EMOJI_ERROR} The role for this item could not be found on the server. It might have been deleted."
STORE_MSG_BADGE_PURCHASED_PENDING = "{emoji_success} Badge **{item_name}** purchased! It will appear on your profile soon (badge display feature pending)."
STORE_MSG_UNKNOWN_ITEM_TYPE_EFFECT = f"{STORE_EMOJI_ERROR} I don't know how to apply this type of item."

STORE_MSG_APPLY_EFFECT_FORBIDDEN = f"{STORE_EMOJI_ERROR} I don't have the necessary permissions to apply this item's effect (e.g., manage roles, change nicknames)."
STORE_MSG_APPLY_EFFECT_HTTP_ERROR = f"{STORE_EMOJI_ERROR} A Discord error occurred while applying this item. Please try again later or contact an admin."
STORE_MSG_APPLY_EFFECT_UNEXPECTED_ERROR = f"{STORE_EMOJI_ERROR} An unexpected error occurred while applying this item. The bot owner has been notified."
STORE_MSG_GENERIC_ERROR = f"{STORE_EMOJI_ERROR} An unexpected error occurred. Please try again."

# --- Economy Configuration (ensure these are consistent if shared with Games cog) ---
ECONOMY_FILE_PATH = "data/economy.json" # Should be the SAME path as used by Games cog
ECONOMY_DEFAULT_BALANCE = 100
ECONOMY_CURRENCY_NAME = "coins"
ECONOMY_CURRENCY_SYMBOL = "🪙" # Optional, for display

