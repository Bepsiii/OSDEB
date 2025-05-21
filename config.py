# config.py
"""
Configuration file for the Discord Bot.
All sensitive information and bot settings should be stored here.
Organized by importance for bot operation.
"""

# --- CORE BOT ESSENTIALS ---
# These are CRITICAL for the bot to connect and function at a basic level.
BOT_TOKEN = "" # YOUR DISCORD BOT TOKEN
OWNER_ID =  # Your Discord User ID (for privileged commands)
COMMAND_PREFIX = "!" # The prefix used to invoke bot commands

# --- COGS - BOT MODULES ---
# Defines which parts of the bot are loaded and active.
COGS_TO_LOAD = [
    "cogs.music",
    "cogs.fun",
    "cogs.games",
    "cogs.voice", # For VoiceInterruptCog
    "cogs.store",
    "cogs.rss",    # For RSS Feed functionality
    "cogs.help",
]

# --- LOGGING ---
# Essential for monitoring and debugging bot activity.
LOG_LEVEL = "INFO" # Set to "DEBUG" for more detailed logs, "WARNING" or "ERROR" for less.

# --- RSS FEED CORE CONFIGURATION (PRIORITY AS PER REQUEST) ---
# Channel ID for summaries is crucial if summaries are enabled.
RSS_SUMMARY_CHANNEL_ID =  # <<<< IMPORTANT: SET THIS TO THE ACTUAL CHANNEL ID FOR HOURLY SUMMARIES >>>>
RSS_HOURLY_SUMMARY_ENABLED = True  # Set to False to disable hourly summaries

RSS_FEEDS_FILE_PATH = "data/rss_feeds.json"  # Path to store RSS feed subscriptions
RSS_CHECK_INTERVAL_SECONDS = 900  # How often to check feeds (e.g., 15 minutes = 900)
RSS_SUMMARY_INTERVAL_HOURS = 1    # How often to generate and post a summary
RSS_MIN_ARTICLES_FOR_SUMMARY = 1   # Min new articles before generating a summary
RSS_MAX_ARTICLES_IN_PROMPT_FOR_SUMMARY = 15 # Max articles to include in a single Gemini prompt

# --- GEMINI API CONFIGURATION (If RSS or other core features depend on it) ---
GEMINI_API_KEY = ""  # Replace with your actual Gemini API key
GEMINI_MODEL_NAME = "gemini-2.5-flash-preview-04-17"  # Or "gemini-pro", "gemini-1.0-pro", etc.
GEMINI_MAX_OUTPUT_TOKENS = 2000 # Maximum tokens for Gemini response
GEMINI_TEMPERATURE = 0.7 # Controls randomness (0.0 to 1.0)
GEMINI_TOP_P = 1.0 # Nucleus sampling
GEMINI_TOP_K = 1 # Top-k sampling
GEMINI_ERROR_MESSAGE = "Sorry, I encountered an error trying to process your request with Gemini."

# --- REVISED GEMINI SUMMARY PROMPT FOR RSS ---
RSS_GEMINI_SUMMARY_PROMPT = (
    "You are a news summarizer for a Discord channel. Please provide a concise and engaging news update "
    "based on the following articles. Use clear Markdown formatting. \n\n"
    "For each significant topic or source, use a heading (e.g., '## Tech Updates' or '### From ExampleSite').\n"
    "For each article under a topic, list its title as a bullet point using a hyphen (-), briefly summarize it, and include its link directly after the summary in parentheses, like this: (Link: <url>).\n"
    "Keep summaries brief and to the point. Group related news items if it makes sense. "
    "Avoid excessive asterisks or unusual formatting unless it enhances readability for Discord.\n\n"
    "Here are the articles:\n\n"
    "{articles_text}" # This placeholder will be filled with formatted article data
)
RSS_SUMMARY_POST_HEADER = "📰 **Hourly News Roundup!** Here's what's new:"
RSS_NO_NEW_ARTICLES_FOR_SUMMARY_MESSAGE = "ℹ️ No new significant articles collected in the past hour to summarize."

# --- BOT PRESENCE CONFIGURATION ---
# How the bot appears in the user list (e.g., "Playing a game", "Listening to !help").
PRESENCE_UPDATE_INTERVAL_SECONDS = 30  # How often to update the bot's presence
TARGET_GUILD_ID_FOR_PRESENCE = 0 # Example: 123456789012345678, or 0/None for global
DEFAULT_PRESENCE_ACTIVITY_TYPE = "listening"  # "playing", "watching", "listening", "competing"
DEFAULT_PRESENCE_NAME = "!help for commands" # e.g., "silence", "your commands"
DEFAULT_PRESENCE_EMOJI = "🎧" # Optional emoji for default presence
MUSIC_PRESENCE_ACTIVITY_TYPE = "listening" # Specific for when music is playing
MUSIC_PRESENCE_EMOJI = "🎶" # Optional emoji for music presence

# --- GENERAL MESSAGE CONFIGURATION ---
DISCORD_MESSAGE_MAX_LENGTH = 2000

# --- ECONOMY CONFIGURATION (Foundation for Store, Games) ---
ECONOMY_FILE_PATH = "data/economy.json"
ECONOMY_DEFAULT_BALANCE = 100
ECONOMY_CURRENCY_NAME = "coins"
ECONOMY_CURRENCY_SYMBOL = "🪙"

# --- MUSIC COG CONFIGURATION ---
MUSIC_INTRO_PATH = "./assets/music_intros/default_intro.mp3"
MUSIC_FFMPEG_EXECUTABLE_PATH = "ffmpeg" # Or full path if not in PATH
MUSIC_FFMPEG_BEFORE_OPTIONS = {
    'reconnect': 1,
    'reconnect_streamed': 1,
    'reconnect_delay_max': 5,
}
MUSIC_FFMPEG_OPTIONS = {
    'options': '-vn -b:a 192k',
    'executable': MUSIC_FFMPEG_EXECUTABLE_PATH,
}
MUSIC_YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'outtmpl': 'downloads/music/%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': False, # Set to False to allow playlist downloads by default
    'nocheckcertificate': True,
    'ignoreerrors': False, # Set to False to catch download errors
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'extract_flat': 'in_playlist', # Crucial for faster playlist parsing
    'lazy_playlist': True,        # Also for faster playlist handling
    'geo_bypass': True,
    # 'cookiefile': 'cookies.txt', # Optional: for sites requiring login
}
MUSIC_DEFAULT_VOLUME = 0.5 # (50% volume)
MUSIC_VOLUME_MIN = 0
MUSIC_VOLUME_MAX = 200 # (0% to 200% volume)
MUSIC_MAX_QUEUE_LENGTH = 50
MUSIC_QUEUE_DISPLAY_LIMIT = 10
MUSIC_MAX_SONG_DURATION_SECONDS = 7200 # 2 hours
MUSIC_ALLOW_PLAYLISTS = True
MUSIC_MAX_PLAYLIST_LENGTH = 50
MUSIC_VC_CONNECT_TIMEOUT = 15.0 # Seconds
MUSIC_IDLE_DISCONNECT_SECONDS = 300 # 5 minutes
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
MUSIC_NOW_PLAYING_EMBED_COLOR = 0x3498DB
MUSIC_QUEUE_EMBED_COLOR = 0x9B59B6
MUSIC_ERROR_EMBED_COLOR = 0xE74C3C
MUSIC_SUCCESS_EMBED_COLOR = 0x2ECC71

# --- Music Cog: Messages ---
MUSIC_MSG_USER_NOT_IN_VC = f"{MUSIC_EMOJI_ERROR} You need to be in a voice channel to use this command!"
MUSIC_MSG_VC_CONNECT_TIMEOUT = f"{MUSIC_EMOJI_ERROR} Timed out trying to connect to the voice channel."
MUSIC_MSG_VC_CONNECT_FAIL = f"{MUSIC_EMOJI_ERROR} Could not connect to your voice channel. Please check my permissions."
MUSIC_MSG_BOT_IN_DIFFERENT_VC = f"{MUSIC_EMOJI_ERROR} I'm already playing music in another voice channel on this server!"
MUSIC_MSG_JOINED_VC = "{emoji_success} Joined **{channel_name}**!" # Uses MUSIC_EMOJI_SUCCESS
MUSIC_MSG_LEFT_VC = "👋 Left the voice channel."
MUSIC_MSG_NOT_IN_VC = f"{MUSIC_EMOJI_ERROR} I'm not currently in a voice channel."
MUSIC_MSG_NOT_IN_VC_STOP = f"{MUSIC_EMOJI_ERROR} I'm not in a voice channel to stop!"
MUSIC_MSG_SONG_UNAVAILABLE = f"{MUSIC_EMOJI_ERROR} This song is unavailable or private."
MUSIC_MSG_UNSUPPORTED_URL = f"{MUSIC_EMOJI_ERROR} This URL or platform is not supported."
MUSIC_MSG_YTDL_GENERIC_ERROR = f"{MUSIC_EMOJI_ERROR} Error fetching song information. The video might be region-locked or removed."
MUSIC_MSG_YTDL_UNEXPECTED_ERROR = f"{MUSIC_EMOJI_ERROR} An unexpected error occurred while searching for the song."
MUSIC_MSG_PLAY_CMD_UNEXPECTED_ERROR = f"{MUSIC_EMOJI_ERROR} An unexpected error occurred while trying to play your request."
MUSIC_MSG_NO_SONG_FOUND = "❓ Couldn't find anything for your query: `{query}`"
MUSIC_MSG_SONG_TOO_LONG = f"{MUSIC_EMOJI_ERROR} Song is too long! Maximum duration is {{max_duration_minutes}} minutes." # Placeholder for formatted minutes
MUSIC_MSG_QUEUE_FULL_PLAYLIST = "{emoji_info} Added **{added_count}** songs. The queue is now full!" # Uses MUSIC_EMOJI_INFO
MUSIC_MSG_PLAYLIST_ADDED = "{emoji_success} Added **{count}** songs to the queue from the playlist!" # Uses MUSIC_EMOJI_SUCCESS
MUSIC_MSG_PLAYLIST_EMPTY_OR_FAILED = f"{MUSIC_EMOJI_INFO} Couldn't add any songs from the playlist. It might be empty or private."
MUSIC_MSG_PLAYLISTS_DISABLED = f"{MUSIC_EMOJI_ERROR} Playlists are currently disabled by the bot owner."
MUSIC_MSG_SONG_ADDED = "{emoji_success} Added to queue: **{title}** ({duration})" # Uses MUSIC_EMOJI_SUCCESS
MUSIC_MSG_QUEUE_FULL_SINGLE = f"{MUSIC_EMOJI_ERROR} The queue is full! Cannot add **{{title}}**."
MUSIC_MSG_STREAM_URL_FAIL = f"{MUSIC_EMOJI_ERROR} Could not get a playable link for **{{title}}**. Skipping."
MUSIC_MSG_PLAYBACK_ERROR = f"{MUSIC_EMOJI_ERROR} An error occurred while trying to play **{{title}}**. Skipping."
MUSIC_MSG_QUEUE_EMPTY_DISCONNECT = "⏹ Queue finished. I'll leave the voice channel shortly if I remain idle."
MUSIC_MSG_IDLE_DISCONNECTED = "👋 Disconnected due to inactivity."
MUSIC_MSG_NOT_PLAYING_SKIP = f"{MUSIC_EMOJI_ERROR} I'm not playing anything to skip!"
MUSIC_MSG_NOTHING_TO_SKIP = f"{MUSIC_EMOJI_ERROR} There's nothing in the queue to skip to!"
MUSIC_MSG_SONG_SKIPPED = "⏭ Skipped **{title}**."
MUSIC_MSG_PLAYER_STOPPED = "⏹ Playback stopped, queue cleared, and I've left the voice channel."
MUSIC_MSG_QUEUE_IS_EMPTY = "텅 빈 대기열 (The queue is empty!)" # Korean for "empty queue"
MUSIC_MSG_NOTHING_PLAYING = f"{MUSIC_EMOJI_INFO} Nothing is currently playing."
MUSIC_MSG_LOOP_NO_SONG = f"{MUSIC_EMOJI_ERROR} There's no song currently playing to loop."
MUSIC_MSG_LOOP_ENABLED = "{emoji_loop} Song loop **enabled** for **{title}**." # Uses MUSIC_EMOJI_LOOP
MUSIC_MSG_LOOP_DISABLED = "{emoji_loop} Song loop **disabled**." # Uses MUSIC_EMOJI_LOOP
MUSIC_MSG_QUEUE_EMPTY_REMOVE = f"{MUSIC_EMOJI_ERROR} The queue is empty, nothing to remove."
MUSIC_MSG_REMOVE_INVALID_POS_TOO_LOW = f"{MUSIC_EMOJI_ERROR} Invalid position. Please use a number greater than 0."
MUSIC_MSG_REMOVE_INVALID_POS_TOO_HIGH = f"{MUSIC_EMOJI_ERROR} Invalid position. That number is too high for the current queue size."
MUSIC_MSG_SONG_REMOVED = "🗑 Removed **{title}** from the queue."
MUSIC_MSG_REMOVE_FAIL = f"{MUSIC_EMOJI_ERROR} Could not remove song at that position. Please check the queue number."
MUSIC_MSG_VOLUME_OUT_OF_RANGE = "{emoji_error} Volume must be between **{min_vol}%** and **{max_vol}%**." # Uses MUSIC_EMOJI_ERROR
MUSIC_MSG_VOLUME_SET = "{emoji_volume} Volume set to **{volume}%**." # Uses MUSIC_EMOJI_VOLUME
MUSIC_MSG_MISSING_ARG = f"{MUSIC_EMOJI_ERROR} You're missing an argument: `{{argument}}`. Check `{{prefix}}help {{command}}`."
MUSIC_MSG_COOLDOWN = "⏳ This command is on cooldown. Please try again in **{cooldown:.2f}s**."
MUSIC_MSG_GUILD_ONLY = "🎶 Music commands only work in servers, not DMs."
MUSIC_MSG_CHECK_FAILURE = f"{MUSIC_EMOJI_ERROR} You don't have the required permissions or a check failed for this command."
MUSIC_MSG_UNEXPECTED_CMD_ERROR = f"{MUSIC_EMOJI_ERROR} An unexpected error occurred with that music command. The bot owner has been notified."


# --- VOICE INTERRUPT COG CONFIGURATION ---
VOICE_INTERRUPT_SOUND_PATH = "./sounds/interrupt_sound.mp3"
VOICE_INTERRUPT_FFMPEG_OPTIONS = {
    'options': '-vn -b:a 128k',
    # 'executable': "ffmpeg" # Optional: if ffmpeg is not in PATH, specify full path
}
VOICE_INTERRUPT_INITIAL_DELAY_SECONDS = 1.5
VOICE_INTERRUPT_CHECK_INTERVAL_SECONDS = 0.75
VOICE_SET_TARGET_ADMIN_ONLY = True # If True, only users with 'Manage Guild' can set targets
VOICE_SET_TARGET_COOLDOWN = 10 # Seconds for !setinterrupttarget cooldown

# --- Voice Interrupt Cog: Messages ---
VOICE_MSG_TARGET_SET = "🎯 Target user for interruption set to **{target_name}** in this server."
VOICE_MSG_TARGET_CLEARED = "🎯 Interrupt target has been cleared for this server."
VOICE_MSG_NO_TARGET_TO_CLEAR = "ℹ️ No interrupt target is currently set for this server."
VOICE_MSG_NO_PERMISSION_TARGET_CMD = "❌ You don't have the required permissions (Manage Guild) to set or clear interrupt targets."
VOICE_MSG_GENERIC_CMD_ERROR = "❗ An unexpected error occurred with that command."



# --- STORE COG CONFIGURATION (Relies on Economy) ---
STORE_FILE_PATH = "data/store.json"
STORE_ITEMS_PER_PAGE = 5
STORE_VIEW_TIMEOUT = 300.0 # Seconds
STORE_NICKNAME_MODAL_TIMEOUT = 180.0 # Seconds
STORE_ADD_ITEM_MODAL_TIMEOUT = 300.0 # Seconds
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
STORE_ITEM_PURCHASE_ERROR_COLOR = 0xE74C3C # Red
# --- Store Cog: Messages ---
STORE_MSG_BALANCE_CHECK = "{user_mention}'s balance: **{balance}** {currency}." # Uses ECONOMY_CURRENCY_NAME
STORE_MSG_EMPTY = "The store is currently empty. Admins can add items using `!addstoreitem`."
STORE_MSG_ITEM_NOT_FOUND = f"{STORE_EMOJI_ERROR} This item is no longer available or the ID is incorrect."
STORE_MSG_INSUFFICIENT_FUNDS = f"{STORE_EMOJI_ERROR} You don't have enough {{currency}} to buy **{{item_name}}**." # Uses ECONOMY_CURRENCY_NAME
STORE_MSG_ITEM_PURCHASED = "{emoji_success} You successfully purchased **{item_name}**! {cost} {currency} deducted." # Uses STORE_EMOJI_SUCCESS, ECONOMY_CURRENCY_NAME
STORE_MSG_ITEM_ADDED = "{emoji_success} Item **{name}** (ID: {id}) added to the store!" # Uses STORE_EMOJI_SUCCESS
STORE_MSG_ITEM_REMOVED = "🗑 Item **{item_name}** (ID: {id}) has been removed from the store."
STORE_MSG_ITEM_ID_NOT_FOUND_REMOVE = f"{STORE_EMOJI_ERROR} No item found with ID `{{id}}`."
STORE_MSG_NICKNAME_CHANGED = "{emoji_success} Your nickname has been changed to **{nickname}** and {cost} {currency} deducted!" # Uses STORE_EMOJI_SUCCESS, ECONOMY_CURRENCY_NAME
STORE_MSG_NICKNAME_FORBIDDEN = f"{STORE_EMOJI_ERROR} I don't have permission to change your nickname. Your coins have been refunded."
STORE_MSG_NICKNAME_ERROR = f"{STORE_EMOJI_ERROR} An error occurred. Your coins have been refunded."
STORE_MSG_ROLE_ALREADY_HAS = f"{STORE_EMOJI_INFO} You already have the **{{role_name}}** role."
STORE_MSG_ROLE_NOT_FOUND_EFFECT = f"{STORE_EMOJI_ERROR} The role for this item could not be found on the server. Your coins have been refunded."
STORE_MSG_BADGE_PURCHASED_PENDING = "{emoji_success} Badge **{item_name}** purchased! It will appear on your profile soon (badge display feature pending)." # Uses STORE_EMOJI_SUCCESS
STORE_MSG_UNKNOWN_ITEM_TYPE_EFFECT = f"{STORE_EMOJI_ERROR} I don't know how to apply this type of item. Coins refunded."
STORE_MSG_APPLY_EFFECT_FORBIDDEN = f"{STORE_EMOJI_ERROR} I don't have the necessary permissions to apply this item's effect. Your coins have been refunded."
STORE_MSG_APPLY_EFFECT_HTTP_ERROR = f"{STORE_EMOJI_ERROR} A Discord error occurred while applying this item. Please try again later. Your coins have been refunded."
STORE_MSG_APPLY_EFFECT_UNEXPECTED_ERROR = f"{STORE_EMOJI_ERROR} An unexpected error occurred. Your coins have been refunded."
STORE_MSG_GENERIC_ERROR = f"{STORE_EMOJI_ERROR} An unexpected error occurred. Please try again."


# --- GENERAL GAME SETTINGS (Relies on Economy) ---
ALLOW_GAMES_IN_DMS = False
GAMES_MIN_BET_MESSAGE = "Minimum bet is {min_bet} coins." # Uses ECONOMY_CURRENCY_NAME via "coins"
GAMES_INSUFFICIENT_FUNDS_MESSAGE = "You don't have enough coins! Your current balance: {balance} coins." # Uses ECONOMY_CURRENCY_NAME via "coins"
GAMES_OPPONENT_INSUFFICIENT_FUNDS_MESSAGE = "{opponent_name} doesn't have enough coins to accept the bet (Their balance: {opponent_balance})." # Uses ECONOMY_CURRENCY_NAME via "coins"
GAMES_BALANCE_MESSAGE = "{user_mention}'s balance: **{balance}** {currency}." # Uses ECONOMY_CURRENCY_NAME


# --- CONNECT 4 CONFIGURATION (Game Specific) ---
CONNECT4_MIN_BET = 1
CONNECT4_GAME_TIMEOUT_SECONDS = 300.0
CONNECT4_COOLDOWN_SECONDS = 30
CONNECT4_EMBED_COLOR = 0x8A2BE2 # BlueViolet
CONNECT4_PLAYER1_EMOJI = "🔴"
CONNECT4_PLAYER2_EMOJI = "🔵"
CONNECT4_EMPTY_EMOJI = "⚪"
CONNECT4_CANNOT_PLAY_SELF_MESSAGE = "You can't play Connect 4 against yourself!"
CONNECT4_CANNOT_PLAY_BOT_MESSAGE = "You can't challenge a bot to Connect 4!"


# --- BLACKJACK CONFIGURATION (Game Specific) ---
BLACKJACK_MIN_BET = 5
BLACKJACK_GAME_TIMEOUT_SECONDS = 180.0
BLACKJACK_COOLDOWN_SECONDS = 10
BLACKJACK_EMBED_COLOR = 0x2ECC71 # Emerald Green
BLACKJACK_CARD_RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
BLACKJACK_CARD_SUITS = ["♠️", "♣️", "♥️", "♦️"]
BLACKJACK_HIDDEN_CARD_EMOJI = "❓"
BLACKJACK_NATURAL_PAYOUT_MULTIPLIER = 2.5 # e.g. bet 10, win 25
BLACKJACK_WIN_PAYOUT_MULTIPLIER = 2.0 # e.g. bet 10, win 20


# --- ROULETTE CONFIGURATION (Game Specific) ---
ROULETTE_MIN_BET = 10
ROULETTE_GAME_TIMEOUT_SECONDS = 180.0 # For the game interaction itself
ROULETTE_MODAL_TIMEOUT_SECONDS = 120.0 # For the bet placement modal
ROULETTE_COOLDOWN_SECONDS = 15
ROULETTE_GIF_PATH = "assets/gifs/roulette_spin.gif"
ROULETTE_SPIN_DURATION_SECONDS = 5
ROULETTE_PAYOUT_NUMBER = 35 # Bet on a single number (e.g., bet 10, win 350 + original 10 back)
ROULETTE_PAYOUT_COLOR = 2  # Bet on red/black (e.g., bet 10, win 10 + original 10 back)
ROULETTE_PAYOUT_GREEN = 35 # Bet on green (0 or 00)
ROULETTE_INITIAL_EMBED_COLOR = 0xFFD700 # Gold
ROULETTE_SPIN_EMBED_COLOR = 0xFFAC33 # Orange
ROULETTE_RESULT_EMBED_COLOR = None # Will be set to Green for win, Red for loss
ROULETTE_PLACE_BET_MESSAGE = "Place your bet by choosing an option below! What will it be?"
ROULETTE_SPINNING_MESSAGE = "No more bets! The wheel is spinning... 🎡"
ROULETTE_WIN_MESSAGE = "🎉 Lady Luck smiles upon you! You win **{payout_amount}** coins!" # Uses ECONOMY_CURRENCY_NAME via "coins"
ROULETTE_LOSS_MESSAGE = "💔 Better luck next time! The house takes your bet."
ROULETTE_TIMEOUT_MESSAGE = "Roulette game timed out. Your bet was not processed and has been voided."


# --- FUN COG: JOKES CONFIGURATION ---
JOKES_LIST = [
    "Why did the scarecrow win an award? Because he was outstanding in his field!",
    "What do you call fake spaghetti? An impasta!",
    "How do you organize a space party? You planet!",
    "Why don't programmers like nature? It has too many bugs.",
    "What did the zero say to the eight? Nice belt!",
    "Why was the math book sad? Because it had too many problems.",
]

# --- FUN COG: SNAP COMMAND CONFIGURATION ---
SNAP_MEDIA_FOLDER = "./Images" # Folder containing images for the snap command

# --- FUN COG: FISH COMMAND CONFIGURATION ---
FISH_IMAGES_FOLDER = "./fish" # Folder containing fish images
FISH_DM_MESSAGE = "You've been fished! Hope you like this catch! 🎣"
FISH_CHANNEL_CONFIRM_MESSAGE = "{user_mention} just got a surprise fish in their DMs! 🐟"


# --- RSS FEED COG - SUPPLEMENTARY CONFIG (Less critical than core RSS settings) ---
RSS_USER_AGENT = "DiscordRSSBot/1.0 (YourBotName; +http://your.bot.website.or.contact/)" # Good practice for web requests
RSS_REQUEST_TIMEOUT_SECONDS = 15 # Timeout for fetching a single feed
RSS_MAX_DESCRIPTION_LENGTH = 300 # For individual article details if ever used directly (not in current summary prompt)
RSS_DEFAULT_EMBED_COLOR = 0xEE802F # Orange-ish color for RSS embeds (if individual posts were made)
RSS_MAX_FETCH_ERRORS_BEFORE_DISABLE = 5 # How many consecutive errors before logging a major warning (feed not actually disabled automatically by this)
RSS_MAX_ARTICLES_ON_FIRST_FETCH = 1 # How many articles to process on the very first fetch of a NEW feed (to avoid spam)

# --- RSS Cog: Emojis ---
RSS_EMOJI_ADD = "➕"
RSS_EMOJI_REMOVE = "➖"
RSS_EMOJI_LIST = "📋"
RSS_EMOJI_NEWS = "📰" # General news/feed emoji
RSS_EMOJI_ERROR = "⚠️" # Using a warning sign for errors
RSS_EMOJI_SUCCESS = "✅"
RSS_EMOJI_INFO = "ℹ️"

# --- RSS Cog: Messages ---
RSS_MSG_FEED_ADDED = "{emoji_success} Successfully added RSS feed: `{feed_url}`. It will be included in hourly summaries (if enabled)."
RSS_MSG_FEED_REMOVED = "{emoji_success} Successfully removed RSS feed: `{feed_url}`."
RSS_MSG_FEED_NOT_FOUND_REMOVE = "{emoji_error} Could not find an RSS feed with that URL/ID in this server to remove."
RSS_MSG_FEED_ALREADY_EXISTS = "{emoji_error} This RSS feed (`{feed_url}`) is already being monitored for this server."
RSS_MSG_INVALID_URL = "{emoji_error} The URL provided does not seem to be a valid RSS/Atom feed URL or is unreachable."
RSS_MSG_INVALID_CHANNEL = "{emoji_error} Could not find the channel `{channel_name}`. Please make sure I can see it." # If a specific channel was needed per feed
RSS_MSG_NO_FEEDS = "{emoji_info} There are no RSS feeds currently being monitored for summaries in this server."
RSS_MSG_LIST_HEADER = "**Currently Monitored RSS Feeds for Summaries:**"
RSS_MSG_FETCH_ERROR = "{emoji_error} Error fetching feed `{feed_url}`: {error}"
RSS_MSG_PARSE_ERROR = "{emoji_error} Error parsing feed `{feed_url}`. It might not be a valid feed."
RSS_MSG_MANUAL_CHECK_START = "⚙️ Starting manual collection of articles from all RSS feeds..."
RSS_MSG_MANUAL_CHECK_COMPLETE = "⚙️ Manual RSS article collection finished. {new_articles_count} new articles collected for the next summary."
# RSS_MSG_NEW_ARTICLE_POSTED (Not primary if only summaries are posted. Keep if individual posts are an option)


# --- GENERAL ERROR EMBED COLOR (Fallback) ---
# This can be used by cogs that don't have their own specific error embed colors.
# ERROR_EMBED_COLOR = 0xE74C3C # Red (Consider if Music/Store error colors are sufficient or a global one is needed)