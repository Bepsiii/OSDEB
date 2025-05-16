# store_cog.py
import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput
import random
import json
import os

# --- Constants ---
ECONOMY_FILE = "economy.json"
STORE_FILE = "store.json"

# --- Utility Functions (moved here to avoid circular dependencies) ---
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

def load_store():
    try:
        with open(STORE_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        print("Error decoding store.json.  Returning empty store.")
        return {}

def save_store(store):
    try:
        with open(STORE_FILE, 'w') as f:
            json.dump(store, f, indent=4)
    except Exception as e:
        print(f"Error saving store: {e}")

class NicknameModal(Modal):
    def __init__(self, store_cog, member):
        super().__init__(title="Change Nickname")
        self.store_cog = store_cog
        self.member = member
        self.new_nickname = TextInput(label="New Nickname", placeholder="Enter your new nickname", required=True)
        self.add_item(self.new_nickname)

    async def on_submit(self, interaction: discord.Interaction):
        new_nick = self.new_nickname.value
        try:
            await self.member.edit(nick=new_nick)
            await interaction.response.send_message(f"Nickname changed to {new_nick}!", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("I don't have permission to change nicknames.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

class AddItemModal(Modal):
    def __init__(self, store_cog):
        super().__init__(title="Add Item to Store")
        self.store_cog = store_cog
        self.item_name = TextInput(label="Item Name", placeholder="Enter the name")
        self.item_cost = TextInput(label="Item Cost", placeholder="Enter the cost")
        self.item_description = TextInput(label="Item Description", placeholder="Enter a brief description")
        self.item_type = TextInput(label="Item Type (role, color, badge, nickname)", placeholder="Enter the type of item")
        self.item_data = TextInput(label="Item Data (role_id, hex, url)", placeholder="Enter role_id, hex, or url") # More descriptive label

        for item in [self.item_name, self.item_cost, self.item_description, self.item_type, self.item_data]:
          self.add_item(item)


    async def on_submit(self, interaction: discord.Interaction):
        try:
            name = self.item_name.value
            cost = int(self.item_cost.value)
            description = self.item_description.value
            item_type = self.item_type.value.lower()
            item_data = self.item_data.value

            if item_type not in ("role", "color", "badge", "nickname"):
                await interaction.response.send_message("Invalid item type", ephemeral=True)
                return

            if cost < 0:
                await interaction.response.send_message("Cost must be non-negative", ephemeral=True)
                return

            item_details = {}  # Initialize item_details

            if item_type == "role":
                try:
                    role_id = int(item_data)
                except ValueError:
                    await interaction.response.send_message("Role ID must be an integer", ephemeral=True)
                    return
                item_details = {"type": item_type, "role_id": item_data}

            elif item_type == "color":
                try:
                    int(item_data, 16)  # Test if valid hex
                except ValueError:
                    await interaction.response.send_message("Hex must be valid", ephemeral=True)
                    return
                item_details = {"type": item_type, "color_hex": item_data}

            elif item_type == "badge":
                # You might want to validate the URL here
                item_details = {"type": item_type, "badge_url": item_data}

            elif item_type == "nickname":
                item_details = {"type": item_type}  # No specific data needed

            item_id = str(random.randint(1000, 9999))
            new_item = {
                "name": name,
                "cost": cost,
                "description": description,
                **item_details  # Merge item-specific data
            }

            self.store_cog.store[item_id] = new_item
            save_store(self.store_cog.store)

            await interaction.response.send_message(f"Item '{name}' added with ID: {item_id}", ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)


class StoreView(discord.ui.View):  # Define the View outside of the command
    def __init__(self, store_cog, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.store_cog = store_cog  # Store a reference to the cog
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()  # Clear existing buttons before re-adding

        for item_id, item in self.store_cog.store.items():
            button = discord.ui.Button(label=f"Buy {item['name']} ({item['cost']} coins)", custom_id=item_id)
            button.callback = self.create_callback(item_id)  # Create a unique callback for each button
            self.add_item(button)

    def create_callback(self, item_id):
        async def callback(interaction: discord.Interaction):
            item = self.store_cog.store.get(item_id)
            if not item:
                await interaction.response.send_message("Item not found.", ephemeral=True)
                return

            user_balance = get_balance(interaction.user.id)
            if user_balance < item['cost']:
                await interaction.response.send_message("Not enough coins.", ephemeral=True)
                return

            update_balance(interaction.user.id, -item['cost'])

            #Special Case, use modal.

            if item['type'] == "nickname":
                modal = NicknameModal(self.store_cog, interaction.user)
                await interaction.response.send_modal(modal)
                return #Don't apply item effect, the Modal submission will handle it.


            await self.store_cog.apply_item_effect(interaction, interaction.user, item) #Pass interaction for follow-up.
            await interaction.response.send_message(f"Purchased {item['name']}!", ephemeral=True)
        return callback



class Store(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.store = load_store()

    @commands.command(name="balance", description="Check your coin balance")
    async def balance(self, ctx, member: discord.Member = None):
        """Checks the user's or another member's coin balance."""
        member = member or ctx.author  # Use the author if no member is specified
        user_balance = get_balance(member.id)
        await ctx.send(f"{member.display_name}'s balance: {user_balance} coins")

    @commands.command(name="store", description="View the store") # Modified command name
    async def store(self, ctx):
        """Displays the store with buttons to buy items."""
        store_view = StoreView(self) # Pass self (the cog instance) to the view
        embed = discord.Embed(title="Store", description="Click a button to buy an item:", color=discord.Color.gold())
        if not self.store:
          embed.description = "The store is empty."
        await ctx.send(embed=embed, view=store_view)

    @commands.command(name="add_item", description="Add an item to the store (Admin Only)")
    @commands.has_permissions(administrator=True)
    async def add_item(self, ctx):
        """Adds a new item to the store (Admin only)."""
        modal = AddItemModal(self)
        await ctx.interaction.response.send_modal(modal)

    @commands.command(name="remove_item", description="Remove an item (Admin Only)")
    @commands.has_permissions(administrator=True)
    async def remove_item(self, ctx, item_id: str):
        """Removes an item from the store (Admin only)."""
        if item_id not in self.store:
            await ctx.send("Invalid item ID.")
            return

        del self.store[item_id]
        save_store(self.store)

        # Update the buttons after removing an item
        # Find the original message and edit the view
        for message in self.bot.cached_messages: #Iterate through cached messages to find the original message.
            if (message.author == self.bot.user) and (len(message.embeds) > 0 and message.embeds[0].title == "Store"): #Check to see if it is a stores message to find a potential view.
                view = StoreView(self) #Create the view.
                embed = discord.Embed(title="Store", description="Click a button to buy an item:", color=discord.Color.gold()) #Recreate the store message.
                if not self.store: #Check to see if a new item exists.
                  embed.description = "The store is empty."
                await message.edit(embed=embed, view=view) #Rerender the message.
                break

        await ctx.send(f"Item with ID {item_id} removed.", delete_after = 5)  # Delete confirmation after a short delay.

    async def apply_item_effect(self, interaction: discord.Interaction, member: discord.Member, item): #Pass interaction
        """Applies the effect of a purchased item."""
        if item['type'] == "role":
            role = interaction.guild.get_role(int(item['role_id']))
            if role:
                try:
                    await member.add_roles(role)
                except discord.Forbidden:
                    await interaction.followup.send("I don't have the permissions.", ephemeral=True) #use interaction.followup
                except discord.HTTPException:
                    await interaction.followup.send("Adding role failed.", ephemeral=True) #Use interaction.followup

            else:
                await interaction.followup.send("The specified role could not be found.", ephemeral=True) #Use interaction.followup


        elif item['type'] == "color":
            role_name = f"{member.name}-color"
            existing_role = discord.utils.get(interaction.guild.roles, name=role_name)
            color = discord.Colour(int(item['color_hex'], 16))

            if existing_role:
                try:
                    await existing_role.edit(colour=color)
                except discord.Forbidden:
                    await interaction.followup.send("I do not have permissions to edit roles.", ephemeral=True) #Use interaction.followup
                except discord.HTTPException:
                    await interaction.followup.send("Editing role failed.", ephemeral=True) #use interaction.followup
            else:
                try:
                    new_role = await interaction.guild.create_role(name=role_name, colour=color)
                    await member.add_roles(new_role)
                except discord.Forbidden:
                    await interaction.followup.send("I do not have permissions to create and give roles.", ephemeral=True) #use interaction.followup
                except discord.HTTPException:
                    await interaction.followup.send("Creating role failed", ephemeral=True) #use interaction.followup

        elif item['type'] == "badge":
            # Implement logic to add a badge to the user's profile.
            # This might involve storing the badge URL in a user profile database
            # and displaying it somehow (e.g., in a custom profile command).
            # The exact implementation will depend on how you want to handle user profiles.
            await interaction.followup.send("Badge functionality is not yet implemented.", ephemeral=True)  # Placeholder message  #use interaction.followup

        elif item['type'] == "nickname":
            # This is handled in the Modal.
            pass

        else:
            await interaction.followup.send("Unknown item type.", ephemeral=True)  #use interaction.followup


async def setup(bot):
    await bot.add_cog(Store(bot))