# cogs/games.py
"""
A cog for interactive games with an economy system.
Includes Connect 4, Blackjack, and Roulette.
"""
import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput
import random
import json
import os
import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple

# Assuming your config.py is in the parent directory or accessible via your Python path
# If main_bot.py and config.py are in the root, and cogs is a subdirectory:
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config # Now it should find config.py

# --- Logger Setup ---
logger = logging.getLogger(__name__)

# --- Roulette Constants (Fundamental Rules - Less likely to change via config) ---
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
        self._load_economy()

    def _load_economy(self):
        """Loads economy data from the JSON file."""
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, 'r') as f:
                    self.economy_data = json.load(f)
                logger.info(f"Economy data loaded successfully from {self.file_path}")
            else:
                self.economy_data = {}
                logger.info(f"Economy file {self.file_path} not found. Starting with empty economy.")
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON from {self.file_path}. Starting with empty economy.")
            self.economy_data = {}
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
        # No need for lock on read if writes are locked and infrequent,
        # but for safety with potential future concurrent reads/writes:
        # async with self.lock:
        return self.economy_data.get(str(user_id), self.default_balance)

    async def update_balance(self, user_id: int, amount: int) -> int:
        """
        Updates the balance of a user by a given amount (can be negative).
        Returns the new balance.
        """
        user_id_str = str(user_id)
        async with self.lock: # Ensure atomic read-modify-write for a user's balance
            current_balance = self.economy_data.get(user_id_str, self.default_balance)
            new_balance = current_balance + amount
            self.economy_data[user_id_str] = new_balance
        await self._save_economy() # Save after every update
        logger.info(f"User {user_id} balance updated by {amount}. New balance: {new_balance}")
        return new_balance

# --- Connect 4 Game ---
class Connect4Game:
    """Represents the state and logic of a Connect 4 game."""
    def __init__(self, players: List[discord.Member], bet: int):
        self.players = players  # [player1, player2]
        self.board: List[List[int]] = [[0] * 7 for _ in range(6)]  # 0: empty, 1: player1, 2: player2
        self.current_player_index: int = 0  # Index in self.players list
        self.bet: int = bet
        self.winner: Optional[discord.Member] = None
        self.is_draw: bool = False

    @property
    def current_player(self) -> discord.Member:
        return self.players[self.current_player_index]

    def make_move(self, column: int) -> Optional[Tuple[int, int]]:
        """Attempts to place a piece in the given column. Returns (row, col) if successful, else None."""
        if not (0 <= column < 7):
            return None
        for row in range(5, -1, -1):  # Iterate from bottom row up
            if self.board[row][column] == 0:
                self.board[row][column] = self.current_player_index + 1
                return row, column
        return None # Column is full

    def check_win(self, row: int, col: int) -> bool:
        """Checks if the last move resulted in a win."""
        player_piece = self.current_player_index + 1
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]  # Horizontal, Vertical, Diagonal /, Diagonal \

        for dr, dc in directions:
            count = 1
            # Check in positive direction
            for i in range(1, 4):
                r, c = row + dr * i, col + dc * i
                if 0 <= r < 6 and 0 <= c < 7 and self.board[r][c] == player_piece:
                    count += 1
                else:
                    break
            # Check in negative direction
            for i in range(1, 4):
                r, c = row - dr * i, col - dc * i
                if 0 <= r < 6 and 0 <= c < 7 and self.board[r][c] == player_piece:
                    count += 1
                else:
                    break
            if count >= 4:
                self.winner = self.current_player
                return True
        return False

    def check_draw(self) -> bool:
        """Checks if the game is a draw (board is full)."""
        if all(self.board[0][c] != 0 for c in range(7)): # Check only top row
            self.is_draw = True
            return True
        return False

    def switch_player(self):
        self.current_player_index = 1 - self.current_player_index

    def get_board_string(self) -> str:
        """Generates a string representation of the board using emojis."""
        p1_emoji = getattr(config, 'CONNECT4_PLAYER1_EMOJI', '🔴')
        p2_emoji = getattr(config, 'CONNECT4_PLAYER2_EMOJI', '🔵')
        empty_emoji = getattr(config, 'CONNECT4_EMPTY_EMOJI', '⚪')
        return "\n".join("".join([p1_emoji if cell == 1 else p2_emoji if cell == 2 else empty_emoji for cell in row]) for row in self.board)


class Connect4View(View):
    """View for handling Connect 4 game interactions."""
    def __init__(self, game: Connect4Game, economy_manager: EconomyManager, initial_message: discord.Message):
        super().__init__(timeout=getattr(config, 'CONNECT4_GAME_TIMEOUT_SECONDS', 300.0))
        self.game = game
        self.economy_manager = economy_manager
        self.initial_message = initial_message # Store the message to edit
        self._add_column_buttons()

    def _add_column_buttons(self):
        for i in range(7):
            button = Button(label=str(i + 1), style=discord.ButtonStyle.secondary, custom_id=f"c4_col_{i}")
            button.callback = self.column_button_callback
            self.add_item(button)

    async def column_button_callback(self, interaction: discord.Interaction):
        custom_id = interaction.data["custom_id"]
        column = int(custom_id.split("_")[-1])

        if interaction.user != self.game.current_player:
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return
        
        await interaction.response.defer() # Acknowledge interaction

        move_result = self.game.make_move(column)
        if move_result is None:
            await interaction.followup.send("That column is full! Try another.", ephemeral=True)
            return

        row, col = move_result
        if self.game.check_win(row, col):
            await self._end_game(interaction, winner=self.game.current_player)
        elif self.game.check_draw():
            await self._end_game(interaction, is_draw=True)
        else:
            self.game.switch_player()
            embed = self._build_embed()
            await self.initial_message.edit(embed=embed, view=self) # Edit original message

    def _build_embed(self, game_over_message: Optional[str] = None) -> discord.Embed:
        embed_color = getattr(config, 'CONNECT4_EMBED_COLOR', discord.Color.purple())
        embed = discord.Embed(title="Connect 4", color=embed_color)
        board_str = self.game.get_board_string()
        
        if game_over_message:
            embed.description = f"{board_str}\n\n**{game_over_message}**"
        else:
            embed.description = f"**Current Player:** {self.game.current_player.mention}\n{board_str}"
        
        embed.add_field(name="Player 1 (🔴)", value=self.game.players[0].mention, inline=True)
        embed.add_field(name="Player 2 (🔵)", value=self.game.players[1].mention, inline=True)
        embed.set_footer(text=f"Bet per player: {self.game.bet} coins")
        return embed

    async def _end_game(self, interaction: discord.Interaction, winner: Optional[discord.Member] = None, is_draw: bool = False):
        game_over_message = ""
        if winner:
            winnings = self.game.bet * 2 # Winner gets both bets
            await self.economy_manager.update_balance(winner.id, winnings)
            game_over_message = f"🎉 {winner.mention} wins and gets {winnings} coins!"
            logger.info(f"Connect 4 game ended. Winner: {winner.name}. Bet: {self.game.bet}")
        elif is_draw:
            # Return bets to players
            await self.economy_manager.update_balance(self.game.players[0].id, self.game.bet)
            await self.economy_manager.update_balance(self.game.players[1].id, self.game.bet)
            game_over_message = f"🤝 It's a draw! Bets of {self.game.bet} coins returned to each player."
            logger.info(f"Connect 4 game ended in a draw. Bet: {self.game.bet}")

        for item in self.children: # Disable buttons
            if isinstance(item, Button):
                item.disabled = True
        
        embed = self._build_embed(game_over_message)
        await self.initial_message.edit(embed=embed, view=self) # Edit original message
        self.stop() # Stop the view from listening to further interactions

    async def on_timeout(self):
        logger.info(f"Connect 4 game timed out. Players: {[p.name for p in self.game.players]}")
        game_over_message = "Game timed out! Bets are returned."
        # Return bets on timeout
        if not self.game.winner and not self.game.is_draw: # Ensure game hasn't already ended
            await self.economy_manager.update_balance(self.game.players[0].id, self.game.bet)
            await self.economy_manager.update_balance(self.game.players[1].id, self.game.bet)
        
        for item in self.children:
            if isinstance(item, Button):
                item.disabled = True
        embed = self._build_embed(game_over_message)
        try:
            await self.initial_message.edit(embed=embed, view=self)
        except discord.NotFound:
            logger.warning("Connect 4 game message not found on timeout, likely deleted.")
        except discord.HTTPException as e:
            logger.error(f"Failed to edit Connect 4 message on timeout: {e}")
        self.stop()

# --- Blackjack Game ---
class BlackjackGame:
    """Represents the state and logic of a Blackjack game."""
    def __init__(self, player: discord.Member, bet: int):
        self.player = player
        self.bet = bet
        self.deck = self._create_deck()
        random.shuffle(self.deck)
        self.player_hand: List[str] = []
        self.dealer_hand: List[str] = []
        self.game_over: bool = False
        self.result_message: str = ""
        self._deal_initial_hands()

    def _create_deck(self) -> List[str]:
        ranks = getattr(config, 'BLACKJACK_CARD_RANKS', ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"])
        suits = getattr(config, 'BLACKJACK_CARD_SUITS', {"♠️", "♣️", "♥️", "♦️"}) # Use set for unique suits
        return [f"{r}{s}" for s in suits for r in ranks]

    def _deal_initial_hands(self):
        for _ in range(2):
            self.player_hand.append(self.deck.pop())
            self.dealer_hand.append(self.deck.pop())

    def _calculate_hand_value(self, hand: List[str]) -> int:
        value = 0
        aces = 0
        for card in hand:
            rank = card[:-len(getattr(config, 'BLACKJACK_CARD_SUITS', {"♠️"})[0])] # Adjust based on suit emoji length
            if rank.isdigit():
                value += int(rank)
            elif rank in ["J", "Q", "K"]:
                value += 10
            elif rank == "A":
                aces += 1
                value += 11
        while value > 21 and aces > 0:
            value -= 10
            aces -= 1
        return value

    def player_value(self) -> int: return self._calculate_hand_value(self.player_hand)
    def dealer_value(self) -> int: return self._calculate_hand_value(self.dealer_hand)

    def hit(self) -> bool: # Returns True if player busts
        if not self.deck: # Should not happen with a standard deck and few players
            logger.warning("Blackjack deck is empty during hit.")
            return True # Treat as bust or error
        self.player_hand.append(self.deck.pop())
        if self.player_value() > 21:
            self.game_over = True
            self.result_message = "Bust! You lose."
            return True
        return False

    def stand(self):
        self.game_over = True
        # Dealer plays
        while self.dealer_value() < 17:
            if not self.deck: break # Stop if deck runs out
            self.dealer_hand.append(self.deck.pop())

        player_val = self.player_value()
        dealer_val = self.dealer_value()

        if dealer_val > 21:
            self.result_message = "Dealer busts! You win!"
        elif player_val > dealer_val:
            self.result_message = "You win!"
        elif player_val < dealer_val:
            self.result_message = "Dealer wins!"
        else: # Push
            self.result_message = "Push! It's a tie."


class BlackjackView(View):
    """View for handling Blackjack game interactions."""
    def __init__(self, game: BlackjackGame, economy_manager: EconomyManager, initial_message: discord.Message):
        super().__init__(timeout=getattr(config, 'BLACKJACK_GAME_TIMEOUT_SECONDS', 120.0))
        self.game = game
        self.economy_manager = economy_manager
        self.initial_message = initial_message
        self._update_button_states()

    def _update_button_states(self):
        # Disable buttons if game is over
        for item in self.children:
            if isinstance(item, Button):
                item.disabled = self.game.game_over
    
    def _build_embed(self) -> discord.Embed:
        embed_color = getattr(config, 'BLACKJACK_EMBED_COLOR', discord.Color.green())
        embed = discord.Embed(title=f"Blackjack - Bet: {self.game.bet}", color=embed_color)
        embed.add_field(name=f"{self.game.player.display_name}'s Hand ({self.game.player_value()})", value=" ".join(self.game.player_hand) or "No cards", inline=False)
        
        dealer_hand_display = ""
        if self.game.game_over:
            dealer_hand_display = " ".join(self.game.dealer_hand)
        else:
            dealer_hand_display = f"{self.game.dealer_hand[0]} {getattr(config, 'BLACKJACK_HIDDEN_CARD_EMOJI', '❓')}"
        embed.add_field(name=f"Dealer's Hand ({self.game.dealer_value() if self.game.game_over else '?'})", value=dealer_hand_display or "No cards", inline=False)

        if self.game.game_over:
            embed.description = f"**Result: {self.game.result_message}**"
        
        return embed

    async def _end_game(self, interaction: Optional[discord.Interaction]):
        self._update_button_states() # Disable buttons
        payout = 0
        player_val = self.game.player_value()
        dealer_val = self.game.dealer_value()

        if "You win!" in self.game.result_message: # Covers player win and dealer bust
            if player_val == 21 and len(self.game.player_hand) == 2 and not (dealer_val == 21 and len(self.game.dealer_hand) == 2): # Natural Blackjack
                payout = int(self.game.bet * getattr(config, 'BLACKJACK_NATURAL_PAYOUT_MULTIPLIER', 2.5))
                self.game.result_message += f" (Natural Blackjack! Pays {payout} coins)"
            else:
                payout = self.game.bet * getattr(config, 'BLACKJACK_WIN_PAYOUT_MULTIPLIER', 2)
        elif "Push!" in self.game.result_message:
            payout = self.game.bet # Bet returned
        # Loss means payout is 0, bet is already considered lost unless returned

        if payout > 0 : # This includes returning the original bet in a push
             await self.economy_manager.update_balance(self.game.player.id, payout)
        # If player loses (not a push), the bet was conceptually "lost" when placed.
        # If you deduct upfront, then on loss, nothing happens. If you deduct on loss, then:
        # elif payout == 0 and "lose" in self.game.result_message.lower():
        #    await self.economy_manager.update_balance(self.game.player.id, -self.game.bet)


        embed = self._build_embed()
        if interaction: # If called from a button press
            await self.initial_message.edit(embed=embed, view=self)
        else: # If called from timeout or other non-interaction path
            try:
                await self.initial_message.edit(embed=embed, view=self)
            except discord.NotFound:
                logger.warning("Blackjack game message not found on end_game (likely deleted).")
            except discord.HTTPException as e:
                logger.error(f"Failed to edit Blackjack message on end_game: {e}")
        self.stop()

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.success, custom_id="bj_hit")
    async def hit_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.game.player:
            await interaction.response.send_message("This isn't your game!", ephemeral=True)
            return
        await interaction.response.defer()

        if self.game.hit(): # Player busted
            await self._end_game(interaction)
        else:
            embed = self._build_embed()
            await self.initial_message.edit(embed=embed, view=self)

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.danger, custom_id="bj_stand")
    async def stand_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.game.player:
            await interaction.response.send_message("This isn't your game!", ephemeral=True)
            return
        await interaction.response.defer()
        
        self.game.stand()
        await self._end_game(interaction)

    async def on_timeout(self):
        logger.info(f"Blackjack game for {self.game.player.name} timed out.")
        if not self.game.game_over:
            self.game.game_over = True
            self.game.result_message = "Game timed out. You lose your bet."
            # On timeout, player loses their bet if game wasn't finished.
            # If bet was deducted upfront, no change needed. If not, deduct here:
            # await self.economy_manager.update_balance(self.game.player.id, -self.game.bet)
            await self._end_game(None) # No interaction for timeout
        self.stop()


# --- Roulette Game ---
class RouletteGame:
    """Represents the state and logic of a Roulette game."""
    def __init__(self, player: discord.Member, bet_amount: int):
        self.player = player
        self.bet_amount = bet_amount
        self.bet_type: Optional[str] = None  # e.g., "red", "black", "number_0", "number_15"
        self.winning_number: int = random.randint(0, 36)
        self.payout: int = 0
        self.game_over: bool = False

    def place_bet(self, bet_type: str):
        self.bet_type = bet_type

    def calculate_payout(self) -> int:
        self.game_over = True
        if self.bet_type is None: return 0

        if self.bet_type.startswith("number_"):
            try:
                chosen_number = int(self.bet_type.split("_")[1])
                if chosen_number == self.winning_number:
                    self.payout = self.bet_amount * getattr(config, 'ROULETTE_PAYOUT_NUMBER', 35)
            except ValueError:
                self.payout = 0 # Invalid bet type
        elif self.bet_type == "red" and self.winning_number in ROULETTE_RED_NUMBERS:
            self.payout = self.bet_amount * getattr(config, 'ROULETTE_PAYOUT_COLOR', 2)
        elif self.bet_type == "black" and self.winning_number in ROULETTE_BLACK_NUMBERS:
            self.payout = self.bet_amount * getattr(config, 'ROULETTE_PAYOUT_COLOR', 2)
        elif self.bet_type == "green" and self.winning_number == ROULETTE_GREEN_NUMBER: # Assuming 0 is green
            self.payout = self.bet_amount * getattr(config, 'ROULETTE_PAYOUT_GREEN', 35) # Typically same as number
        else:
            self.payout = 0
        return self.payout

    def get_winning_color(self) -> str:
        if self.winning_number == ROULETTE_GREEN_NUMBER: return "Green"
        if self.winning_number in ROULETTE_RED_NUMBERS: return "Red"
        if self.winning_number in ROULETTE_BLACK_NUMBERS: return "Black"
        return "Unknown"


class RouletteNumberModal(Modal, title="Bet on a Number (0-36)"):
    """Modal for placing a specific number bet in Roulette."""
    bet_number_input = TextInput(label="Number (0-36)", placeholder="Enter a number", min_length=1, max_length=2)

    def __init__(self, game: RouletteGame, parent_view: 'RouletteView'):
        super().__init__(timeout=getattr(config, 'ROULETTE_MODAL_TIMEOUT_SECONDS', 120.0))
        self.game = game
        self.parent_view = parent_view

    async def on_submit(self, interaction: discord.Interaction):
        try:
            number = int(self.bet_number_input.value)
            if not (0 <= number <= 36):
                await interaction.response.send_message("Invalid number. Must be between 0 and 36.", ephemeral=True)
                return
            # No defer needed here, modal submission is the response
            await self.parent_view.process_bet(interaction, f"number_{number}")
        except ValueError:
            await interaction.response.send_message("Invalid input. Please enter a number.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error in RouletteNumberModal on_submit: {e}", exc_info=True)
            await interaction.response.send_message("An error occurred processing your bet.", ephemeral=True)


class RouletteView(View):
    """View for handling Roulette game interactions."""
    def __init__(self, game: RouletteGame, economy_manager: EconomyManager, initial_message: discord.Message):
        super().__init__(timeout=getattr(config, 'ROULETTE_GAME_TIMEOUT_SECONDS', 180.0))
        self.game = game
        self.economy_manager = economy_manager
        self.initial_message = initial_message
        self._add_bet_buttons()

    def _add_bet_buttons(self):
        # Add Red, Black, Green buttons
        self.add_item(Button(label="Red", style=discord.ButtonStyle.red, custom_id="roulette_red"))
        self.add_item(Button(label="Black", style=discord.ButtonStyle.secondary, custom_id="roulette_black")) # .grey is an alias for .secondary
        self.add_item(Button(label="Green (0)", style=discord.ButtonStyle.success, custom_id="roulette_green"))
        # Add Number button
        self.add_item(Button(label="Specific Number", style=discord.ButtonStyle.primary, custom_id="roulette_number_select"))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.game.player:
            await interaction.response.send_message("This is not your game!", ephemeral=True)
            return False
        if self.game.game_over:
            await interaction.response.send_message("The game is already over!", ephemeral=True)
            return False
        return True

    async def on_button_click(self, interaction: discord.Interaction, button_id: str):
        if button_id == "roulette_number_select":
            modal = RouletteNumberModal(self.game, self)
            await interaction.response.send_modal(modal)
        else: # Red, Black, Green
            bet_type = button_id.split("_")[1]
            await self.process_bet(interaction, bet_type)

    async def process_bet(self, interaction: discord.Interaction, bet_type: str):
        """Processes the bet after a button press or modal submission."""
        # If called from modal, interaction is already responded to.
        # If called from button, we need to defer.
        if not interaction.response.is_done():
            await interaction.response.defer()

        self.game.place_bet(bet_type)
        
        # Disable buttons after bet is placed
        for item in self.children:
            if isinstance(item, Button):
                item.disabled = True

        spin_embed_color = getattr(config, 'ROULETTE_SPIN_EMBED_COLOR', discord.Color.gold())
        spin_message = getattr(config, 'ROULETTE_SPINNING_MESSAGE', "Spinning the wheel...")
        spinning_embed = discord.Embed(title="Roulette", description=spin_message, color=spin_embed_color)
        
        roulette_gif_path = getattr(config, 'ROULETTE_GIF_PATH', None)
        gif_file = None
        if roulette_gif_path and os.path.exists(roulette_gif_path):
            try:
                gif_file = discord.File(roulette_gif_path, filename=os.path.basename(roulette_gif_path))
                spinning_embed.set_image(url=f"attachment://{os.path.basename(roulette_gif_path)}")
            except Exception as e:
                logger.error(f"Failed to load roulette GIF '{roulette_gif_path}': {e}")
                gif_file = None # Ensure it's None if loading fails

        await self.initial_message.edit(embed=spinning_embed, view=self, attachments=[gif_file] if gif_file else [])

        await asyncio.sleep(getattr(config, 'ROULETTE_SPIN_DURATION_SECONDS', 5))

        self.game.calculate_payout()
        payout = self.game.payout
        winning_number = self.game.winning_number
        winning_color = self.game.get_winning_color()
        
        result_message = f"The wheel stops on **{winning_number} ({winning_color})**!\n"
        if payout > 0:
            final_payout_amount = payout # Payout includes the original bet back + winnings
            await self.economy_manager.update_balance(self.game.player.id, final_payout_amount)
            result_message += getattr(config, 'ROULETTE_WIN_MESSAGE', "Congratulations! You win **{payout_amount}** coins!").format(payout_amount=final_payout_amount)
            logger.info(f"Roulette win for {self.game.player.name}. Bet: {self.game.bet_amount} on {bet_type}. Won: {final_payout_amount}")
        else:
            # Bet was "lost" when placed. If not deducting upfront, deduct here:
            # await self.economy_manager.update_balance(self.game.player.id, -self.game.bet_amount)
            result_message += getattr(config, 'ROULETTE_LOSS_MESSAGE', "Sorry, you didn't win this time.")
            logger.info(f"Roulette loss for {self.game.player.name}. Bet: {self.game.bet_amount} on {bet_type}.")

        result_embed_color = getattr(config, 'ROULETTE_RESULT_EMBED_COLOR', discord.Color.dark_green() if payout > 0 else discord.Color.dark_red())
        result_embed = discord.Embed(title="Roulette Result", description=result_message, color=result_embed_color)
        result_embed.set_footer(text=f"You bet {self.game.bet_amount} on {bet_type.replace('_', ' ')}.")

        await self.initial_message.edit(embed=result_embed, view=self, attachments=[]) # Clear attachments
        self.stop()

    # Dynamically handle button clicks based on custom_id
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.component:
            custom_id = interaction.data.get("custom_id")
            if custom_id and custom_id.startswith("roulette_"):
                if await self.interaction_check(interaction): # Perform common checks
                    await self.on_button_click(interaction, custom_id)
            # else:
                # Fallback or error for unexpected custom_id if necessary
                # logger.warning(f"Unhandled component interaction with custom_id: {custom_id}")

    async def on_timeout(self):
        logger.info(f"Roulette game for {self.game.player.name} timed out.")
        if not self.game.game_over:
            # If game times out before bet placed, or during spin (less likely with current flow)
            for item in self.children:
                if isinstance(item, Button):
                    item.disabled = True
            timeout_message = getattr(config, 'ROULETTE_TIMEOUT_MESSAGE', "Roulette game timed out. Your bet was not processed.")
            embed = discord.Embed(title="Roulette Timeout", description=timeout_message, color=discord.Color.orange())
            try:
                await self.initial_message.edit(embed=embed, view=self, attachments=[])
            except discord.NotFound:
                 logger.warning("Roulette game message not found on timeout.")
            except discord.HTTPException as e:
                logger.error(f"Failed to edit Roulette message on timeout: {e}")
        self.stop()


# --- Games Cog ---
class Games(commands.Cog):
    """Cog for hosting various games like Connect 4, Blackjack, and Roulette."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.economy_file_path = getattr(config, 'ECONOMY_FILE_PATH', 'data/economy.json')
        # Ensure the directory for the economy file exists
        os.makedirs(os.path.dirname(self.economy_file_path), exist_ok=True)

        self.economy_lock = asyncio.Lock()
        self.economy_manager = EconomyManager(
            file_path=self.economy_file_path,
            default_balance=getattr(config, 'ECONOMY_DEFAULT_BALANCE', 100),
            lock=self.economy_lock
        )
        logger.info(f"Games Cog loaded. Economy manager initialized with file: {self.economy_file_path}")

    async def cog_check(self, ctx: commands.Context) -> bool:
        """Cog-wide check to ensure commands are not used in DMs if not intended."""
        if ctx.guild is None and not getattr(config, 'ALLOW_GAMES_IN_DMS', False):
            await ctx.send("Game commands are typically used in servers.")
            return False
        return True

    async def common_bet_validation(self, ctx: commands.Context, bet: int, min_bet: int, user_id: Optional[int] = None) -> bool:
        """Common validation for bet amounts and player balance."""
        if user_id is None: user_id = ctx.author.id

        if bet < min_bet:
            min_bet_msg = getattr(config, 'GAMES_MIN_BET_MESSAGE', "Minimum bet is {min_bet} coins.")
            await ctx.send(min_bet_msg.format(min_bet=min_bet))
            return False
        
        balance = await self.economy_manager.get_balance(user_id)
        if balance < bet:
            low_bal_msg = getattr(config, 'GAMES_INSUFFICIENT_FUNDS_MESSAGE', "You don't have enough coins! Your balance: {balance}")
            await ctx.send(low_bal_msg.format(balance=balance))
            return False
        return True

    @commands.command(name="balance", aliases=["bal", "money"], help="Check your current coin balance.")
    async def balance(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        target_user = member or ctx.author
        balance = await self.economy_manager.get_balance(target_user.id)
        bal_msg = getattr(config, 'GAMES_BALANCE_MESSAGE', "{user_mention}'s balance: **{balance}** coins.")
        await ctx.send(bal_msg.format(user_mention=target_user.mention, balance=balance))
        logger.info(f"Balance check for {target_user.name} by {ctx.author.name}: {balance} coins.")

    @commands.command(name="connect4", aliases=["c4"], help="Play Connect 4 with another player for a bet.")
    @commands.guild_only()
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
        if not await self.common_bet_validation(ctx, bet, min_bet, opponent.id):
            # Adjust message for opponent
            opp_low_bal_msg = getattr(config, 'GAMES_OPPONENT_INSUFFICIENT_FUNDS_MESSAGE', "{opponent_name} doesn't have enough coins (Balance: {opponent_balance}).")
            opp_balance = await self.economy_manager.get_balance(opponent.id)
            await ctx.send(opp_low_bal_msg.format(opponent_name=opponent.display_name, opponent_balance=opp_balance))
            return

        # Deduct bets upfront
        await self.economy_manager.update_balance(ctx.author.id, -bet)
        await self.economy_manager.update_balance(opponent.id, -bet)
        logger.info(f"Connect 4 game initiated between {ctx.author.name} and {opponent.name} for {bet} coins each.")

        game = Connect4Game([ctx.author, opponent], bet)
        
        # Send initial message and then pass it to the view for editing
        initial_embed = discord.Embed(title="Connect 4", description="Setting up the game...", color=getattr(config, 'CONNECT4_EMBED_COLOR', discord.Color.purple()))
        initial_message = await ctx.send(embed=initial_embed) # Send first, then pass to view

        view = Connect4View(game, self.economy_manager, initial_message)
        # Now edit the message with the view and proper initial board state
        final_initial_embed = view._build_embed()
        await initial_message.edit(embed=final_initial_embed, view=view)


    @commands.command(name="blackjack", aliases=["bj"], help="Play Blackjack against the dealer for a bet.")
    @commands.cooldown(1, getattr(config, 'BLACKJACK_COOLDOWN_SECONDS', 10), commands.BucketType.user)
    async def blackjack(self, ctx: commands.Context, bet: int):
        min_bet = getattr(config, 'BLACKJACK_MIN_BET', 1)
        if not await self.common_bet_validation(ctx, bet, min_bet): return
        
        # Deduct bet upfront (or handle payouts to include returning bet on win/push)
        # For simplicity, let's assume bet is taken and winnings are net profit + original bet.
        # If player loses, the bet is gone. If they push, bet is returned.
        # Current BlackjackGame logic assumes bet is "at stake" and payouts are total returns.
        # So, no deduction here. Payouts will handle it.
        # await self.economy_manager.update_balance(ctx.author.id, -bet) # Example if deducting upfront

        logger.info(f"Blackjack game started by {ctx.author.name} for {bet} coins.")
        game = BlackjackGame(ctx.author, bet)
        
        initial_message = await ctx.send(embed=discord.Embed(title="Blackjack", description="Dealing cards...", color=getattr(config, 'BLACKJACK_EMBED_COLOR', discord.Color.green())))
        view = BlackjackView(game, self.economy_manager, initial_message)
        
        initial_embed = view._build_embed() # Get embed with initial hands
        await initial_message.edit(embed=initial_embed, view=view)

    @commands.command(name="roulette", help="Play Roulette with various betting options.")
    @commands.cooldown(1, getattr(config, 'ROULETTE_COOLDOWN_SECONDS', 15), commands.BucketType.user)
    async def roulette(self, ctx: commands.Context, bet: int):
        min_bet = getattr(config, 'ROULETTE_MIN_BET', 1)
        if not await self.common_bet_validation(ctx, bet, min_bet): return

        # Bet is "at stake". Payouts will handle adding winnings or doing nothing on loss.
        # If deducting upfront:
        # await self.economy_manager.update_balance(ctx.author.id, -bet)
        logger.info(f"Roulette game started by {ctx.author.name} for {bet} coins.")

        game = RouletteGame(ctx.author, bet)
        
        initial_embed_color = getattr(config, 'ROULETTE_INITIAL_EMBED_COLOR', discord.Color.gold())
        initial_embed_msg = getattr(config, 'ROULETTE_PLACE_BET_MESSAGE', "Place your bet by choosing an option below!")
        initial_embed = discord.Embed(title=f"Roulette - Bet: {bet}", description=initial_embed_msg, color=initial_embed_color)
        
        initial_message = await ctx.send(embed=initial_embed)
        view = RouletteView(game, self.economy_manager, initial_message)
        await initial_message.edit(view=view) # Add the view to the sent message

    # --- Error Handlers for Game Commands ---
    async def game_command_error_handler(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"You're missing an argument: `{error.param.name}`. Try `{ctx.prefix}help {ctx.command.qualified_name}`.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("Invalid argument provided. Please check the command usage.")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"This command is on cooldown. Try again in {error.retry_after:.2f} seconds.")
        elif isinstance(error, commands.GuildOnly):
            await ctx.send("This game can only be played in a server.")
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

    @balance.error # Added error handler for balance
    async def balance_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.BadArgument): # e.g. invalid member
            await ctx.send("Could not find that member. Please try again.")
        else:
            await self.game_command_error_handler(ctx,error)


async def setup(bot: commands.Bot):
    """Sets up the Games cog."""
    # Ensure the 'data' directory (or configured path) exists for economy.json
    economy_dir = os.path.dirname(getattr(config, 'ECONOMY_FILE_PATH', 'data/economy.json'))
    if economy_dir and not os.path.exists(economy_dir): # Check if economy_dir is not empty string
        try:
            os.makedirs(economy_dir, exist_ok=True)
            logger.info(f"Created directory for economy file: {economy_dir}")
        except OSError as e:
            logger.error(f"Could not create directory {economy_dir}: {e}")
            # Potentially raise an error or prevent cog loading if directory creation is critical
            # For now, we'll let it try to proceed, EconomyManager will log if file can't be accessed.

    await bot.add_cog(Games(bot))
    logger.info("Games cog has been setup and added to the bot.")

