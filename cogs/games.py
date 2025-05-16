# cogs/games.py
"""
A cog for interactive games with an economy system.
Includes Connect 4, Blackjack, and Roulette.
"""
import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Modal, TextInput # Ensure View, Modal, TextInput are imported
import json
import os
import asyncio
import logging
import random
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
                with open(self.file_path, 'w') as f:
                    json.dump({}, f, indent=4) 
                logger.info(f"Economy file {self.file_path} not found. Created an empty economy file.")
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON from {self.file_path}. Recreating with an empty economy.")
            self.economy_data = {}
            with open(self.file_path, 'w') as f: 
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
        return self.economy_data.get(str(user_id), self.default_balance)

    async def update_balance(self, user_id: int, amount: int) -> int:
        """
        Updates the balance of a user by a given amount (can be negative).
        Returns the new balance.
        """
        user_id_str = str(user_id)
        async with self.lock:
            current_balance = self.economy_data.get(user_id_str, self.default_balance)
            new_balance = current_balance + amount
            self.economy_data[user_id_str] = new_balance
        await self._save_economy() 
        logger.info(f"User {user_id} balance updated by {amount}. New balance: {new_balance}")
        return new_balance

# --- Connect 4 Game ---
class Connect4Game:
    """Represents the state and logic of a Connect 4 game."""
    def __init__(self, players: List[discord.Member], bet: int):
        self.players = players
        self.board: List[List[int]] = [[0] * 7 for _ in range(6)]
        self.current_player_index: int = 0
        self.bet: int = bet
        self.winner: Optional[discord.Member] = None
        self.is_draw: bool = False

    @property
    def current_player(self) -> discord.Member:
        return self.players[self.current_player_index]

    def make_move(self, column: int) -> Optional[Tuple[int, int]]:
        if not (0 <= column < 7): return None
        for row in range(5, -1, -1):
            if self.board[row][column] == 0:
                self.board[row][column] = self.current_player_index + 1
                return row, column
        return None

    def check_win(self, row: int, col: int) -> bool:
        player_piece = self.current_player_index + 1
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        for dr, dc in directions:
            count = 1
            for i in range(1, 4): # Check positive direction
                r, c = row + dr * i, col + dc * i
                if 0 <= r < 6 and 0 <= c < 7 and self.board[r][c] == player_piece: count += 1
                else: break
            for i in range(1, 4): # Check negative direction
                r, c = row - dr * i, col - dc * i
                if 0 <= r < 6 and 0 <= c < 7 and self.board[r][c] == player_piece: count += 1
                else: break
            if count >= 4: self.winner = self.current_player; return True
        return False

    def check_draw(self) -> bool:
        if all(self.board[0][c] != 0 for c in range(7)): self.is_draw = True; return True
        return False

    def switch_player(self):
        self.current_player_index = 1 - self.current_player_index

    def get_board_string(self) -> str:
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
        self.initial_message = initial_message
        self._add_column_buttons()

    def _add_column_buttons(self):
        for i in range(7):
            button = Button(label=str(i + 1), style=discord.ButtonStyle.secondary, custom_id=f"c4_col_{i}")
            button.callback = self.column_button_callback # Assign method directly
            self.add_item(button)

    async def column_button_callback(self, interaction: discord.Interaction):
        # Extract column from custom_id (assuming custom_id is like "c4_col_X")
        try:
            column = int(interaction.data["custom_id"].split("_")[-1])
        except (IndexError, ValueError):
            logger.error(f"Connect4View: Could not parse column from custom_id '{interaction.data['custom_id']}'")
            await interaction.response.send_message("Error processing your move.", ephemeral=True)
            return

        if interaction.user != self.game.current_player:
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return
        
        await interaction.response.defer() 

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
            await self.initial_message.edit(embed=embed, view=self) 

    def _build_embed(self, game_over_message: Optional[str] = None) -> discord.Embed:
        embed_color = getattr(config, 'CONNECT4_EMBED_COLOR', discord.Color.purple())
        embed = discord.Embed(title="Connect 4", color=embed_color)
        board_str = self.game.get_board_string()
        
        if game_over_message:
            embed.description = f"{board_str}\n\n**{game_over_message}**"
        else:
            embed.description = f"**Current Player:** {self.game.current_player.mention}\n{board_str}"
        
        p1_emoji = getattr(config, 'CONNECT4_PLAYER1_EMOJI', '🔴')
        p2_emoji = getattr(config, 'CONNECT4_PLAYER2_EMOJI', '🔵')
        embed.add_field(name=f"Player 1 ({p1_emoji})", value=self.game.players[0].mention, inline=True)
        embed.add_field(name=f"Player 2 ({p2_emoji})", value=self.game.players[1].mention, inline=True)
        embed.set_footer(text=f"Bet per player: {self.game.bet} {getattr(config, 'ECONOMY_CURRENCY_NAME', 'coins')}")
        return embed

    async def _end_game(self, interaction: discord.Interaction, winner: Optional[discord.Member] = None, is_draw: bool = False):
        game_over_message = ""
        currency_name = getattr(config, 'ECONOMY_CURRENCY_NAME', 'coins')
        if winner:
            winnings = self.game.bet * 2 
            await self.economy_manager.update_balance(winner.id, winnings)
            game_over_message = f"🎉 {winner.mention} wins and gets {winnings} {currency_name}!"
            logger.info(f"Connect 4 game ended. Winner: {winner.name}. Bet: {self.game.bet}")
        elif is_draw:
            await self.economy_manager.update_balance(self.game.players[0].id, self.game.bet)
            await self.economy_manager.update_balance(self.game.players[1].id, self.game.bet)
            game_over_message = f"🤝 It's a draw! Bets of {self.game.bet} {currency_name} returned."
            logger.info(f"Connect 4 game ended in a draw. Bet: {self.game.bet}")

        for item in self.children: 
            if isinstance(item, Button): item.disabled = True
        
        embed = self._build_embed(game_over_message)
        await self.initial_message.edit(embed=embed, view=self) 
        self.stop() 

    async def on_timeout(self):
        logger.info(f"Connect 4 game timed out. Players: {[p.name for p in self.game.players]}")
        game_over_message = "Game timed out! Bets are returned."
        if not self.game.winner and not self.game.is_draw: 
            await self.economy_manager.update_balance(self.game.players[0].id, self.game.bet)
            await self.economy_manager.update_balance(self.game.players[1].id, self.game.bet)
        
        for item in self.children:
            if isinstance(item, Button): item.disabled = True
        embed = self._build_embed(game_over_message)
        try: await self.initial_message.edit(embed=embed, view=self)
        except discord.HTTPException as e: logger.error(f"Failed to edit Connect 4 message on timeout: {e}")
        self.stop()

# --- Blackjack Game ---
class BlackjackGame:
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
        suits_config = getattr(config, 'BLACKJACK_CARD_SUITS', ["♠️", "♣️", "♥️", "♦️"]) # Ensure it's a list or tuple
        if isinstance(suits_config, set): suits_config = list(suits_config) # Convert set to list if needed
        return [f"{r}{s}" for s in suits_config for r in ranks]

    def _deal_initial_hands(self):
        for _ in range(2):
            if self.deck: self.player_hand.append(self.deck.pop())
            if self.deck: self.dealer_hand.append(self.deck.pop())

    def _calculate_hand_value(self, hand: List[str]) -> int:
        value, aces = 0, 0
        # Determine suit length from config to correctly parse rank
        suits_config = getattr(config, 'BLACKJACK_CARD_SUITS', ["♠️", "♣️", "♥️", "♦️"])
        suit_char_length = len(suits_config[0]) if suits_config else 1 # Length of the first suit emoji

        for card in hand:
            rank = card[:-suit_char_length] # Remove suit part
            if rank.isdigit(): value += int(rank)
            elif rank in ["J", "Q", "K"]: value += 10
            elif rank == "A": aces += 1; value += 11
        while value > 21 and aces > 0: value -= 10; aces -= 1
        return value

    def player_value(self) -> int: return self._calculate_hand_value(self.player_hand)
    def dealer_value(self) -> int: return self._calculate_hand_value(self.dealer_hand)

    def hit(self) -> bool: 
        if not self.deck: return True 
        self.player_hand.append(self.deck.pop())
        if self.player_value() > 21:
            self.game_over = True
            self.result_message = "Bust! You lose."
            return True
        return False

    def stand(self):
        self.game_over = True
        while self.dealer_value() < 17:
            if not self.deck: break 
            self.dealer_hand.append(self.deck.pop())
        player_val, dealer_val = self.player_value(), self.dealer_value()
        if dealer_val > 21: self.result_message = "Dealer busts! You win!"
        elif player_val > dealer_val: self.result_message = "You win!"
        elif player_val < dealer_val: self.result_message = "Dealer wins!"
        else: self.result_message = "Push! It's a tie."

class BlackjackView(View):
    def __init__(self, game: BlackjackGame, economy_manager: EconomyManager, initial_message: discord.Message):
        super().__init__(timeout=getattr(config, 'BLACKJACK_GAME_TIMEOUT_SECONDS', 120.0))
        self.game = game
        self.economy_manager = economy_manager
        self.initial_message = initial_message
        self._update_button_states()

    def _update_button_states(self):
        for item in self.children:
            if isinstance(item, Button): item.disabled = self.game.game_over
    
    def _build_embed(self) -> discord.Embed:
        embed_color = getattr(config, 'BLACKJACK_EMBED_COLOR', discord.Color.green())
        embed = discord.Embed(title=f"Blackjack - Bet: {self.game.bet} {getattr(config, 'ECONOMY_CURRENCY_NAME', 'coins')}", color=embed_color)
        embed.add_field(name=f"{self.game.player.display_name}'s Hand ({self.game.player_value()})", value=" ".join(self.game.player_hand) or "No cards", inline=False)
        dealer_hand_display = " ".join(self.game.dealer_hand) if self.game.game_over else f"{self.game.dealer_hand[0] if self.game.dealer_hand else ''} {getattr(config, 'BLACKJACK_HIDDEN_CARD_EMOJI', '❓')}"
        embed.add_field(name=f"Dealer's Hand ({self.game.dealer_value() if self.game.game_over else '?'})", value=dealer_hand_display or "No cards", inline=False)
        if self.game.game_over: embed.description = f"**Result: {self.game.result_message}**"
        return embed

    async def _end_game(self, interaction: Optional[discord.Interaction]):
        self._update_button_states() 
        payout = 0
        player_val, dealer_val = self.game.player_value(), self.game.dealer_value()
        currency_name = getattr(config, 'ECONOMY_CURRENCY_NAME', 'coins')

        if "You win!" in self.game.result_message: 
            if player_val == 21 and len(self.game.player_hand) == 2 and not (dealer_val == 21 and len(self.game.dealer_hand) == 2):
                payout = int(self.game.bet * getattr(config, 'BLACKJACK_NATURAL_PAYOUT_MULTIPLIER', 2.5))
                self.game.result_message += f" (Natural Blackjack! Pays {payout} {currency_name})"
            else: payout = self.game.bet * getattr(config, 'BLACKJACK_WIN_PAYOUT_MULTIPLIER', 2)
        elif "Push!" in self.game.result_message: payout = self.game.bet
        
        if payout > 0: await self.economy_manager.update_balance(self.game.player.id, payout)
        elif "lose" in self.game.result_message.lower() and payout == 0: # Explicit loss, bet is lost (no update needed if not deducted upfront)
            logger.info(f"Blackjack loss for {self.game.player.name}, bet of {self.game.bet} {currency_name} lost.")


        embed = self._build_embed()
        edit_target = interaction.message if interaction else self.initial_message
        if edit_target:
            try: await edit_target.edit(embed=embed, view=self)
            except discord.HTTPException as e: logger.error(f"Failed to edit Blackjack message on end_game: {e}")
        self.stop()

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.success, custom_id="bj_hit")
    async def hit_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.game.player: await interaction.response.send_message("This isn't your game!", ephemeral=True); return
        await interaction.response.defer()
        if self.game.hit(): await self._end_game(interaction)
        else: await interaction.edit_original_response(embed=self._build_embed(), view=self)

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.danger, custom_id="bj_stand")
    async def stand_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.game.player: await interaction.response.send_message("This isn't your game!", ephemeral=True); return
        await interaction.response.defer()
        self.game.stand(); await self._end_game(interaction)

    async def on_timeout(self):
        logger.info(f"Blackjack game for {self.game.player.name} timed out.")
        if not self.game.game_over:
            self.game.game_over = True; self.game.result_message = f"Game timed out. You lose your bet of {self.game.bet} {getattr(config, 'ECONOMY_CURRENCY_NAME', 'coins')}."
            # Bet is lost on timeout
            await self._end_game(None) 
        self.stop()

# --- Roulette Game ---
class RouletteGame:
    def __init__(self, player: discord.Member, bet_amount: int):
        self.player = player; self.bet_amount = bet_amount; self.bet_type: Optional[str] = None
        self.winning_number: int = random.randint(0, 36); self.payout: int = 0; self.game_over: bool = False

    def place_bet(self, bet_type: str): self.bet_type = bet_type

    def calculate_payout(self) -> int:
        self.game_over = True; self.payout = 0 # Reset payout
        if self.bet_type is None: return 0
        if self.bet_type.startswith("number_"):
            try: chosen_number = int(self.bet_type.split("_")[1])
            except (IndexError, ValueError): return 0
            if chosen_number == self.winning_number: self.payout = self.bet_amount * getattr(config, 'ROULETTE_PAYOUT_NUMBER', 35)
        elif self.bet_type == "red" and self.winning_number in ROULETTE_RED_NUMBERS: self.payout = self.bet_amount * getattr(config, 'ROULETTE_PAYOUT_COLOR', 2)
        elif self.bet_type == "black" and self.winning_number in ROULETTE_BLACK_NUMBERS: self.payout = self.bet_amount * getattr(config, 'ROULETTE_PAYOUT_COLOR', 2)
        elif self.bet_type == "green" and self.winning_number == ROULETTE_GREEN_NUMBER: self.payout = self.bet_amount * getattr(config, 'ROULETTE_PAYOUT_GREEN', 35)
        return self.payout

    def get_winning_color(self) -> str:
        if self.winning_number == ROULETTE_GREEN_NUMBER: return "Green"
        if self.winning_number in ROULETTE_RED_NUMBERS: return "Red"
        if self.winning_number in ROULETTE_BLACK_NUMBERS: return "Black"
        return "Unknown" # Should not happen for 0-36

# --- FIX: RouletteNumberModal class definition ---
class RouletteNumberModal(Modal, title="Bet on a Number (0-36)"):
    # Define class attributes for TextInputs
    bet_number_input = TextInput(
        label="Number (0-36)",
        placeholder="Enter a number between 0 and 36",
        min_length=1,
        max_length=2,
        required=True
    )

    def __init__(self, game: RouletteGame, parent_view: 'RouletteView'):
        super().__init__(timeout=getattr(config, 'ROULETTE_MODAL_TIMEOUT_SECONDS', 120.0))
        self.game = game
        self.parent_view = parent_view
        # self.add_item(self.bet_number_input) # Items are added automatically if defined as class attributes

    async def on_submit(self, interaction: discord.Interaction):
        try:
            number = int(self.bet_number_input.value)
            if not (0 <= number <= 36):
                await interaction.response.send_message("Invalid number. Must be between 0 and 36.", ephemeral=True)
                return
            await self.parent_view.process_bet(interaction, f"number_{number}")
        except ValueError:
            await interaction.response.send_message("Invalid input. Please enter a whole number.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error in RouletteNumberModal on_submit: {e}", exc_info=True)
            await interaction.response.send_message("An error occurred processing your bet.", ephemeral=True)

class RouletteView(View):
    def __init__(self, game: RouletteGame, economy_manager: EconomyManager, initial_message: discord.Message):
        super().__init__(timeout=getattr(config, 'ROULETTE_GAME_TIMEOUT_SECONDS', 180.0))
        self.game = game; self.economy_manager = economy_manager; self.initial_message = initial_message
        self._add_bet_buttons()

    def _add_bet_buttons(self):
        self.add_item(Button(label="Red", style=discord.ButtonStyle.red, custom_id="roulette_red"))
        self.add_item(Button(label="Black", style=discord.ButtonStyle.secondary, custom_id="roulette_black"))
        self.add_item(Button(label=f"Green ({ROULETTE_GREEN_NUMBER})", style=discord.ButtonStyle.success, custom_id="roulette_green"))
        self.add_item(Button(label="Specific Number", style=discord.ButtonStyle.primary, custom_id="roulette_number_select"))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.game.player: await interaction.response.send_message("This is not your game!", ephemeral=True); return False
        if self.game.game_over: await interaction.response.send_message("The game is already over!", ephemeral=True); return False
        return True

    # This method will be dynamically called by button callbacks if custom_ids match
    async def _dispatch_button_click(self, interaction: discord.Interaction, custom_id: str):
        if not await self.interaction_check(interaction): return

        if custom_id == "roulette_number_select":
            modal = RouletteNumberModal(self.game, self)
            await interaction.response.send_modal(modal)
        elif custom_id in ["roulette_red", "roulette_black", "roulette_green"]:
            bet_type = custom_id.split("_")[1]
            await self.process_bet(interaction, bet_type)
        else: # Should not happen if buttons are defined correctly
            logger.warning(f"RouletteView received unknown custom_id: {custom_id}")
            await interaction.response.send_message("Unknown action.", ephemeral=True)
            
    # Need to override on_interaction or assign callbacks manually if not using @discord.ui.button
    # For simplicity with dynamic buttons, let's use a more direct callback assignment or override on_interaction.
    # The previous refactor used on_interaction. Let's stick to that or ensure callbacks are set.
    # For this structure, setting callbacks in _add_bet_buttons is cleaner.

    # Re-defining button callbacks to use _dispatch_button_click
    async def button_callback_router(self, interaction: discord.Interaction):
        custom_id = interaction.data["custom_id"]
        await self._dispatch_button_click(interaction, custom_id)
    
    # Modify _add_bet_buttons to assign the router
    def _add_bet_buttons(self): # Overwrite previous
        self.clear_items() # Clear any existing items if called multiple times
        buttons_data = [
            {"label": "Red", "style": discord.ButtonStyle.red, "custom_id": "roulette_red"},
            {"label": "Black", "style": discord.ButtonStyle.secondary, "custom_id": "roulette_black"},
            {"label": f"Green ({ROULETTE_GREEN_NUMBER})", "style": discord.ButtonStyle.success, "custom_id": "roulette_green"},
            {"label": "Specific Number", "style": discord.ButtonStyle.primary, "custom_id": "roulette_number_select"}
        ]
        for data in buttons_data:
            button = Button(label=data["label"], style=data["style"], custom_id=data["custom_id"])
            button.callback = self.button_callback_router # Assign the single router callback
            self.add_item(button)


    async def process_bet(self, interaction: discord.Interaction, bet_type: str):
        if not interaction.response.is_done(): await interaction.response.defer()
        self.game.place_bet(bet_type)
        for item in self.children: 
            if isinstance(item, Button): item.disabled = True

        spin_embed_color = getattr(config, 'ROULETTE_SPIN_EMBED_COLOR', discord.Color.gold())
        spin_message = getattr(config, 'ROULETTE_SPINNING_MESSAGE', "Spinning the wheel...")
        spinning_embed = discord.Embed(title="Roulette", description=spin_message, color=spin_embed_color)
        
        roulette_gif_path = getattr(config, 'ROULETTE_GIF_PATH', None)
        gif_file = None
        attachments_to_send = []
        if roulette_gif_path and os.path.exists(roulette_gif_path):
            try:
                gif_file = discord.File(roulette_gif_path, filename=os.path.basename(roulette_gif_path))
                spinning_embed.set_image(url=f"attachment://{os.path.basename(roulette_gif_path)}")
                attachments_to_send.append(gif_file)
            except Exception as e: logger.error(f"Failed to load roulette GIF '{roulette_gif_path}': {e}")
        
        # Use followup if already deferred (e.g. from button click)
        # Use edit_original_response if called from modal submission (interaction.response is done by modal)
        edit_target = interaction.message if interaction.message else self.initial_message
        if interaction.response.is_done() and not isinstance(interaction.response, discord.interactions.InteractionResponded): # Modal submission path
             await interaction.edit_original_response(embed=spinning_embed, view=self, attachments=attachments_to_send)
        else: # Button click path (already deferred)
            await interaction.followup.edit_message(message_id=edit_target.id, embed=spinning_embed, view=self, attachments=attachments_to_send)


        await asyncio.sleep(getattr(config, 'ROULETTE_SPIN_DURATION_SECONDS', 5))

        self.game.calculate_payout()
        payout, winning_number, winning_color = self.game.payout, self.game.winning_number, self.game.get_winning_color()
        currency_name = getattr(config, 'ECONOMY_CURRENCY_NAME', 'coins')
        
        result_message = f"The wheel stops on **{winning_number} ({winning_color})**!\n"
        if payout > 0:
            final_payout_amount = payout # Payout includes original bet for color/green, is net for number
            if not bet_type.startswith("number_"): # For color/green, payout is total return
                await self.economy_manager.update_balance(self.game.player.id, final_payout_amount)
            else: # For number, payout is winnings + original bet returned
                 await self.economy_manager.update_balance(self.game.player.id, final_payout_amount + self.game.bet_amount)
            result_message += getattr(config, 'ROULETTE_WIN_MESSAGE', "Congratulations! You win **{payout_amount}** {currency}!").format(payout_amount=final_payout_amount, currency=currency_name)
            logger.info(f"Roulette win for {self.game.player.name}. Bet: {self.game.bet_amount} on {bet_type}. Won: {final_payout_amount}")
        else:
            await self.economy_manager.update_balance(self.game.player.id, -self.game.bet_amount) # Deduct loss
            result_message += getattr(config, 'ROULETTE_LOSS_MESSAGE', "Sorry, you didn't win this time. You lost {bet_amount} {currency}.")
            result_message = result_message.format(bet_amount=self.game.bet_amount, currency=currency_name)
            logger.info(f"Roulette loss for {self.game.player.name}. Bet: {self.game.bet_amount} on {bet_type}.")

        result_embed_color = getattr(config, 'ROULETTE_RESULT_EMBED_COLOR', None)
        if result_embed_color is None: result_embed_color = discord.Color.dark_green() if payout > 0 else discord.Color.dark_red()
        result_embed = discord.Embed(title="Roulette Result", description=result_message, color=result_embed_color)
        result_embed.set_footer(text=f"You bet {self.game.bet_amount} {currency_name} on {bet_type.replace('_', ' ')}.")
        
        if interaction.response.is_done() and not isinstance(interaction.response, discord.interactions.InteractionResponded):
            await interaction.edit_original_response(embed=result_embed, view=self, attachments=[])
        else:
            await interaction.followup.edit_message(message_id=edit_target.id, embed=result_embed, view=self, attachments=[])
        self.stop()

    async def on_timeout(self):
        logger.info(f"Roulette game for {self.game.player.name} timed out.")
        if not self.game.game_over:
            for item in self.children: 
                if isinstance(item, Button): item.disabled = True
            timeout_message = getattr(config, 'ROULETTE_TIMEOUT_MESSAGE', "Roulette game timed out. Your bet was not processed.")
            embed = discord.Embed(title="Roulette Timeout", description=timeout_message, color=discord.Color.orange())
            edit_target = self.initial_message
            if edit_target:
                try: await edit_target.edit(embed=embed, view=self, attachments=[])
                except discord.HTTPException as e: logger.error(f"Failed to edit Roulette message on timeout: {e}")
        self.stop()

# --- Games Cog ---
class GamesCog(commands.Cog, name="Games"):
    """Cog for hosting various games like Connect 4, Blackjack, and Roulette."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.economy_file_path = getattr(config, 'ECONOMY_FILE_PATH', 'data/economy.json')
        economy_dir = os.path.dirname(self.economy_file_path)
        if economy_dir and not os.path.exists(economy_dir):
            try: os.makedirs(economy_dir, exist_ok=True); logger.info(f"Created directory for economy file: {economy_dir}")
            except OSError as e: logger.error(f"Could not create directory {economy_dir}: {e}")

        self.economy_lock = asyncio.Lock()
        self.economy_manager = EconomyManager(
            file_path=self.economy_file_path,
            default_balance=getattr(config, 'ECONOMY_DEFAULT_BALANCE', 100),
            lock=self.economy_lock
        )
        self.bot.economy_manager = self.economy_manager # Attach to bot instance
        logger.info(f"Games Cog loaded. Economy manager initialized and attached to bot. File: {self.economy_file_path}")

    async def cog_check(self, ctx: commands.Context) -> bool:
        if ctx.guild is None and not getattr(config, 'ALLOW_GAMES_IN_DMS', False):
            await ctx.send(getattr(config, 'MUSIC_MSG_GUILD_ONLY', "Game commands are typically used in servers."))
            return False
        return True

    async def common_bet_validation(self, ctx: commands.Context, bet: int, min_bet: int, user_id: Optional[int] = None) -> bool:
        target_user_id = user_id if user_id is not None else ctx.author.id
        if bet < min_bet:
            await ctx.send(getattr(config, 'GAMES_MIN_BET_MESSAGE', "Minimum bet is {min_bet} coins.").format(min_bet=min_bet))
            return False
        balance = await self.economy_manager.get_balance(target_user_id)
        if balance < bet:
            if user_id and user_id != ctx.author.id:
                try: opponent = await self.bot.fetch_user(user_id)
                except discord.NotFound: opponent_name = f"User ID {user_id}"
                else: opponent_name = opponent.display_name
                msg = getattr(config, 'GAMES_OPPONENT_INSUFFICIENT_FUNDS_MESSAGE', "{opponent_name} doesn't have enough coins (Balance: {opponent_balance}).")
                await ctx.send(msg.format(opponent_name=opponent_name, opponent_balance=balance))
            else:
                msg = getattr(config, 'GAMES_INSUFFICIENT_FUNDS_MESSAGE', "You don't have enough coins! Your balance: {balance}")
                await ctx.send(msg.format(balance=balance))
            return False
        return True

    @commands.command(name="balance", aliases=["bal", "money"], help="Check your current coin balance.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def balance(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        target_user = member or ctx.author
        balance_val = await self.economy_manager.get_balance(target_user.id)
        currency_name = getattr(config, 'ECONOMY_CURRENCY_NAME', 'coins')
        bal_msg = getattr(config, 'GAMES_BALANCE_MESSAGE', "{user_mention}'s balance: **{balance}** {currency}.")
        await ctx.send(bal_msg.format(user_mention=target_user.mention, balance=balance_val, currency=currency_name))
        logger.info(f"Balance check for {target_user.name} by {ctx.author.name}: {balance_val} {currency_name}.")

    @commands.command(name="connect4", aliases=["c4"], help="Play Connect 4 with another player for a bet.")
    @commands.guild_only()
    @commands.cooldown(1, getattr(config, 'CONNECT4_COOLDOWN_SECONDS', 30), commands.BucketType.channel)
    async def connect4(self, ctx: commands.Context, opponent: discord.Member, bet: int):
        min_bet = getattr(config, 'CONNECT4_MIN_BET', 1)
        if ctx.author == opponent: await ctx.send(getattr(config, 'CONNECT4_CANNOT_PLAY_SELF_MESSAGE', "You can't play against yourself!")); return
        if opponent.bot: await ctx.send(getattr(config, 'CONNECT4_CANNOT_PLAY_BOT_MESSAGE', "You can't play against a bot!")); return
        if not await self.common_bet_validation(ctx, bet, min_bet, ctx.author.id): return
        if not await self.common_bet_validation(ctx, bet, min_bet, opponent.id): return
        await self.economy_manager.update_balance(ctx.author.id, -bet)
        await self.economy_manager.update_balance(opponent.id, -bet)
        logger.info(f"Connect 4 game: {ctx.author.name} vs {opponent.name}, bet: {bet} each.")
        game = Connect4Game([ctx.author, opponent], bet)
        msg = await ctx.send(embed=discord.Embed(title="Connect 4", description="Setting up...", color=getattr(config, 'CONNECT4_EMBED_COLOR', discord.Color.purple())))
        view = Connect4View(game, self.economy_manager, msg)
        await msg.edit(embed=view._build_embed(), view=view)

    @commands.command(name="blackjack", aliases=["bj"], help="Play Blackjack against the dealer for a bet.")
    @commands.cooldown(1, getattr(config, 'BLACKJACK_COOLDOWN_SECONDS', 10), commands.BucketType.user)
    async def blackjack(self, ctx: commands.Context, bet: int):
        min_bet = getattr(config, 'BLACKJACK_MIN_BET', 1)
        if not await self.common_bet_validation(ctx, bet, min_bet): return
        logger.info(f"Blackjack game: {ctx.author.name}, bet: {bet}.")
        game = BlackjackGame(ctx.author, bet)
        msg = await ctx.send(embed=discord.Embed(title="Blackjack", description="Dealing...", color=getattr(config, 'BLACKJACK_EMBED_COLOR', discord.Color.green())))
        view = BlackjackView(game, self.economy_manager, msg)
        await msg.edit(embed=view._build_embed(), view=view)

    @commands.command(name="roulette", help="Play Roulette with various betting options.")
    @commands.cooldown(1, getattr(config, 'ROULETTE_COOLDOWN_SECONDS', 15), commands.BucketType.user)
    async def roulette(self, ctx: commands.Context, bet: int):
        min_bet = getattr(config, 'ROULETTE_MIN_BET', 1)
        if not await self.common_bet_validation(ctx, bet, min_bet): return
        logger.info(f"Roulette game: {ctx.author.name}, bet: {bet}.")
        game = RouletteGame(ctx.author, bet)
        embed = discord.Embed(title=f"Roulette - Bet: {bet}", description=getattr(config, 'ROULETTE_PLACE_BET_MESSAGE', "Place your bet!"), color=getattr(config, 'ROULETTE_INITIAL_EMBED_COLOR', discord.Color.gold()))
        msg = await ctx.send(embed=embed)
        view = RouletteView(game, self.economy_manager, msg)
        await msg.edit(view=view) # Add view to the existing message

    async def game_command_error_handler(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.MissingRequiredArgument): await ctx.send(f"Missing argument: `{error.param.name}`. Try `{ctx.prefix}help {ctx.command.qualified_name}`.")
        elif isinstance(error, commands.BadArgument): await ctx.send(f"Invalid argument for `{error.param.name if hasattr(error, 'param') else 'argument'}`.")
        elif isinstance(error, commands.CommandOnCooldown): await ctx.send(f"Command on cooldown. Try again in {error.retry_after:.2f}s.")
        elif isinstance(error, commands.NoPrivateMessage): await ctx.send("This game can only be played in a server.")
        elif isinstance(error, commands.CommandInvokeError) and isinstance(error.original, KeyError) and 'currency' in str(error.original):
            logger.error(f"KeyError for 'currency' in {ctx.command.qualified_name}: {error.original}", exc_info=True)
            await ctx.send("Issue displaying balance message (currency name might be missing in config).")
        else:
            logger.error(f"Unhandled error in {ctx.command.qualified_name}: {error}", exc_info=True)
            await ctx.send("An unexpected error occurred with this game command.")

    @connect4.error
    async def connect4_error(self, ctx: commands.Context, error: commands.CommandError): await self.game_command_error_handler(ctx, error)
    @blackjack.error
    async def blackjack_error(self, ctx: commands.Context, error: commands.CommandError): await self.game_command_error_handler(ctx, error)
    @roulette.error
    async def roulette_error(self, ctx: commands.Context, error: commands.CommandError): await self.game_command_error_handler(ctx, error)
    @balance.error 
    async def balance_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.BadArgument) and hasattr(error, 'param') and error.param.name == 'member':
            await ctx.send("Could not find that member.")
        else: await self.game_command_error_handler(ctx,error)

async def setup(bot: commands.Bot):
    """Sets up the GamesCog."""
    economy_dir = os.path.dirname(getattr(config, 'ECONOMY_FILE_PATH', 'data/economy.json'))
    if economy_dir and not os.path.exists(economy_dir): 
        try: os.makedirs(economy_dir, exist_ok=True); logger.info(f"Created directory for economy file: {economy_dir}")
        except OSError as e: logger.error(f"Could not create directory {economy_dir}: {e}")
    await bot.add_cog(GamesCog(bot))
    logger.info("GamesCog has been setup and added to the bot.")

