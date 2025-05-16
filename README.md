# OSDEB
Open Source Discord Entertainment Bot

This is a largely open source AI generated project i have created as a basic discord bot. some of the features include:
Gemini API access + commands - Gemini API is FREE for personal use. i am not responsible for using the API for commercial use
incredibly basic economy system using JSON
Largly a music bot that supports Soundcloud and any other services that dont require API Access to play from them. the bot also has the ability to use local files in the Music Folder
This is also a largely modular bot with cogs and commands being stored in separate files from the main python file.
Best command is being able to fish someone which takes a image from the fish folder and messages the target with a random image of a fish. cause why not?

For what its worth, its definitely not anything amazing but its good enough for basic use™ 
Dont be a penis with the code and everything will be fine and work.

# Discord Bot Setup Guide

This guide provides instructions on how to set up and run this multi-functional Discord bot.

## Prerequisites

1.  **Python**: Ensure you have Python 3.8 or newer installed. You can download it from [python.org](https://www.python.org/).
2.  **FFmpeg**: Required for the music cog to play audio.
    * **Windows**: Download from [FFmpeg Official Site](https://ffmpeg.org/download.html) (select a Windows build). Extract it and add the `bin` folder (containing `ffmpeg.exe`) to your system's PATH environment variable.
    * **Linux (Debian/Ubuntu)**: `sudo apt update && sudo apt install ffmpeg`
    * **macOS (using Homebrew)**: `brew install ffmpeg`
3.  **Discord Bot Token**: You'll need a token for your bot from the [Discord Developer Portal](https://discord.com/developers/applications).
4.  **(Optional) Google Gemini API Key**: If you plan to use the Gemini AI features, obtain an API key from [Google AI Studio](https://aistudio.google.com/app/apikey).

## Setup Instructions

1.  **Clone/Download Files**:
    * Place all the bot files (`main_bot.py`, `config.py`, `gemini_service.py`, and the `cogs` directory with all its Python files like `music.py`, `fun.py`, `games.py`, `store.py`, `voice.py`) into a single project folder.
    * Create the necessary subdirectories as specified in `config.py` (e.g., `data/` for economy/store files, `sounds/` for interrupt sounds, `assets/gifs/` for roulette GIF, `Images/` and `fish/` for the Fun cog).

2.  **Create a Virtual Environment (Recommended)**:
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # Linux/macOS
    source venv/bin/activate
    ```

3.  **Install Dependencies**:
    * Create a `requirements.txt` file in your project folder with the content provided in the "requirements.txt" Canvas.
    * Install the required Python libraries:
        ```bash
        pip install -r requirements.txt
        ```
        *Note: PyNaCl is usually a dependency of `discord.py` for voice, so it should be installed automatically. If you encounter voice issues, you might need to install it manually: `pip install PyNaCl`.*

4.  **Configure the Bot (`config.py`)**:
    * Open `config.py` and fill in all the required fields:
        * `BOT_TOKEN`: Your Discord bot token.
        * `OWNER_ID`: Your Discord user ID.
        * `GEMINI_API_KEY`: Your Google Gemini API key (if using Gemini features).
        * Review and adjust all paths (e.g., `ECONOMY_FILE_PATH`, `STORE_FILE_PATH`, `MUSIC_INTRO_PATH`, `VOICE_INTERRUPT_SOUND_PATH`, `ROULETTE_GIF_PATH`, `SNAP_MEDIA_FOLDER`, `FISH_IMAGES_FOLDER`). Ensure these paths are correct relative to where `main_bot.py` will run.
        * Set `TARGET_GUILD_ID_FOR_PRESENCE` if you want music presence tied to a specific server.
        * Customize lists like `JOKES_LIST` and `COGS_TO_LOAD`.
        * Review all other settings (timeouts, messages, emojis, etc.) and adjust as needed.

5.  **Add Assets**:
    * Place your intro sounds, interrupt sounds, roulette GIFs, images for the `snap` command, and fish images into the respective folders defined in `config.py`.

6.  **Run the Bot**:
    ```bash
    python main_bot.py
    ```
    You should see log messages in your console indicating the bot is connecting and cogs are loading.

## Standard Bot Commands (Examples)

The command prefix is typically `!` (configurable in `config.py`).

**General:**
* `!help`: (If a help command is implemented, often provided by a default cog or a custom one) Shows available commands.

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

**Music Cog (`cogs/music.py` - assuming `MusicV2` refactor):**
* `!join`: Bot joins your voice channel.
* `!leave` (or `!dc`): Bot leaves the voice channel and clears the queue.
* `!play <song name or URL>` (or `!p`): Plays a song or adds it/playlist to the queue.
* `!skip` (or `!s`): Skips the current song.
* `!stop`: Stops playback, clears queue, and leaves.
* `!queue` (or `!q`): Shows the music queue.
* `!nowplaying` (or `!np`): Shows the currently playing song.
* `!loop`: Toggles looping for the current song.
* `!remove <position>`: Removes a song from the queue by its position number.
* `!volume <0-200>`: Sets the player volume.

**Store Cog (`cogs/store.py`):**
* `!store`: Displays items available for purchase.
* `!balance [@User]`: (Shared with Games cog) Checks coin balance.
* `!addstoreitem`: (Admin) Opens a prompt/modal to add an item to the store.
* `!removestoreitem <item_id>`: (Admin) Removes an item from the store by its ID.

**Voice Interrupt Cog (`cogs/voice.py`):**
* `!setinterrupttarget @User` (or `!settarget`): (Admin) Sets a user to be "interrupted" with a sound when they join/speak in VC.
* `!clearinterrupttarget`: (Admin) Clears the interrupt target.

**Gemini AI (if `gemini_service.py` and command in `main_bot.py` are used):**
* `!gemini <prompt>`: Sends a prompt to the Gemini AI and gets a response.

*This is a general list based on the cogs developed. Specific command names, aliases, and permissions might vary based on the final configuration and code.*

## Troubleshooting
* **"FFmpeg/AVConv not found"**: Ensure FFmpeg is installed correctly and its `bin` directory is in your system's PATH.
* **No Sound/Music Issues**:
    * Check FFmpeg installation.
    * Ensure the bot has `Connect` and `Speak` permissions in the voice channel.
    * Verify `PyNaCl` is installed (`pip show PyNaCl`).
    * Check `yt-dlp` is up-to-date (`pip install --upgrade yt-dlp`).
    * Look for errors in the bot's console logs.
* **Cog Loading Errors**: Check the console for messages like "Failed to load extension". This usually indicates an error within the cog file itself or a missing dependency.
* **File Not Found (economy.json, store.json, sound files)**: Ensure the paths in `config.py` are correct and the bot has permissions to read/write to those locations. Make sure the specified directories exist.

