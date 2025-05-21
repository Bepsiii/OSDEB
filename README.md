# Discord Bot Setup Guide

This guide provides instructions on how to set up and run this multi-functional Discord bot.

## ⚠️ Most Common Startup Error: "Invalid bot token!" ⚠️

If you see `❌ Invalid bot token!` in your console when starting the bot, **this is the first thing to fix.**

**Solution: Reset and correctly copy your token.**
1.  **Go to the Discord Developer Portal**: [https://discord.com/developers/applications](https://discord.com/developers/applications)
2.  **Select your Bot Application.**
3.  Navigate to the **"Bot"** page from the menu on the left.
4.  Find the **"Token"** section (it's below your bot's username).
5.  Click the **"Reset Token"** button. Discord will ask you to confirm. Click "Yes, do it!".
    * *Your old token will immediately stop working.*
6.  A **new token** will be displayed. **Immediately click the "Copy" button** that appears next to this new token.
    * *Do not try to manually select and copy the text; use the provided "Copy" button to avoid errors.*
7.  Open your `config.py` file in your code editor.
8.  Find the line that says:
    ```python
    BOT_TOKEN = "..."
    ```
9.  **Carefully delete only the old token string** that is currently inside the quotation marks.
10. **Paste the new token you just copied** directly between the quotation marks.
    * Ensure there are **NO extra spaces** before or after the token string.
    * It should look like: `BOT_TOKEN = "NewlyCopiedTokenString"`
11. **Save the `config.py` file.**
12. Try running your bot again (`py bot.py` or `python bot.py`).

If the error persists after following these steps *exactly*, double-check for any typos or accidental modifications to the token string in `config.py`.

## Prerequisites

1.  **Python**: Ensure you have Python 3.9 or newer installed (Python 3.10+ is recommended for newer type hint syntax if you plan to modify the code extensively). You can download it from [python.org](https://www.python.org/).
2.  **FFmpeg**: Required for the music cog to play audio.
    * **Windows**: Download from [FFmpeg Official Site](https://ffmpeg.org/download.html) (select a Windows build). Extract it and add the `bin` folder (containing `ffmpeg.exe`) to your system's PATH environment variable.
    * **Linux (Debian/Ubuntu)**: `sudo apt update && sudo apt install ffmpeg`
    * **macOS (using Homebrew)**: `brew install ffmpeg`
3.  **Discord Bot Token**: You'll need a token for your bot from the [Discord Developer Portal](https://discord.com/developers/applications). (See troubleshooting above if you have issues).
4.  **Google Gemini API Key**: Required for the Gemini AI features, including the RSS feed summarization. Obtain an API key from [Google AI Studio](https://aistudio.google.com/app/apikey).

## Setup Instructions

1.  **Clone/Download Files**:
    * Place all the bot files (`bot.py`, `config.py`, `gemini_service.py`, and the `cogs` directory with all its Python files like `music.py`, `fun.py`, `games.py`, `store.py`, `voice.py`, `rss.py`, `help.py`) into a single project folder.
    * Create the necessary subdirectories as specified in `config.py` (e.g., `data/` for economy/store/rss files, `sounds/` for interrupt sounds, `assets/` for music intros/GIFs, `Images/` and `fish/` for the Fun cog).

2.  **Create a Virtual Environment (Recommended)**:
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # Linux/macOS
    source venv/bin/activate
    ```

3.  **Install Dependencies**:
    * Use the `requirements.txt` file provided previously. If you don't have it, create one with at least the following content (refer to the `requirements_txt_rss_update` artifact for the full list):
      ```text
      discord.py>=2.3.0
      google-generativeai>=0.3.0
      yt-dlp>=2023.07.06
      feedparser>=6.0.0  # For RSS Cog
      aiohttp>=3.8.0     # For RSS Cog (often a discord.py dependency too)
      # PyNaCl>=1.5.0 # Usually a discord.py dependency for voice
      ```
    * Install the required Python libraries:
        ```bash
        pip install -r requirements.txt
        ```
        *Note: PyNaCl is usually a dependency of `discord.py` for voice. If you encounter voice issues, try `pip install PyNaCl`.*

4.  **Configure the Bot (`config.py`)**:
    * Open `config.py` (refer to the `config_py_rss_gemini_summary_prompt_update` artifact as your base).
    * Fill in all the required fields, especially:
        * `BOT_TOKEN` (see troubleshooting above).
        * `OWNER_ID`.
        * `GEMINI_API_KEY`.
        * **`RSS_SUMMARY_CHANNEL_ID`**: This is crucial for the RSS summary feature. Set it to the ID of the channel where hourly summaries should be posted.
    * Review and adjust all paths (e.g., `ECONOMY_FILE_PATH`, `MUSIC_INTRO_PATH`, `VOICE_INTERRUPT_SOUND_PATH`). Ensure these paths are correct relative to where `bot.py` will run.
    * Customize lists like `JOKES_LIST` and `COGS_TO_LOAD` (ensure `"cogs.rss"` and `"cogs.help"` are included, and `"cogs.voicekick"` is removed if not used).
    * Review all other settings (timeouts, messages, emojis, etc.) and adjust as needed.

5.  **Add Assets**:
    * Place your intro sounds, interrupt sounds, images for the `snap` command, and fish images into the respective folders defined in `config.py`.

6.  **Run the Bot**:
    ```bash
    python bot.py
    ```
    You should see log messages in your console indicating the bot is connecting and cogs are loading.

## Standard Bot Commands (Examples)

The command prefix is typically `!` (configurable in `config.py`). Use `!help` for a full list from the bot.

**General:**
* `!help` (or `!h`, `!commands`): Shows the main help message listing all command categories (cogs).
* `!help <command_name>`: Shows detailed help for a specific command.
* `!help <CategoryName>`: Shows all commands within a specific category/cog.

**Fun Cog (`cogs/fun.py`):**
* `!example_command`: Sends an example message.
* `!joke`: Tells a random joke.
* `!snap`: Sends a random image/video from the configured media folder.
* `!fish @User`: Sends a random fish picture to the mentioned user's DMs.
* `!say <message>`: Makes the bot repeat your message.

**Games Cog (`cogs/games.py`):**
* `!balance [@User]`: Checks your (or another user's) coin balance.
* `!connect4 @Opponent <bet>`: Starts a Connect 4 game with a bet.
* `!blackjack <bet>` (or `!bj <bet>`): Starts a Blackjack game.
* `!roulette <bet>`: Starts a Roulette game.

**Music Cog (`cogs/music.py`):**
* `!join`: Bot joins your voice channel.
* `!leave` (or `!dc`, `!stop`): Bot leaves the voice channel and clears the queue.
* `!play <song name or URL>` (or `!p`): Plays a song or adds it/playlist to the queue.
* `!skip` (or `!s`): Skips the current song.
* `!queue` (or `!q`): Shows the music queue.
* `!nowplaying` (or `!np`): Shows the currently playing song.
* `!loop`: Toggles looping for the current song.
* `!remove <position>`: Removes a song from the queue by its position number.
* `!volume <0-200>`: Sets the player volume.

**Store Cog (`cogs/store.py`):**
* `!store`: Displays items available for purchase.
* `!addstoreitem`: (Admin) Opens a prompt/button to add an item to the store.
* `!removestoreitem <item_id>`: (Admin) Removes an item from the store by its ID.

**Voice Interrupt Cog (`cogs/voice.py`):**
* `!setinterrupttarget @User` (or `!settarget`): (Admin) Sets a user to be "interrupted" with a sound.
* `!clearinterrupttarget`: (Admin) Clears the interrupt target.

**RSS Summarizer Cog (`cogs/rss.py`):**
* `!rss add <feed_url> [#error_channel]` : Adds an RSS feed to be included in hourly summaries. Errors/confirmations for this command go to `#error_channel` or the current channel.
* `!rss remove <feed_url_or_index>`: Removes an RSS feed from monitoring.
* `!rss list`: Lists RSS feeds being monitored for summaries.
* `!rss collectnow`: (Owner) Manually triggers article collection from feeds.
* `!rss summarizenow`: (Owner) Manually triggers Gemini summary of collected articles to the configured summary channel.
    * *Note: Hourly summaries are posted automatically to the channel set in `RSS_SUMMARY_CHANNEL_ID` in `config.py`.*

**Gemini AI (if `gemini_service.py` and command in `bot.py` are used):**
* `!gemini <prompt>`: Sends a prompt to the Gemini AI and gets a response.

*This is a general list. Specific command names, aliases, and permissions might vary based on the final configuration and code.*

## Further Troubleshooting
* **"FFmpeg/AVConv not found"**: Ensure FFmpeg is installed correctly and its `bin` directory is in your system's PATH.
* **No Sound/Music Issues**: Check FFmpeg, bot permissions (`Connect`, `Speak`), `PyNaCl` installation, `yt-dlp` version, and console logs.
* **Cog Loading Errors**: Check console for "Failed to load extension" messages. This usually indicates an error within the cog file or a missing dependency.
* **File Not Found (economy.json, store.json, sound files, rss_feeds.json)**: Ensure paths in `config.py` are correct, directories exist, and the bot has read/write permissions.
* **`RuntimeError: Event loop is closed`**: Often a secondary error. Fix primary errors (like invalid token or critical cog load failures) first.
* **RSS Summaries Not Posting**:
    * Ensure `RSS_HOURLY_SUMMARY_ENABLED = True` in `config.py`.
    * **Verify `RSS_SUMMARY_CHANNEL_ID` in `config.py` is set to a valid channel ID where the bot has permission to send messages and embeds.**
    * Check `GEMINI_API_KEY` is correct and active.
    * Ensure `bot.gemini_service` is available (check `bot.py` and console logs at startup).
    * Look for errors in the bot's console related to "RSSSummarizer Cog", "Gemini service", or "post_hourly_summary_loop".
    * Make sure enough articles are being collected (`RSS_MIN_ARTICLES_FOR_SUMMARY`).
