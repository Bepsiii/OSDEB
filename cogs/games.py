# cogs/games.py
"""
A cog for interactive games with an economy system.
Includes Connect 4, Blackjack, and Roulette.
"""
import discord
from discord.ext import commands, tasks # tasks might not be used here but often is in cogs
import json
import os
import asyncio
import logging
import random # Ensure random is imported if used by games
from typing import List, Dict, Any, Optional, Tuple

# Assuming your config.py is in the parent directory or accessible via your Python path
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config 

# --- Logger Setup ---
logger = logging.getLogger(__name__)

# --- Roulette Constants (Fundamental Rules) ---
ROULETTE_RED_NUMBERS = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
ROULETTE_BLACK_NUMBERS = [2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35]
ROULETTE_GREEN_NUMBER = 0


class EconomyManager:
    """Manages player balances stored in a JSON file."""
    def __init__(self, file_path: str, default_balance: int, lock: asyncio.Lock):
        self.file_path = file_path
        self.default_balance = default_balance
        self.lock = lock
        self.economy_data: Dict[str, int] = {}
        self._load_economy() # Load data on initialization

    def _load_economy(self):
        """Loads economy data from the JSON file."""
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, 'r') as f:
                    self.economy_data = json.load(f)
                logger.info(f"Economy data loaded successfully from {self.file_path}")
            else:
                self.economy_data = {}
                # Create the file if it doesn't exist
                with open(self.file_path, 'w') as f:
                    json.dump({}, f, indent=4) # Save an empty JSON object
                logger.info(f"Economy file {self.file_path} not found. Created an empty economy file.")
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON from {self.file_path}. Recreating with an empty economy.")
            self.economy_data = {}
            with open(self.file_path, 'w') as f: # Overwrite corrupted file
                json.dump({}, f, indent=4)
        except Exception as e:
            logger.error(f"Unexpected error loading economy data: {e}", exc_info=True)
            self.economy_data = {}

    async def _save_economy(self):
        """Saves the current economy data to the JSON file."""
        async with self.lock:
            try:
                with open(self.file_path, 'w') as f:
                    json.dump(self.economy_data, f, indent=4)
                logger.debug(f"Economy data saved to {self.file_path}")
            except Exception as e:
                logger.error(f"Error saving economy data to {self.file_path}: {e}", exc_info=True)

    async def get_balance(self, user_id: int) -> int:
        """Gets the balance of a user."""
        # Reading can be done without lock if writes are infrequent and locked,
        # but for absolute safety or more complex scenarios, locking reads is safer.
        # For this simple JSON case, it's likely fine without lock for reads.
        return self.economy_data.get(str(user_id), self.default_balance)

    async def update_balance(self, user_id: int, amount: int) -> int:
        """
        Updates the balance of a user by a given amount (can be negative).
        Returns the new balance.
        """
        user_id_str = str(user_id)
        # Ensure atomic read-modify-write for a user's balance
        async with self.lock:
            current_balance = self.economy_data.get(user_id_str, self.default_balance)
            new_balance = current_balance + amount
            self.economy_data[user_id_str] = new_balance
        
        await self._save_economy() # Save after every update
        logger.info(f"User {user_id} balance updated by {amount}. New balance: {new_balance}")
        return new_balance

# --- Game Classes (Connect4Game, BlackjackGame, RouletteGame, and their Views) ---
# These classes should be the same as in `games_cog_py_refactored` from previous turns.
# For brevity, I'm not re-pasting them here, but ensure they are present in your actual file.
# Make sure they use `Optional`, `List`, `Tuple` from `typing` where needed.

# Example placeholder for Connect4Game (ensure full class is present)
class Connect4Game:
    def __init__(self, players: List[discord.Member], bet: int):
        self.players = players; self.bet = bet; self.board = [[0]*7 for _ in range(6)]; self.current_player_index = 0; self.winner = None; self.is_draw = False
    @property
    def current_player(self) -> discord.Member: return self.players[self.current_player_index]
    def make_move(self, column: int) -> Optional[Tuple[int, int]]: return (0,0) # Simplified
    def check_win(self, row: int, col: int) -> bool: return False # Simplified
    def check_draw(self) -> bool: return False # Simplified
    def switch_player(self): self.current_player_index = 1 - self.current_player_index
    def get_board_string(self) -> str: return "Board placeholder"

class Connect4View(View):
    def __init__(self, game: Connect4Game, economy_manager: EconomyManager, initial_message: discord.Message):
        super().__init__(timeout=getattr(config, 'CONNECT4_GAME_TIMEOUT_SECONDS', 300.0)); self.game = game; self.economy_manager = economy_manager; self.initial_message = initial_message; self._add_column_buttons()
    def _add_column_buttons(self): pass # Simplified
    async def column_button_callback(self, interaction: discord.Interaction): pass # Simplified
    def _build_embed(self, game_over_message: Optional[str] = None) -> discord.Embed: return discord.Embed(title="Connect4") # Simplified
    async def _end_game(self, interaction: discord.Interaction, winner: Optional[discord.Member] = None, is_draw: bool = False): self.stop() # Simplified
    async def on_timeout(self): self.stop() # Simplified

# Example placeholder for BlackjackGame
class BlackjackGame:
    def __init__(self, player: discord.Member, bet: int): self.player = player; self.bet = bet; self.deck = []; self.player_hand = []; self.dealer_hand = []; self.game_over = False; self.result_message = ""
    def _create_deck(self) -> List[str]: return []
    def _deal_initial_hands(self): pass
    def _calculate_hand_value(self, hand: List[str]) -> int: return 0
    def player_value(self) -> int: return 0
    def dealer_value(self) -> int: return 0
    def hit(self) -> bool: return False
    def stand(self): self.game_over = True

class BlackjackView(View):
    def __init__(self, game: BlackjackGame, economy_manager: EconomyManager, initial_message: discord.Message): super().__init__(timeout=getattr(config, 'BLACKJACK_GAME_TIMEOUT_SECONDS', 120.0)); self.game = game; self.economy_manager = economy_manager; self.initial_message = initial_message
    def _update_button_states(self): pass
    def _build_embed(self) -> discord.Embed: return discord.Embed(title="Blackjack")
    async def _end_game(self, interaction: Optional[discord.Interaction]): self.stop()
    @discord.ui.button(label="Hit", style=discord.ButtonStyle.success, custom_id="bj_hit")
    async def hit_button(self, interaction: discord.Interaction, button: Button): pass
    @discord.ui.button(label="Stand", style=discord.ButtonStyle.danger, custom_id="bj_stand")
    async def stand_button(self, interaction: discord.Interaction, button: Button): pass
    async def on_timeout(self): self.stop()

# Example placeholder for RouletteGame
class RouletteGame:
    def __init__(self, player: discord.Member, bet_amount: int): self.player = player; self.bet_amount = bet_amount; self.bet_type = None; self.winning_number = 0; self.payout = 0; self.game_over = False
    def place_bet(self, bet_type: str): self.bet_type = bet_type
    def calculate_payout(self) -> int: self.game_over = True; return 0
    def get_winning_color(self) -> str: return "Red"

class RouletteNumberModal(Modal, title="Bet on a Number (0-36)"):
    bet_number_input = TextInput(label="Number (0-36)"); def __init__(self, game: RouletteGame, parent_view: 'RouletteView'): super().__init__(); self.game = game; self.parent_view = parent_view
    async def on_submit(self, interaction: discord.Interaction): pass

class RouletteView(View):
    def __init__(self, game: RouletteGame, economy_manager: EconomyManager, initial_message: discord.Message): super().__init__(timeout=getattr(config, 'ROULETTE_GAME_TIMEOUT_SECONDS', 180.0)); self.game = game; self.economy_manager = economy_manager; self.initial_message = initial_message; self._add_bet_buttons()
    def _add_bet_buttons(self): pass
    async def interaction_check(self, interaction: discord.Interaction) -> bool: return True
    async def on_button_click(self, interaction: discord.Interaction, button_id: str): pass
    async def process_bet(self, interaction: discord.Interaction, bet_type: str): self.stop()
    async def on_interaction(self, interaction: discord.Interaction): pass
    async def on_timeout(self): self.stop()


# --- Games Cog ---
class GamesCog(commands.Cog, name="Games"): # Renamed to GamesCog for clarity
    """Cog for hosting various games like Connect 4, Blackjack, and Roulette."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.economy_file_path = getattr(config, 'ECONOMY_FILE_PATH', 'data/economy.json')
        
        # Ensure the directory for the economy file exists
        economy_dir = os.path.dirname(self.economy_file_path)
        if economy_dir and not os.path.exists(economy_dir): # Check if economy_dir is not empty string
            try:
                os.makedirs(economy_dir, exist_ok=True)
                logger.info(f"Created directory for economy file: {economy_dir}")
            except OSError as e:
                logger.error(f"Could not create directory {economy_dir}: {e}")
                # Depending on severity, you might want to raise an error or prevent cog loading

        self.economy_lock = asyncio.Lock()
        self.economy_manager = EconomyManager( # Initialize EconomyManager
            file_path=self.economy_file_path,
            default_balance=getattr(config, 'ECONOMY_DEFAULT_BALANCE', 100),
            lock=self.economy_lock
        )
        # --- CRITICAL: Attach EconomyManager to the bot instance ---
        self.bot.economy_manager = self.economy_manager
        logger.info(f"Games Cog loaded. Economy manager initialized and attached to bot instance (bot.economy_manager). File: {self.economy_file_path}")


    async def cog_check(self, ctx: commands.Context) -> bool:
        """Cog-wide check to ensure commands are not used in DMs if not intended."""
        if ctx.guild is None and not getattr(config, 'ALLOW_GAMES_IN_DMS', False):
            # Using the configured message for this specific check
            await ctx.send(getattr(config, 'MUSIC_MSG_GUILD_ONLY', "Game commands are typically used in servers."))
            return False
        return True

    async def common_bet_validation(self, ctx: commands.Context, bet: int, min_bet: int, user_id: Optional[int] = None) -> bool:
        """Common validation for bet amounts and player balance."""
        target_user_id = user_id if user_id is not None else ctx.author.id

        if bet < min_bet:
            min_bet_msg = getattr(config, 'GAMES_MIN_BET_MESSAGE', "Minimum bet is {min_bet} coins.")
            await ctx.send(min_bet_msg.format(min_bet=min_bet))
            return False
        
        balance = await self.economy_manager.get_balance(target_user_id)
        if balance < bet:
            # For opponent checks, a more specific message might be needed if user_id is opponent's
            if user_id and user_id != ctx.author.id:
                opponent = await self.bot.fetch_user(user_id) # Fetch user for display name
                opp_low_bal_msg = getattr(config, 'GAMES_OPPONENT_INSUFFICIENT_FUNDS_MESSAGE', "{opponent_name} doesn't have enough coins (Balance: {opponent_balance}).")
                await ctx.send(opp_low_bal_msg.format(opponent_name=opponent.display_name, opponent_balance=balance))
            else: # For the command author
                low_bal_msg = getattr(config, 'GAMES_INSUFFICIENT_FUNDS_MESSAGE', "You don't have enough coins! Your balance: {balance}")
                await ctx.send(low_bal_msg.format(balance=balance))
            return False
        return True

    @commands.command(name="balance", aliases=["bal", "money"], help="Check your current coin balance.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def balance(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        target_user = member or ctx.author
        balance_val = await self.economy_manager.get_balance(target_user.id)
        currency_name = getattr(config, 'ECONOMY_CURRENCY_NAME', 'coins') # Get currency name
        bal_msg = getattr(config, 'GAMES_BALANCE_MESSAGE', "{user_mention}'s balance: **{balance}** {currency}.")
        
        # --- FIX: Added currency=currency_name to .format() ---
        await ctx.send(bal_msg.format(user_mention=target_user.mention, balance=balance_val, currency=currency_name))
        logger.info(f"Balance check for {target_user.name} by {ctx.author.name}: {balance_val} {currency_name}.")

    @commands.command(name="connect4", aliases=["c4"], help="Play Connect 4 with another player for a bet.")
    @commands.guild_only() # Ensures command is used in a guild
    @commands.cooldown(1, getattr(config, 'CONNECT4_COOLDOWN_SECONDS', 30), commands.BucketType.channel)
    async def connect4(self, ctx: commands.Context, opponent: discord.Member, bet: int):
        min_bet = getattr(config, 'CONNECT4_MIN_BET', 1)
        if ctx.author == opponent:
            await ctx.send(getattr(config, 'CONNECT4_CANNOT_PLAY_SELF_MESSAGE', "You can't play against yourself!"))
            return
        if opponent.bot:
            await ctx.send(getattr(config, 'CONNECT4_CANNOT_PLAY_BOT_MESSAGE', "You can't play against a bot!"))
            return

        if not await self.common_bet_validation(ctx, bet, min_bet, ctx.author.id): return
        if not await self.common_bet_validation(ctx, bet, min_bet, opponent.id): return # common_bet_validation now sends specific opponent message

        await self.economy_manager.update_balance(ctx.author.id, -bet)
        await self.economy_manager.update_balance(opponent.id, -bet)
        logger.info(f"Connect 4 game initiated between {ctx.author.name} and {opponent.name} for {bet} coins each.")

        game = Connect4Game([ctx.author, opponent], bet)
        initial_embed = discord.Embed(title="Connect 4", description="Setting up the game...", color=getattr(config, 'CONNECT4_EMBED_COLOR', discord.Color.purple()))
        initial_message = await ctx.send(embed=initial_embed) 
        view = Connect4View(game, self.economy_manager, initial_message)
        final_initial_embed = view._build_embed()
        await initial_message.edit(embed=final_initial_embed, view=view)


    @commands.command(name="blackjack", aliases=["bj"], help="Play Blackjack against the dealer for a bet.")
    @commands.cooldown(1, getattr(config, 'BLACKJACK_COOLDOWN_SECONDS', 10), commands.BucketType.user)
    async def blackjack(self, ctx: commands.Context, bet: int):
        min_bet = getattr(config, 'BLACKJACK_MIN_BET', 1)
        if not await self.common_bet_validation(ctx, bet, min_bet): return
        
        logger.info(f"Blackjack game started by {ctx.author.name} for {bet} coins.")
        game = BlackjackGame(ctx.author, bet)
        initial_message = await ctx.send(embed=discord.Embed(title="Blackjack", description="Dealing cards...", color=getattr(config, 'BLACKJACK_EMBED_COLOR', discord.Color.green())))
        view = BlackjackView(game, self.economy_manager, initial_message)
        initial_embed = view._build_embed() 
        await initial_message.edit(embed=initial_embed, view=view)

    @commands.command(name="roulette", help="Play Roulette with various betting options.")
    @commands.cooldown(1, getattr(config, 'ROULETTE_COOLDOWN_SECONDS', 15), commands.BucketType.user)
    async def roulette(self, ctx: commands.Context, bet: int):
        min_bet = getattr(config, 'ROULETTE_MIN_BET', 1)
        if not await self.common_bet_validation(ctx, bet, min_bet): return

        logger.info(f"Roulette game started by {ctx.author.name} for {bet} coins.")
        game = RouletteGame(ctx.author, bet)
        initial_embed_color = getattr(config, 'ROULETTE_INITIAL_EMBED_COLOR', discord.Color.gold())
        initial_embed_msg = getattr(config, 'ROULETTE_PLACE_BET_MESSAGE', "Place your bet by choosing an option below!")
        initial_embed = discord.Embed(title=f"Roulette - Bet: {bet}", description=initial_embed_msg, color=initial_embed_color)
        initial_message = await ctx.send(embed=initial_embed)
        view = RouletteView(game, self.economy_manager, initial_message)
        await initial_message.edit(view=view) 

    # --- Error Handlers for Game Commands ---
    async def game_command_error_handler(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"You're missing an argument: `{error.param.name}`. Try `{ctx.prefix}help {ctx.command.qualified_name}`.")
        elif isinstance(error, commands.BadArgument): # Catches failed Member, int conversions etc.
            await ctx.send(f"Invalid argument provided for `{error.param.name if hasattr(error, 'param') else 'argument'}`. Please check the command usage.")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"This command is on cooldown. Try again in {error.retry_after:.2f} seconds.")
        # --- FIX: Changed commands.GuildOnly to commands.NoPrivateMessage ---
        elif isinstance(error, commands.NoPrivateMessage): # Corrected exception type
            await ctx.send("This game can only be played in a server.")
        elif isinstance(error, commands.CommandInvokeError) and isinstance(error.original, KeyError) and 'currency' in str(error.original):
             # Specific handling for the currency KeyError if it still somehow occurs
            logger.error(f"KeyError for 'currency' in command {ctx.command.qualified_name}: {error.original}", exc_info=True)
            await ctx.send("There was an issue displaying your balance message. The currency name might be missing in config.")
        else:
            logger.error(f"Unhandled error in command {ctx.command.qualified_name}: {error}", exc_info=True)
            await ctx.send("An unexpected error occurred while running this game command.")

    @connect4.error
    async def connect4_error(self, ctx: commands.Context, error: commands.CommandError):
        await self.game_command_error_handler(ctx, error)

    @blackjack.error
    async def blackjack_error(self, ctx: commands.Context, error: commands.CommandError):
        await self.game_command_error_handler(ctx, error)

    @roulette.error
    async def roulette_error(self, ctx: commands.Context, error: commands.CommandError):
        await self.game_command_error_handler(ctx, error)

    @balance.error 
    async def balance_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.BadArgument) and isinstance(error.param, commands.parameters.Parameter) and error.param.name == 'member':
            await ctx.send("Could not find that member. Please try again or check the name/ID.")
        else: # Delegate to the more general handler
            await self.game_command_error_handler(ctx,error)


async def setup(bot: commands.Bot):
    """Sets up the GamesCog."""
    # Ensure the 'data' directory (or configured path) exists for economy.json
    economy_dir = os.path.dirname(getattr(config, 'ECONOMY_FILE_PATH', 'data/economy.json'))
    if economy_dir and not os.path.exists(economy_dir): 
        try:
            os.makedirs(economy_dir, exist_ok=True)
            logger.info(f"Created directory for economy file: {economy_dir}")
        except OSError as e:
            logger.error(f"Could not create directory {economy_dir}: {e}")
            # Potentially raise an error or prevent cog loading if directory creation is critical
    
    # The EconomyManager is initialized within the cog's __init__ and attached to bot.economy_manager
    await bot.add_cog(GamesCog(bot)) # Renamed to GamesCog
    logger.info("GamesCog has been setup and added to the bot.")

