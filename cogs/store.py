# cogs/store.py
"""
A cog for a server store where users can buy items with economy currency.
Items can include roles, nickname changes, custom color roles, and badges.
"""
import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput, Select
import json
import os
import asyncio
import logging
import random
from typing import Dict, Any, Optional, List, Tuple # <--- IMPORTS ADDED/MODIFIED HERE

# Assuming your config.py and a shared economy_manager.py are accessible
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

# --- Attempt to import EconomyManager ---
# This assumes EconomyManager is defined in 'cogs.games' as per previous refactoring.
# If EconomyManager is in a different shared utility module (e.g., utils.economy), adjust the import path.
try:
    from cogs.games import EconomyManager # Primary attempt
except ImportError:
    logger = logging.getLogger(__name__) # Define logger here if not already defined globally in this file
    logger.warning(
        "Could not import EconomyManager from 'cogs.games'. "
        "Store cog might not function correctly with economy features if EconomyManager is not available via bot instance. "
        "Ensure Games cog (or wherever EconomyManager is defined) is loaded before Store cog, "
        "and EconomyManager is attached to the bot instance (e.g., bot.economy_manager)."
    )
    # Define a dummy class only if the real one cannot be imported AND it's not expected to be on bot instance.
    # However, the cog __init__ expects it on the bot instance, so this dummy here is less useful.
    # The check in setup for bot.economy_manager is more critical.
    class EconomyManager:
        def __init__(self, *args, **kwargs): pass
        async def get_balance(self, user_id: int) -> int: return 0
        async def update_balance(self, user_id: int, amount: int) -> int: return 0


# --- Logger Setup ---
logger = logging.getLogger(__name__) # Ensures logger is defined for the whole module

# --- Store Manager ---
class StoreManager:
    """Manages store items stored in a JSON file."""
    def __init__(self, file_path: str, lock: asyncio.Lock):
        self.file_path = file_path
        self.lock = lock
        self.store_data: Dict[str, Dict[str, Any]] = {}
        self._load_store()

    def _load_store(self):
        """Loads store data from the JSON file."""
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, 'r') as f:
                    self.store_data = json.load(f)
                logger.info(f"Store data loaded successfully from {self.file_path}")
            else:
                self.store_data = {}
                # Create the file if it doesn't exist
                with open(self.file_path, 'w') as f:
                    json.dump({}, f, indent=4)
                logger.info(f"Store file {self.file_path} not found. Created an empty store file.")
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON from {self.file_path}. Recreating with an empty store.")
            self.store_data = {}
            with open(self.file_path, 'w') as f: # Overwrite corrupted file
                json.dump({}, f, indent=4)
        except Exception as e:
            logger.error(f"Unexpected error loading store data: {e}", exc_info=True)
            self.store_data = {}

    async def _save_store(self):
        """Saves the current store data to the JSON file."""
        async with self.lock:
            try:
                with open(self.file_path, 'w') as f:
                    json.dump(self.store_data, f, indent=4)
                logger.debug(f"Store data saved to {self.file_path}")
            except Exception as e:
                logger.error(f"Error saving store data to {self.file_path}: {e}", exc_info=True)

    async def add_item(self, item_id: str, item_details: Dict[str, Any]) -> bool:
        """Adds an item to the store."""
        if item_id in self.store_data:
            logger.warning(f"Attempted to add item with existing ID: {item_id}")
            return False 
        self.store_data[item_id] = item_details
        await self._save_store()
        logger.info(f"Item '{item_details.get('name', 'Unknown Item')}' (ID: {item_id}) added to store.")
        return True

    async def remove_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Removes an item from the store by its ID."""
        async with self.lock: 
            removed_item = self.store_data.pop(item_id, None)
        if removed_item:
            await self._save_store()
            logger.info(f"Item '{removed_item.get('name', 'Unknown Item')}' (ID: {item_id}) removed from store.")
        else:
            logger.warning(f"Attempted to remove non-existent item ID: {item_id}")
        return removed_item

    def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Gets an item from the store by its ID."""
        return self.store_data.get(item_id)

    def get_all_items(self) -> Dict[str, Dict[str, Any]]:
        """Gets all items in the store."""
        return self.store_data.copy() 

# --- Modals ---
class NicknameModal(Modal, title="Change Your Nickname"):
    new_nickname_input = TextInput(label="New Nickname", placeholder="Enter your desired nickname", required=True, max_length=32)

    def __init__(self, member: discord.Member, store_cog: 'StoreCog', item_id_for_purchase: str): # Added store_cog and item_id
        super().__init__(timeout=getattr(config, 'STORE_NICKNAME_MODAL_TIMEOUT', 180.0))
        self.member = member
        self.store_cog = store_cog
        self.item_id_for_purchase = item_id_for_purchase


    async def on_submit(self, interaction: discord.Interaction):
        new_nick = self.new_nickname_input.value
        item = self.store_cog.store_manager.get_item(self.item_id_for_purchase)

        if not item or item.get('type') != 'nickname': # Should not happen if flow is correct
            await interaction.response.send_message("Error with nickname item. Please try again.", ephemeral=True)
            return

        # Deduct cost now that nickname is confirmed
        try:
            user_balance = await self.store_cog.economy_manager.get_balance(self.member.id)
            item_cost = item.get('cost', 0)
            if user_balance < item_cost: # Double check balance, though StoreView should have checked
                await interaction.response.send_message(getattr(config, 'STORE_MSG_INSUFFICIENT_FUNDS', "❌ You don't have enough {currency}.").format(currency=getattr(config, 'ECONOMY_CURRENCY_NAME', 'coins')), ephemeral=True)
                return
            
            await self.store_cog.economy_manager.update_balance(self.member.id, -item_cost)
            logger.info(f"User {self.member.id} paid {item_cost} for nickname change.")

            await self.member.edit(nick=new_nick)
            await interaction.response.send_message(
                getattr(config, 'STORE_MSG_NICKNAME_CHANGED', "✅ Your nickname has been changed to **{nickname}** and {cost} {currency} deducted!").format(
                    nickname=new_nick, cost=item_cost, currency=getattr(config, 'ECONOMY_CURRENCY_NAME', 'coins')
                ),
                ephemeral=True
            )
            logger.info(f"User {self.member.id} changed nickname to '{new_nick}' via store item.")

        except discord.Forbidden:
            # Refund if forbidden, as cost was deducted optimistically
            await self.store_cog.economy_manager.update_balance(self.member.id, item_cost) 
            await interaction.response.send_message(getattr(config, 'STORE_MSG_NICKNAME_FORBIDDEN', "❌ I don't have permission to change your nickname. Your coins have been refunded."), ephemeral=True)
        except discord.HTTPException as e:
            await self.store_cog.economy_manager.update_balance(self.member.id, item_cost)
            logger.error(f"Failed to change nickname for {self.member.id}: {e}", exc_info=True)
            await interaction.response.send_message(getattr(config, 'STORE_MSG_NICKNAME_ERROR', "❌ An error occurred. Your coins have been refunded."), ephemeral=True)
        except Exception as e:
            # Attempt to refund on any other error during the process
            if item: await self.store_cog.economy_manager.update_balance(self.member.id, item.get('cost',0))
            logger.error(f"Unexpected error in NicknameModal on_submit for {self.member.id}: {e}", exc_info=True)
            await interaction.response.send_message(getattr(config, 'STORE_MSG_GENERIC_ERROR', "❌ An unexpected error occurred. Your coins have been refunded if deducted."), ephemeral=True)


class AddItemModal(Modal, title="Add New Item to Store"):
    item_name_input = TextInput(label="Item Name", placeholder="e.g., VIP Role, Custom Color", required=True, max_length=100)
    item_cost_input = TextInput(label="Item Cost (Coins)", placeholder="e.g., 1000", required=True)
    item_description_input = TextInput(label="Item Description", style=discord.TextStyle.long, placeholder="A brief description of the item and its effect.", required=True, max_length=500)
    item_type_input = TextInput(label=f"Item Type ({', '.join(getattr(config, 'STORE_ITEM_TYPES', {}).keys())})", placeholder="e.g., role, color", required=True)
    item_data_input = TextInput(label="Item Data (Context-Dependent)", placeholder="Role ID, Hex Color (#RRGGBB), Badge Image URL, or 'N/A'", required=False, max_length=200)

    def __init__(self, store_manager: StoreManager):
        super().__init__(timeout=getattr(config, 'STORE_ADD_ITEM_MODAL_TIMEOUT', 300.0))
        self.store_manager = store_manager
        self.valid_item_types = getattr(config, 'STORE_ITEM_TYPES', {"role": {}, "color": {}, "badge": {}, "nickname": {}})

    async def on_submit(self, interaction: discord.Interaction):
        name = self.item_name_input.value
        description = self.item_description_input.value
        item_type_str = self.item_type_input.value.lower()
        item_data_str = self.item_data_input.value or None 

        try:
            cost = int(self.item_cost_input.value)
            if cost < 0:
                await interaction.response.send_message("Item cost must be a non-negative number.", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("Item cost must be a valid number.", ephemeral=True)
            return

        if item_type_str not in self.valid_item_types:
            await interaction.response.send_message(f"Invalid item type. Valid types are: {', '.join(self.valid_item_types.keys())}", ephemeral=True)
            return

        type_config = self.valid_item_types[item_type_str]
        if type_config.get("requires_data", False) and not item_data_str:
            await interaction.response.send_message(f"Item data is required for type '{item_type_str}'. ({type_config.get('data_prompt', '')})", ephemeral=True)
            return
        
        if item_type_str == "role":
            try:
                int(item_data_str) 
            except (ValueError, TypeError):
                await interaction.response.send_message("For 'role' type, Item Data must be a valid Role ID.", ephemeral=True)
                return
        elif item_type_str == "color":
            if not (item_data_str and item_data_str.startswith("#") and len(item_data_str) == 7):
                try:
                    int(item_data_str.lstrip("#"), 16)
                except (ValueError, TypeError):
                     await interaction.response.send_message("For 'color' type, Item Data must be a valid Hex Color string (e.g., #RRGGBB).", ephemeral=True)
                     return
            item_data_str = item_data_str.lstrip("#").upper() # Store canonical form
        elif item_type_str == "badge":
            if not (item_data_str and (item_data_str.startswith("http://") or item_data_str.startswith("https://"))):
                 await interaction.response.send_message("For 'badge' type, Item Data must be a valid Image URL.", ephemeral=True)
                 return

        item_id = str(random.randint(10000, 99999)) 
        while self.store_manager.get_item(item_id): 
            item_id = str(random.randint(10000, 99999))

        new_item_details = {
            "name": name,
            "cost": cost,
            "description": description,
            "type": item_type_str,
            "data": item_data_str 
        }

        if await self.store_manager.add_item(item_id, new_item_details):
            await interaction.response.send_message(
                getattr(config, 'STORE_MSG_ITEM_ADDED', "✅ Item **{name}** (ID: {id}) added to the store!").format(name=name, id=item_id),
                ephemeral=True
            )
        else:
            await interaction.response.send_message("Failed to add item (ID might already exist).", ephemeral=True)

# --- Store View with Pagination ---
class StoreView(View):
    def __init__(self, store_cog: 'StoreCog', items_per_page: int = 5):
        super().__init__(timeout=getattr(config, 'STORE_VIEW_TIMEOUT', 300.0))
        self.store_cog = store_cog
        self.items_per_page = items_per_page
        self.current_page = 0
        self.items: List[Tuple[str, Dict[str, Any]]] = [] 
        self.message: Optional[discord.Message] = None # To store the message this view is attached to
        self._update_items_list()

    def _update_items_list(self):
        all_items = self.store_cog.store_manager.get_all_items()
        self.items = sorted(all_items.items(), key=lambda item_tuple: item_tuple[1].get('name', '').lower())


    async def _get_page_embed_and_buttons(self) -> discord.Embed:
        self.clear_items() 

        start_index = self.current_page * self.items_per_page
        end_index = start_index + self.items_per_page
        page_items = self.items[start_index:end_index]

        embed_color = getattr(config, 'STORE_EMBED_COLOR', discord.Color.gold())
        embed = discord.Embed(title=f"{getattr(config, 'STORE_EMOJI_TITLE', '🛍️')} Item Store - Page {self.current_page + 1}/{ (len(self.items) + self.items_per_page -1) // self.items_per_page }", color=embed_color)
        
        if not self.items:
            embed.description = getattr(config, 'STORE_MSG_EMPTY', "The store is currently empty. Check back later!")
            return embed

        if not page_items and self.current_page > 0: # Navigated to an empty page beyond actual items
            self.current_page -=1 # Go back one page
            start_index = self.current_page * self.items_per_page
            end_index = start_index + self.items_per_page
            page_items = self.items[start_index:end_index]
            embed.title = f"{getattr(config, 'STORE_EMOJI_TITLE', '🛍️')} Item Store - Page {self.current_page + 1}/{ (len(self.items) + self.items_per_page -1) // self.items_per_page }"


        for item_id, item in page_items:
            item_label = item.get('name', 'Unknown Item')
            item_cost = item.get('cost', 0)
            item_desc = item.get('description', 'No description.')
            item_type_display = item.get('type', 'N/A').capitalize()
            currency_name = getattr(config, 'ECONOMY_CURRENCY_NAME', 'coins')

            embed.add_field(
                name=f"{item_label} - {item_cost} {currency_name}",
                value=f"*Type: {item_type_display}*\n{item_desc}",
                inline=False
            )
            buy_button = Button(label=f"Buy {item_label}", custom_id=f"buy_{item_id}", style=discord.ButtonStyle.green, emoji=getattr(config, 'STORE_EMOJI_BUY', '🛒'))
            buy_button.callback = self.buy_button_callback
            self.add_item(buy_button)

        if self.current_page > 0:
            prev_button = Button(label="Previous", custom_id="prev_page", style=discord.ButtonStyle.blurple, emoji="⬅️")
            prev_button.callback = self.nav_button_callback
            self.add_item(prev_button)

        if end_index < len(self.items):
            next_button = Button(label="Next", custom_id="next_page", style=discord.ButtonStyle.blurple, emoji="➡️")
            next_button.callback = self.nav_button_callback
            self.add_item(next_button)
            
        return embed

    async def nav_button_callback(self, interaction: discord.Interaction):
        custom_id = interaction.data["custom_id"]
        if custom_id == "prev_page" and self.current_page > 0:
            self.current_page -= 1
        elif custom_id == "next_page" and (self.current_page + 1) * self.items_per_page < len(self.items):
            self.current_page += 1
        
        embed = await self._get_page_embed_and_buttons()
        await interaction.response.edit_message(embed=embed, view=self)

    async def buy_button_callback(self, interaction: discord.Interaction):
        item_id = interaction.data["custom_id"].replace("buy_", "")
        item = self.store_cog.store_manager.get_item(item_id)

        if not item:
            await interaction.response.send_message(getattr(config, 'STORE_MSG_ITEM_NOT_FOUND', "❌ This item is no longer available."), ephemeral=True)
            self._update_items_list()
            embed = await self._get_page_embed_and_buttons()
            if self.message:
                try: await self.message.edit(embed=embed, view=self)
                except discord.HTTPException: pass
            return

        user_balance = await self.store_cog.economy_manager.get_balance(interaction.user.id)
        item_cost = item.get('cost', 0)

        if user_balance < item_cost:
            await interaction.response.send_message(
                getattr(config, 'STORE_MSG_INSUFFICIENT_FUNDS', "❌ You don't have enough {currency} to buy **{item_name}**.").format(
                    currency=getattr(config, 'ECONOMY_CURRENCY_NAME', 'coins'), item_name=item.get('name')
                ), ephemeral=True)
            return

        if item.get('type') == "nickname":
            # For nickname, we open the modal first. Cost is deducted *after* successful modal submission.
            nick_modal = NicknameModal(member=interaction.user, store_cog=self.store_cog, item_id_for_purchase=item_id)
            await interaction.response.send_modal(nick_modal)
            # The modal's on_submit will handle cost deduction and confirmation.
            return 

        # For other items, defer, deduct cost, then apply effect.
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.store_cog.economy_manager.update_balance(interaction.user.id, -item_cost)
        success = await self.store_cog.apply_item_effect(interaction, interaction.user, item, is_purchase_interaction=True)

        if success:
             await interaction.followup.send(
                getattr(config, 'STORE_MSG_ITEM_PURCHASED', "✅ You successfully purchased **{item_name}**! {cost} {currency} deducted.").format(
                    item_name=item.get('name'), cost=item_cost, currency=getattr(config, 'ECONOMY_CURRENCY_NAME', 'coins')
                    ),
                ephemeral=True
            )
        else: # apply_item_effect should send its own error, but if not, refund.
            # If apply_item_effect returned False and didn't send a message, we might need a generic failure message.
            # And crucial: refund if effect application failed AFTER deduction.
            if not interaction.is_done(): # Check if interaction already responded by apply_item_effect
                 await interaction.followup.send("Failed to apply item effect. Your coins have been refunded.", ephemeral=True)
            await self.store_cog.economy_manager.update_balance(interaction.user.id, item_cost) # Refund
            logger.warning(f"Item effect application failed for {item.get('name')} for user {interaction.user.id}. Coins refunded.")


    async def on_timeout(self):
        for child in self.children:
            if isinstance(child, (Button, Select)):
                child.disabled = True
        if self.message: 
            try:
                timeout_embed = discord.Embed(title="Store Closed", description="This store session has timed out. Use the store command again.", color=discord.Color.orange())
                await self.message.edit(embed=timeout_embed, view=self) 
            except discord.HTTPException:
                pass 
        logger.info("StoreView timed out and disabled components.")


# --- Store Cog ---
class StoreCog(commands.Cog, name="Store"):
    """Manages a virtual store where users can buy items using server currency."""
    def __init__(self, bot: commands.Bot): 
        self.bot = bot
        # --- CRITICAL: Ensure EconomyManager is available on the bot instance ---
        if not hasattr(bot, 'economy_manager'):
            logger.critical("StoreCog FATAL: bot.economy_manager not found! GamesCog (or main bot setup) must initialize and attach it.")
            # Fallback to a dummy to prevent immediate crash, but features will be broken.
            class DummyEconomyManager:
                async def get_balance(self, user_id): return 0
                async def update_balance(self, user_id, amount): return 0
            self.economy_manager = DummyEconomyManager()
            # Consider raising an exception here to halt bot startup if EconomyManager is essential
            # raise RuntimeError("EconomyManager not found on bot instance. StoreCog cannot function.")
        else:
            self.economy_manager = bot.economy_manager
        
        self.store_file_path = getattr(config, 'STORE_FILE_PATH', 'data/store.json')
        store_dir = os.path.dirname(self.store_file_path)
        if store_dir and not os.path.exists(store_dir):
            os.makedirs(store_dir, exist_ok=True)
        
        self.store_lock = asyncio.Lock()
        self.store_manager = StoreManager(file_path=self.store_file_path, lock=self.store_lock)
        logger.info(f"Store Cog loaded. Store manager initialized with file: {self.store_file_path}")

    @commands.command(name="balance", aliases=["bal", "money"], help="Check your or another user's coin balance.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def balance(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        target_user = member or ctx.author
        user_balance = await self.economy_manager.get_balance(target_user.id)
        currency_name = getattr(config, 'ECONOMY_CURRENCY_NAME', 'coins')
        await ctx.send(
            getattr(config, 'STORE_MSG_BALANCE_CHECK', "{user_mention}'s balance: **{balance}** {currency}.").format(
                user_mention=target_user.mention, balance=user_balance, currency=currency_name
            )
        )

    @commands.command(name="store", help="Displays available items in the store.")
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def store_command(self, ctx: commands.Context): 
        view = StoreView(self, items_per_page=getattr(config, 'STORE_ITEMS_PER_PAGE', 5))
        view._update_items_list() 
        embed = await view._get_page_embed_and_buttons()
        
        message = await ctx.send(embed=embed, view=view)
        view.message = message


    @commands.command(name="addstoreitem", help="Adds an item to the store (Admin only).")
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def add_store_item(self, ctx: commands.Context):
        class AdminAddItemView(View):
            def __init__(self, store_manager_ref):
                super().__init__(timeout=60.0) # Short timeout for this admin action button
                self.store_manager_ref = store_manager_ref
                self.message_to_delete: Optional[discord.Message] = None
            
            @discord.ui.button(label="Add New Store Item", style=discord.ButtonStyle.primary)
            async def add_item_button(self, interaction: discord.Interaction, button: Button):
                modal = AddItemModal(self.store_manager_ref)
                await interaction.response.send_modal(modal)
                button.disabled = True # Disable after click
                await interaction.edit_original_response(view=self) # Update the view on the message
                # Optionally, make the button message ephemeral or delete it after modal submission
                # For now, just disable.
                self.stop() # Stop this view

            async def on_timeout(self):
                if self.message_to_delete:
                    try:
                        for child in self.children: # Disable all components on timeout
                            if isinstance(child, (Button, Select)):
                                child.disabled = True
                        await self.message_to_delete.edit(content="Item addition prompt timed out.", view=self)
                    except discord.HTTPException:
                        pass # Message might have been deleted

        view = AdminAddItemView(self.store_manager)
        msg = await ctx.send("Click the button to add a new item to the store:", view=view)
        view.message_to_delete = msg


    @commands.command(name="removestoreitem", help="Removes an item from the store by ID (Admin only).")
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def remove_store_item(self, ctx: commands.Context, item_id: str):
        removed_item = await self.store_manager.remove_item(item_id)
        if removed_item:
            await ctx.send(
                getattr(config, 'STORE_MSG_ITEM_REMOVED', "🗑 Item **{item_name}** (ID: {id}) has been removed from the store.").format(
                    item_name=removed_item.get('name', 'Unknown'), id=item_id
                )
            )
        else:
            await ctx.send(getattr(config, 'STORE_MSG_ITEM_ID_NOT_FOUND_REMOVE', "❌ No item found with ID `{id}`.").format(id=item_id))

    async def apply_item_effect(self, interaction: discord.Interaction, member: discord.Member, item: Dict[str, Any], is_purchase_interaction: bool = False) -> bool:
        item_type = item.get("type")
        item_data = item.get("data")
        item_name = item.get("name", "Unknown Item")
        guild = interaction.guild
        
        # Use followup if called from a deferred interaction (like a purchase button)
        # Use response if called from a new interaction (like a modal submit that wasn't deferred yet)
        # This logic is tricky. The `is_purchase_interaction` helps.
        # If it's a purchase, StoreView already deferred.
        # If it's a modal submit, the modal's on_submit handles the response.
        # This method is now more for non-modal effects or post-modal confirmations.
        
        # For non-nickname items where cost is already deducted by StoreView:
        response_method = interaction.followup.send if is_purchase_interaction else interaction.response.send_message

        try:
            if item_type == "role":
                role_id = int(item_data)
                role_to_assign = guild.get_role(role_id)
                if role_to_assign:
                    if role_to_assign in member.roles:
                        # This message should ideally be sent by the buy_button_callback if it checks first.
                        # If we reach here, it's a bit late.
                        # await response_method(getattr(config, 'STORE_MSG_ROLE_ALREADY_HAS', "ℹ️ You already have the **{role_name}** role.").format(role_name=role_to_assign.name), ephemeral=True)
                        logger.info(f"User {member.id} already has role '{role_to_assign.name}' for item '{item_name}'.")
                        return True # Considered "successful" as the state is achieved.
                    await member.add_roles(role_to_assign, reason=f"Purchased '{item_name}' from store.")
                    logger.info(f"Assigned role '{role_to_assign.name}' to {member.id} for item '{item_name}'.")
                    return True
                else:
                    await response_method(getattr(config, 'STORE_MSG_ROLE_NOT_FOUND_EFFECT', "❌ The role for this item could not be found. Your coins have been refunded."), ephemeral=True)
                    return False # Signal failure for refund

            elif item_type == "color":
                hex_color_str = str(item_data) 
                color_val = int(hex_color_str, 16)
                color = discord.Color(color_val)
                # Sanitize role name slightly more
                safe_member_name = ''.join(c if c.isalnum() else '_' for c in member.name)
                role_name = f"{safe_member_name}_color_{hex_color_str}"[:100] # Max role name length is 100
                
                existing_color_roles = [r for r in member.roles if r.name.startswith(f"{safe_member_name}_color_")]
                for old_role in existing_color_roles:
                    if old_role.name != role_name: # Don't remove if it's the exact same role we are about to apply/edit
                        try:
                            await member.remove_roles(old_role, reason="Applying new custom color role.")
                            # Check if role is used by anyone else before deleting
                            if not old_role.members:
                                await old_role.delete(reason="Custom color role no longer in use.")
                                logger.info(f"Deleted unused old color role {old_role.name} for {member.id}")
                        except discord.HTTPException as e:
                            logger.warning(f"Could not remove/delete old color role {old_role.name} for {member.id}: {e}")
                
                custom_role = discord.utils.get(guild.roles, name=role_name)
                if custom_role:
                    await custom_role.edit(colour=color, reason=f"Updating custom color for {member.name}")
                    if custom_role not in member.roles: # Ensure member has the role if it was edited
                        await member.add_roles(custom_role)
                else:
                    custom_role = await guild.create_role(name=role_name, colour=color, reason=f"Creating custom color for {member.name}")
                    await member.add_roles(custom_role)
                
                logger.info(f"Applied color {hex_color_str} to {member.id} via role '{custom_role.name}'.")
                return True

            elif item_type == "badge":
                badge_url = str(item_data)
                logger.info(f"User {member.id} purchased badge '{item_name}' with URL: {badge_url}. (Badge display logic needed)")
                # Actual badge application depends on how your bot handles profiles.
                # This might involve DB updates.
                # The message is sent by the buy_button_callback.
                return True 

            elif item_type == "nickname":
                # This case is now handled by the NicknameModal's on_submit method,
                # which includes cost deduction and sending its own confirmation/error.
                # The StoreView's buy_button_callback directly invokes the modal.
                # So, this part of apply_item_effect for "nickname" should not be reached
                # if the modal flow is the primary path.
                # If it *were* reached (e.g., a different flow), it would need to open the modal.
                # For now, assume StoreView handles modal opening.
                logger.debug(f"apply_item_effect called for nickname item '{item_name}' - should be handled by NicknameModal flow.")
                return True # The purchase initiation was successful, modal takes over.

            else:
                await response_method(getattr(config, 'STORE_MSG_UNKNOWN_ITEM_TYPE_EFFECT', "❓ Don't know how to apply this item type. Coins refunded."), ephemeral=True)
                return False # Signal failure for refund

        except discord.Forbidden:
            logger.warning(f"Permission error applying item '{item_name}' for {member.id}: Bot lacks permissions.")
            await response_method(getattr(config, 'STORE_MSG_APPLY_EFFECT_FORBIDDEN', "❌ I don't have the necessary permissions to apply this item's effect. Your coins have been refunded."), ephemeral=True)
            return False
        except discord.HTTPException as e:
            logger.error(f"HTTP error applying item '{item_name}' for {member.id}: {e}", exc_info=True)
            await response_method(getattr(config, 'STORE_MSG_APPLY_EFFECT_HTTP_ERROR', "❌ A Discord error occurred while applying this item. Please try again later. Your coins have been refunded."), ephemeral=True)
            return False
        except ValueError as e: 
             logger.warning(f"ValueError applying item '{item_name}' for {member.id}: {e}")
             await response_method(f"❌ Invalid data for item effect: {e}. Your coins have been refunded.", ephemeral=True)
             return False
        except Exception as e:
            logger.error(f"Unexpected error applying item '{item_name}' for {member.id}: {e}", exc_info=True)
            await response_method(getattr(config, 'STORE_MSG_APPLY_EFFECT_UNEXPECTED_ERROR', "❌ An unexpected error occurred. Your coins have been refunded."), ephemeral=True)
            return False

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        # Generic error handler for this cog's commands
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing argument: `{error.param.name}`. Usage: `{ctx.prefix}help {ctx.command.qualified_name}`")
        elif isinstance(error, commands.BadArgument): # Catches failed Member, int conversions etc.
            await ctx.send(f"Invalid argument provided for `{error.param.name if hasattr(error, 'param') else 'argument'}`. Please check the command usage.")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"This command is on cooldown. Try again in {error.retry_after:.2f} seconds.")
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send("Store commands generally work best in servers.")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send(f"You don't have the required permissions ({', '.join(error.missing_permissions)}) to use this command.")
        else:
            logger.error(f"Unhandled error in Store command '{ctx.command.qualified_name if ctx.command else 'N/A'}': {error}", exc_info=True)
            await ctx.send("An unexpected error occurred with that store command.")

async def setup(bot: commands.Bot):
    """Sets up the StoreCog, injecting the EconomyManager."""
    if not hasattr(bot, 'economy_manager'):
        logger.critical(
            "StoreCog setup WARNING: `bot.economy_manager` not found! "
            "Ensure GamesCog (or main bot setup) initializes and attaches EconomyManager to the bot instance "
            "BEFORE StoreCog is loaded. Store features requiring economy will fail or use a dummy manager."
        )
        # Define a dummy if not present, so cog loads but logs warnings.
        class DummyEconomyManager:
            async def get_balance(self, user_id): 
                logger.warning("DummyEconomyManager: get_balance called.")
                return 0
            async def update_balance(self, user_id, amount): 
                logger.warning("DummyEconomyManager: update_balance called.")
                return 0
        bot.economy_manager = DummyEconomyManager() # This allows cog to load but is not a real fix.

    store_dir = os.path.dirname(getattr(config, 'STORE_FILE_PATH', 'data/store.json'))
    if store_dir and not os.path.exists(store_dir):
        try:
            os.makedirs(store_dir, exist_ok=True)
            logger.info(f"Created directory for store file: {store_dir}")
        except OSError as e:
            logger.error(f"Could not create directory {store_dir} for store file: {e}")

    await bot.add_cog(StoreCog(bot)) 
    logger.info("StoreCog has been setup and added to the bot.")

