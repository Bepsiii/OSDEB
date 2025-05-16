import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput
import random
import json
import os
import asyncio

# --- Constants ---
ECONOMY_FILE = "economy.json"
ROULETTE_GIF_PATH = "gif/roulette.gif"  # Relative path to the GIF
RED_NUMBERS = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
BLACK_NUMBERS = [2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35]

# --- Utility Functions ---
def load_economy():
    try:
        with open(ECONOMY_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        print("Error decoding economy.json.  Returning empty economy.")
        return {}


def save_economy(economy):
    try:
        with open(ECONOMY_FILE, 'w') as f:
            json.dump(economy, f, indent=4)
    except Exception as e:
        print(f"Error saving economy: {e}")

def get_balance(user_id):
    economy = load_economy()
    return economy.get(str(user_id), 100)

def update_balance(user_id, amount):
    economy = load_economy()
    user_id = str(user_id)
    economy[user_id] = economy.get(user_id, 100) + amount
    save_economy(economy)

# --- Connect 4 Game ---
class Connect4Game:
    def __init__(self, players, bet):
        self.players = players
        self.board = [[0] * 7 for _ in range(6)]
        self.current_player = 0
        self.bet = bet  # Each player's bet

    def make_move(self, col):
        for row in reversed(range(6)):
            if self.board[row][col] == 0:
                self.board[row][col] = self.current_player + 1
                return row, col
        return None

    def check_win(self, row, col):
        player = self.current_player + 1
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        for dr, dc in directions:
            count = 1
            for i in (1, -1):
                r, c = row + dr * i, col + dc * i
                while 0 <= r < 6 and 0 <= c < 7 and self.board[r][c] == player:
                    count += 1
                    r += dr * i
                    c += dc * i
            if count >= 4:
                return True
        return False

class Connect4View(View):
    def __init__(self, game, embed):
        super().__init__(timeout=60)
        self.game = game
        self.embed = embed
        # Create one button per column.
        for i in range(7):
            self.add_item(self.create_button(i))

    def create_button(self, col: int) -> Button:
        button = Button(label=str(col + 1), style=discord.ButtonStyle.blurple, custom_id=f"col_{col}")
        async def callback(interaction: discord.Interaction):
            await self.on_click(interaction, col)
        button.callback = callback
        return button

    async def on_click(self, interaction: discord.Interaction, col):
        await interaction.response.defer()  # Acknowledge immediately

        if interaction.user != self.game.players[self.game.current_player]:
            await interaction.followup.send("Not your turn!", ephemeral=True)
            return

        move = self.game.make_move(col)
        if not move:
            await interaction.followup.send("Column full!", ephemeral=True)
            return

        board_str = "\n".join([
            "".join(["🔴" if cell == 1 else "🔵" if cell == 2 else "⚪" for cell in row])
            for row in self.game.board
        ])
        self.embed.description = f"**Current Player:** {self.game.players[self.game.current_player].mention}\n{board_str}"


        if self.game.check_win(*move):
            asyncio.create_task(self.end_game(interaction, winner=True)) # Run in background
        elif all(cell != 0 for row in self.game.board for cell in row):
             asyncio.create_task(self.end_game(interaction, draw=True)) # Run in background
        else:
            self.game.current_player = 1 - self.game.current_player
            await interaction.followup.edit_message(message_id=interaction.message.id, embed=self.embed)


    async def end_game(self, interaction: discord.Interaction, winner=False, draw=False):
        if winner:
            winner_player = self.game.players[self.game.current_player]
            self.embed.description += f"\n🎉 Winner: {winner_player.mention}!"
            # Winner receives both bets (i.e. 2× bet), as bets were already deducted.
            update_balance(winner_player.id, self.game.bet * 2)
        elif draw:
            self.embed.description += "\n🤝 It's a draw! Bets have been refunded."
            for player in self.game.players:
                update_balance(player.id, self.game.bet)
        await asyncio.sleep(2) # Simulate some work

        await interaction.followup.edit_message(message_id=interaction.message.id, embed=self.embed, view=None)
        self.stop()


# --- Blackjack Game ---
class BlackjackGame:
    def __init__(self, player, bet):
        self.player = player
        self.bet = bet
        self.deck = [f"{r}{s}" for s in ["♠", "♣", "♥", "♦"]
                     for r in ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]]
        random.shuffle(self.deck)
        self.player_hand = []
        self.dealer_hand = []
        self.game_over = False
        self.deal_initial_hands()

    def deal_initial_hands(self):
        self.player_hand.append(self.deck.pop())
        self.player_hand.append(self.deck.pop())
        self.dealer_hand.append(self.deck.pop())
        self.dealer_hand.append(self.deck.pop())

    def calculate_hand(self, hand):
        value, aces = 0, 0
        for card in hand:
            rank = card[:-1]
            if rank in ["J", "Q", "K"]:
                value += 10
            elif rank == "A":
                value, aces = value + 11, aces + 1
            else:
                value += int(rank)
        while value > 21 and aces:
            value, aces = value - 10, aces - 1
        return value

class BlackjackView(View):
    def __init__(self, game):
        super().__init__(timeout=60)
        self.game = game
        self.message = None

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.green)
    async def hit(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer() #Acknowledge the interaction

        if interaction.user != self.game.player:
            await interaction.followup.send("Not your game!", ephemeral=True) #Use followup here as we already deferred
            return

        self.game.player_hand.append(self.game.deck.pop())
        if self.game.calculate_hand(self.game.player_hand) > 21:
            asyncio.create_task(self.end_game(interaction, "Bust! You lose.")) #Defer ending of game.

        else:
            await interaction.followup.edit_message(message_id=interaction.message.id, embed=self.update_embed()) #Edit original interaction

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.red)
    async def stand(self, interaction: discord.Interaction, button: Button):

        await interaction.response.defer()

        if interaction.user != self.game.player:
            await interaction.followup.send("Not your game!", ephemeral=True)
            return

        while self.game.calculate_hand(self.game.dealer_hand) < 17:
            self.game.dealer_hand.append(self.game.deck.pop())

        asyncio.create_task(self.end_game(interaction))  #Run end_game in the background

    def update_embed(self):
        embed = discord.Embed(title="Blackjack", color=discord.Color.blue())
        embed.add_field(name="Your Hand", value=" ".join(self.game.player_hand), inline=False)
        if not self.game.game_over:
            embed.add_field(name="Dealer's Hand", value=f"{self.game.dealer_hand[0]} ?", inline=False)
        else:
            embed.add_field(name="Dealer's Hand", value=" ".join(self.game.dealer_hand), inline=False)
        return embed

    async def end_game(self, interaction: discord.Interaction, result=None):

        self.game.game_over = True
        player_val = self.game.calculate_hand(self.game.player_hand)
        dealer_val = self.game.calculate_hand(self.game.dealer_hand)

        if not result:
            if dealer_val > 21 or player_val > dealer_val:
                result = "You win!"
                # A natural blackjack (2 cards) pays 2.5×; otherwise, win pays 2×.
                if player_val == 21 and len(self.game.player_hand) == 2:
                    update_balance(self.game.player.id, int(self.game.bet * 2.5))
                else:
                    update_balance(self.game.player.id, self.game.bet * 2)
            elif player_val == dealer_val:
                result = "Push! Your bet has been returned."
                update_balance(self.game.player.id, self.game.bet)
            else:
                result = "Dealer wins! You lose your bet."
                update_balance(self.game.player.id, -self.game.bet)
        else:
            update_balance(self.game.player.id, -self.game.bet)  # Player busted

        embed = self.update_embed()
        embed.description = f"**Result:** {result}"
        await asyncio.sleep(2) #Simulate work
        await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=None)
        self.stop()

# --- Roulette Game ---
class RouletteGame:
    def __init__(self, player, bet):
        self.player = player
        self.bet = bet
        self.bet_type = None  # "red", "black", or "number"
        self.bet_number = None
        self.winning_number = random.randint(0, 36)
        self.payout = 0
        self.game_over = False

    def calculate_payout(self):
        if self.bet_type == "number":
            if self.bet_number == self.winning_number:
                self.payout = self.bet * 35  # 35 to 1 payout
        elif self.bet_type == "red":
            self.payout = self.bet * 2 if self.winning_number in RED_NUMBERS else 0
        elif self.bet_type == "black":
            self.payout = self.bet * 2 if self.winning_number in BLACK_NUMBERS else 0
        else:
            self.payout = 0

class RouletteView(View):
    def __init__(self, game):
        super().__init__(timeout=60)
        self.game = game

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.game.player:
            await interaction.response.send_message("This is not your game!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Red", style=discord.ButtonStyle.red, custom_id="roulette_red")
    async def red_button(self, interaction: discord.Interaction, button: Button):
        await self.handle_bet(interaction, "red")

    @discord.ui.button(label="Black", style=discord.ButtonStyle.grey, custom_id="roulette_black")
    async def black_button(self, interaction: discord.Interaction, button: Button):
        await self.handle_bet(interaction, "black")

    @discord.ui.button(label="Number", style=discord.ButtonStyle.blurple, custom_id="roulette_number")
    async def number_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(RouletteNumberModal(self.game, self))


    async def handle_bet(self, interaction: discord.Interaction, bet_type: str, bet_number: int = None):
        # Do NOT defer() here, modal submission is the interaction.  It's already been responded to.
        self.game.bet_type = bet_type
        if bet_type == "number":
            self.game.bet_number = bet_number
        self.game.calculate_payout()

        spinning_embed = discord.Embed(
            title="Roulette",
            description="Spinning...",
            color=discord.Color.gold()
        )

        file = discord.File(ROULETTE_GIF_PATH)
        spinning_embed.set_image(url=f"attachment://{os.path.basename(ROULETTE_GIF_PATH)}")


        await interaction.message.edit(embed=spinning_embed, attachments=[file])


        await asyncio.sleep(5)

        result_message = f"The winning number is **{self.game.winning_number}**!\n"
        if self.game.payout > 0:
            result_message += f"Congratulations, you win **{self.game.payout}** coins!"
            update_balance(self.game.player.id, self.game.payout)
        else:
            result_message += "Sorry, you lose."
            update_balance(self.game.player.id, -self.game.bet)

        result_embed = discord.Embed(
            title="Roulette Result",
            description=result_message,
            color=discord.Color.green()
        )

        await interaction.message.edit(embed=result_embed, attachments=[])
        self.stop()


class RouletteNumberModal(Modal):
    def __init__(self, game: RouletteGame, parent_view: RouletteView):
        super().__init__(title="Place Your Number Bet")
        self.game = game
        self.parent_view = parent_view
        self.bet_number = TextInput(
            label="Bet Number",
            placeholder="Enter a number between 0 and 36",
            min_length=1,
            max_length=2
        )
        self.add_item(self.bet_number)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            number = int(self.bet_number.value)
        except ValueError:
            await interaction.response.send_message("Invalid number entered.", ephemeral=True)
            return
        if not 0 <= number <= 36:
            await interaction.response.send_message("Number must be between 0 and 36.", ephemeral=True)
            return
        await self.parent_view.handle_bet(interaction, "number", bet_number=number)

# --- Games Cog ---
class Games(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["c4"], description="Play Connect 4 with a bet")
    async def connect4(self, ctx, opponent: discord.Member, bet: int):
        if ctx.author == opponent:
            await ctx.send("You can't play against yourself!")
            return
        if bet < 1:
            await ctx.send("Minimum bet: 1 coin")
            return
        author_balance = get_balance(ctx.author.id)
        opponent_balance = get_balance(opponent.id)
        if author_balance < bet:
            await ctx.send(f"You don't have enough coins! Your balance: {author_balance}")
            return
        if opponent_balance < bet:
            await ctx.send(f"{opponent.display_name} doesn't have enough coins to bet!")
            return

        # Deduct bet from both players.
        update_balance(ctx.author.id, -bet)
        update_balance(opponent.id, -bet)

        game = Connect4Game([ctx.author, opponent], bet)
        embed = discord.Embed(title="Connect 4", description="Starting game...", color=discord.Color.purple())
        view = Connect4View(game, embed)
        await ctx.send(embed=embed, view=view)

    @commands.command(aliases=["bj"], description="Play Blackjack with a bet")
    async def blackjack(self, ctx, bet: int):
        if bet < 1:
            await ctx.send("Minimum bet: 1 coin")
            return
        if get_balance(ctx.author.id) < bet:
            await ctx.send(f"Not enough coins! Your balance: {get_balance(ctx.author.id)}")
            return

        game = BlackjackGame(ctx.author, bet)
        view = BlackjackView(game)
        await ctx.send(embed=view.update_embed(), view=view)

    @commands.command(description="Play Roulette with a bet")
    async def roulette(self, ctx, bet: int):
        if bet < 1:
            await ctx.send("Minimum bet: 1 coin")
            return
        if get_balance(ctx.author.id) < bet:
            await ctx.send(f"Not enough coins! Your balance: {get_balance(ctx.author.id)}")
            return

        game = RouletteGame(ctx.author, bet)
        view = RouletteView(game)
        embed = discord.Embed(title="Roulette", description="Place your bet by choosing an option below!", color=discord.Color.gold())
        await ctx.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(Games(bot))