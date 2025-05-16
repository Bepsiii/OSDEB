# cogs/store.py
"""
A cog for a server store where users can buy items with economy currency.
Items can include roles, nickname changes, custom color roles, and badges.
"""
import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput, Select # Select might be used later
import json
import os
import asyncio
import logging
import random
from typing import Dict, Any, Optional, List, Tuple # <--- IMPORTS ENSURED HERE

# Assuming your config.py is accessible
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

# EconomyManager is expected to be on bot.economy_manager, set up by GamesCog or main bot.py
# No direct import of EconomyManager class here is strictly needed if that pattern is followed.

# --- Logger Setup ---
logger = logging.getLogger(__name__)

# --- Store Manager (Class definition should be the same as store_cog_py_refactored_v2) ---
class StoreManager:
    """Manages store items stored in a JSON file."""
    def __init__(self, file_path: str, lock: asyncio.Lock):
        self.file_path = file_path
        self.lock = lock
        self.store_data: Dict[str, Dict[str, Any]] = {}
        self._load_store() # Load data on initialization

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
                    json.dump({}, f, indent=4) # Save an empty JSON object
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
        if item_id in self.store_data:
            logger.warning(f"Attempted to add item with existing ID: {item_id}")
            return False 
        self.store_data[item_id] = item_details
        await self._save_store()
        logger.info(f"Item '{item_details.get('name', 'Unknown Item')}' (ID: {item_id}) added to store.")
        return True

    async def remove_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        async with self.lock: 
            removed_item = self.store_data.pop(item_id, None)
        if removed_item:
            await self._save_store()
            logger.info(f"Item '{removed_item.get('name', 'Unknown Item')}' (ID: {item_id}) removed from store.")
        else:
            logger.warning(f"Attempted to remove non-existent item ID: {item_id}")
        return removed_item

    def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        return self.store_data.get(item_id)

    def get_all_items(self) -> Dict[str, Dict[str, Any]]:
        return self.store_data.copy() 

# --- Modals (NicknameModal, AddItemModal - ensure these are the same as store_cog_py_refactored_v2) ---
# For brevity, re-pasting only NicknameModal with the fix for constructor. AddItemModal should be fine.
class NicknameModal(Modal, title="Change Your Nickname"):
    new_nickname_input = TextInput(label="New Nickname", placeholder="Enter your desired nickname", required=True, max_length=32)

    def __init__(self, member: discord.Member, store_cog: 'StoreCog', item_id_for_purchase: str):
        super().__init__(timeout=getattr(config, 'STORE_NICKNAME_MODAL_TIMEOUT', 180.0))
        self.member = member
        self.store_cog = store_cog # Store the cog instance
        self.item_id_for_purchase = item_id_for_purchase # Store the item ID

    async def on_submit(self, interaction: discord.Interaction):
        new_nick = self.new_nickname_input.value
        item = self.store_cog.store_manager.get_item(self.item_id_for_purchase)
        currency_name = getattr(config, 'ECONOMY_CURRENCY_NAME', 'coins')

        if not item or item.get('type') != 'nickname':
            await interaction.response.send_message("Error: Nickname change item not found or invalid.", ephemeral=True)
            return

        item_cost = item.get('cost', 0)
        user_balance = await self.store_cog.economy_manager.get_balance(self.member.id)

        if user_balance < item_cost:
            msg = getattr(config, 'STORE_MSG_INSUFFICIENT_FUNDS', "❌ You don't have enough {currency} to buy **{item_name}**.").format(
                currency=currency_name, item_name=item.get('name')
            )
            await interaction.response.send_message(msg, ephemeral=True)
            return

        try:
            await self.member.edit(nick=new_nick)
            # Deduct cost AFTER successful nickname change
            await self.store_cog.economy_manager.update_balance(self.member.id, -item_cost)
            
            msg = getattr(config, 'STORE_MSG_NICKNAME_CHANGED', "✅ Your nickname changed to **{nickname}**! {cost} {currency} deducted.").format(
                nickname=new_nick, cost=item_cost, currency=currency_name
            )
            await interaction.response.send_message(msg, ephemeral=True)
            logger.info(f"User {self.member.id} changed nickname to '{new_nick}' via store. Cost: {item_cost}")
        except discord.Forbidden:
            # No cost deduction if forbidden, as it wasn't applied
            await interaction.response.send_message(getattr(config, 'STORE_MSG_NICKNAME_FORBIDDEN', "❌ I don't have permission to change your nickname. No coins were deducted."), ephemeral=True)
        except discord.HTTPException as e:
            logger.error(f"Failed to change nickname for {self.member.id}: {e}", exc_info=True)
            await interaction.response.send_message(getattr(config, 'STORE_MSG_NICKNAME_ERROR', "❌ An error occurred changing nickname. No coins were deducted."), ephemeral=True)
        except Exception as e:
            logger.error(f"Unexpected error in NicknameModal on_submit for {self.member.id}: {e}", exc_info=True)
            await interaction.response.send_message(getattr(config, 'STORE_MSG_GENERIC_ERROR', "❌ An unexpected error occurred. Please try again."), ephemeral=True)

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
            if not (item_data_str and item_data_str.startswith("#") and len(item_data_str) == 7): # Basic hex check
                try: # Allow if user forgets # but provides valid 6-digit hex
                    int(item_data_str.lstrip("#"), 16)
                    if len(item_data_str.lstrip("#")) != 6: raise ValueError("Hex not 6 digits")
                except (ValueError, TypeError):
                     await interaction.response.send_message("For 'color' type, Item Data must be a valid Hex Color string (e.g., #RRGGBB or RRGGBB).", ephemeral=True)
                     return
            item_data_str = item_data_str.lstrip("#").upper() # Store canonical form (6 digits, uppercase)
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
        else: # Should be rare if ID generation is robust
            await interaction.response.send_message("Failed to add item (ID might already exist or other issue).", ephemeral=True)


# --- Store View with Pagination (Class definition should be the same as store_cog_py_refactored_v2) ---
class StoreView(View):
    def __init__(self, store_cog: 'StoreCog', items_per_page: int = 5):
        super().__init__(timeout=getattr(config, 'STORE_VIEW_TIMEOUT', 300.0))
        self.store_cog = store_cog
        self.items_per_page = items_per_page
        self.current_page = 0
        self.items: List[Tuple[str, Dict[str, Any]]] = [] 
        self.message: Optional[discord.Message] = None 
        self._update_items_list()

    def _update_items_list(self):
        all_items = self.store_cog.store_manager.get_all_items()
        self.items = sorted(all_items.items(), key=lambda item_tuple: item_tuple[1].get('name', '').lower())

    async def _get_page_embed_and_buttons(self) -> discord.Embed:
        self.clear_items() 
        total_pages = (len(self.items) + self.items_per_page - 1) // self.items_per_page
        if total_pages == 0: total_pages = 1 # Ensure at least 1 page even if empty

        start_index = self.current_page * self.items_per_page
        end_index = start_index + self.items_per_page
        page_items = self.items[start_index:end_index]

        embed_color = getattr(config, 'STORE_EMBED_COLOR', discord.Color.gold())
        embed = discord.Embed(title=f"{getattr(config, 'STORE_EMOJI_TITLE', '🛍️')} Item Store - Page {self.current_page + 1}/{total_pages}", color=embed_color)
        
        if not self.items:
            embed.description = getattr(config, 'STORE_MSG_EMPTY', "The store is currently empty. Check back later!")
            return embed

        if not page_items and self.current_page > 0: 
            self.current_page = max(0, total_pages - 1) # Go to last valid page or 0
            start_index = self.current_page * self.items_per_page
            end_index = start_index + self.items_per_page
            page_items = self.items[start_index:end_index]
            embed.title = f"{getattr(config, 'STORE_EMOJI_TITLE', '🛍️')} Item Store - Page {self.current_page + 1}/{total_pages}"

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

        if end_index < len(self.items): # or self.current_page < total_pages -1
            next_button = Button(label="Next", custom_id="next_page", style=discord.ButtonStyle.blurple, emoji="➡️")
            next_button.callback = self.nav_button_callback
            self.add_item(next_button)
            
        return embed

    async def nav_button_callback(self, interaction: discord.Interaction):
        custom_id = interaction.data["custom_id"]
        if custom_id == "prev_page" and self.current_page > 0:
            self.current_page -= 1
        elif custom_id == "next_page" :
            total_pages = (len(self.items) + self.items_per_page - 1) // self.items_per_page
            if self.current_page < total_pages -1 :
                 self.current_page += 1
        
        embed = await self._get_page_embed_and_buttons()
        await interaction.response.edit_message(embed=embed, view=self)

    async def buy_button_callback(self, interaction: discord.Interaction):
        item_id = interaction.data["custom_id"].replace("buy_", "")
        item = self.store_cog.store_manager.get_item(item_id)
        currency_name = getattr(config, 'ECONOMY_CURRENCY_NAME', 'coins')

        if not item:
            await interaction.response.send_message(getattr(config, 'STORE_MSG_ITEM_NOT_FOUND', "❌ This item is no longer available."), ephemeral=True)
            self._update_items_list() # Refresh items in case it was removed
            embed = await self._get_page_embed_and_buttons()
            if self.message:
                try: await self.message.edit(embed=embed, view=self)
                except discord.HTTPException: pass
            return

        user_balance = await self.store_cog.economy_manager.get_balance(interaction.user.id)
        item_cost = item.get('cost', 0)
        item_name = item.get('name', 'Unknown Item')

        if user_balance < item_cost:
            msg = getattr(config, 'STORE_MSG_INSUFFICIENT_FUNDS', "❌ You don't have enough {currency} to buy **{item_name}**.").format(
                currency=currency_name, item_name=item_name
            )
            await interaction.response.send_message(msg, ephemeral=True)
            return

        if item.get('type') == "nickname":
            nick_modal = NicknameModal(member=interaction.user, store_cog=self.store_cog, item_id_for_purchase=item_id)
            await interaction.response.send_modal(nick_modal)
            # Cost deduction and confirmation for nickname is handled within NicknameModal.on_submit
            return 

        # For other items, defer, deduct cost, then apply effect.
        await interaction.response.defer(ephemeral=True, thinking=True) # Defer for non-modal items
        
        # Try to apply effect first, then deduct if successful (or deduct then refund on fail)
        # Let's try: apply effect, if it returns True, then deduct.
        effect_applied_successfully = await self.store_cog.apply_item_effect(interaction, interaction.user, item, is_purchase_interaction=True)

        if effect_applied_successfully:
            await self.store_cog.economy_manager.update_balance(interaction.user.id, -item_cost)
            msg = getattr(config, 'STORE_MSG_ITEM_PURCHASED', "✅ You successfully purchased **{item_name}**! {cost} {currency} deducted.").format(
                item_name=item_name, cost=item_cost, currency=currency_name
            )
            await interaction.followup.send(msg, ephemeral=True)
        else:
            # apply_item_effect should have sent an error message.
            # No cost was deducted if effect_applied_successfully is False.
            # If apply_item_effect had already deducted and then failed, it should have refunded.
            # This path means the effect couldn't be applied BEFORE deduction.
            if not interaction.is_done(): # Check if apply_item_effect already responded
                 await interaction.followup.send(f"Could not apply the effect for **{item_name}**. No {currency_name} were deducted.", ephemeral=True)
            logger.warning(f"Item effect application failed for {item_name} for user {interaction.user.id}. No cost deducted by buy_button_callback.")


    async def on_timeout(self):
        for child in self.children:
            if isinstance(child, (Button, Select)):
                child.disabled = True
        if self.message: 
            try:
                timeout_embed = discord.Embed(title="Store Closed", description="This store session has timed out. Use the store command again.", color=discord.Color.orange())
                await self.message.edit(embed=timeout_embed, view=self) 
            except discord.HTTPException: pass 
        logger.info("StoreView timed out and disabled components.")


# --- Store Cog ---
class StoreCog(commands.Cog, name="Store"):
    """Manages a virtual store where users can buy items using server currency."""
    def __init__(self, bot: commands.Bot): 
        self.bot = bot
        if not hasattr(bot, 'economy_manager'):
            logger.critical("StoreCog FATAL: bot.economy_manager not found! GamesCog (or main bot setup) must initialize and attach it before StoreCog loads.")
            # Define a dummy to allow bot to load but log errors for economy actions
            class DummyEconomyManager:
                async def get_balance(self, user_id): logger.error("DummyEconomyManager: get_balance called!"); return 0
                async def update_balance(self, user_id, amount): logger.error("DummyEconomyManager: update_balance called!"); return 0
            self.economy_manager = DummyEconomyManager()
        else:
            self.economy_manager = bot.economy_manager
        
        self.store_file_path = getattr(config, 'STORE_FILE_PATH', 'data/store.json')
        store_dir = os.path.dirname(self.store_file_path)
        if store_dir and not os.path.exists(store_dir):
            os.makedirs(store_dir, exist_ok=True)
        
        self.store_lock = asyncio.Lock()
        self.store_manager = StoreManager(file_path=self.store_file_path, lock=self.store_lock)
        logger.info(f"Store Cog loaded. Store manager initialized with file: {self.store_file_path}")

    # --- FIX: Removed duplicate balance command ---
    # The 'balance' command should be primarily in the GamesCog if EconomyManager is shared.

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
                super().__init__(timeout=60.0) 
                self.store_manager_ref = store_manager_ref
                self.message_to_delete: Optional[discord.Message] = None
            
            @discord.ui.button(label="Add New Store Item", style=discord.ButtonStyle.primary)
            async def add_item_button(self, interaction: discord.Interaction, button: Button):
                modal = AddItemModal(self.store_manager_ref)
                await interaction.response.send_modal(modal)
                button.disabled = True 
                await interaction.edit_original_response(view=self) 
                self.stop() 

            async def on_timeout(self):
                if self.message_to_delete:
                    try:
                        for child_component in self.children: 
                            if isinstance(child_component, (Button, Select)):
                                child_component.disabled = True
                        await self.message_to_delete.edit(content="Item addition prompt timed out.", view=self)
                    except discord.HTTPException: pass

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
        item_cost = item.get("cost", 0) # Get cost for refund messages
        currency_name = getattr(config, 'ECONOMY_CURRENCY_NAME', 'coins')
        
        response_method = interaction.followup.send if is_purchase_interaction and interaction.response.is_done() else interaction.response.send_message

        try:
            if item_type == "role":
                role_id = int(item_data)
                role_to_assign = guild.get_role(role_id)
                if role_to_assign:
                    if role_to_assign in member.roles:
                        # This message is now better handled by StoreView before calling apply_item_effect
                        logger.info(f"User {member.id} already has role '{role_to_assign.name}' for item '{item_name}'.")
                        # If StoreView didn't catch it, send a message.
                        if is_purchase_interaction: # Only send if it's a direct purchase attempt that got this far
                             await response_method(getattr(config, 'STORE_MSG_ROLE_ALREADY_HAS', "ℹ️ You already have the **{role_name}** role. No {currency} deducted.").format(role_name=role_to_assign.name, currency=currency_name), ephemeral=True)
                        return True # Considered "successful" as state is achieved, no cost should have been deducted yet by caller
                    await member.add_roles(role_to_assign, reason=f"Purchased '{item_name}' from store.")
                    logger.info(f"Assigned role '{role_to_assign.name}' to {member.id} for item '{item_name}'.")
                    return True
                else: # Role not found on server
                    await response_method(getattr(config, 'STORE_MSG_ROLE_NOT_FOUND_EFFECT', "❌ The role for this item could not be found. Your {currency} have been refunded if deducted.").format(currency=currency_name), ephemeral=True)
                    return False 

            elif item_type == "color":
                hex_color_str = str(item_data) 
                color_val = int(hex_color_str, 16)
                color = discord.Color(color_val)
                safe_member_name = ''.join(c if c.isalnum() else '_' for c in member.name)
                role_name = f"{safe_member_name}_color_{hex_color_str}"[:100] 
                
                existing_color_roles = [r for r in member.roles if r.name.startswith(f"{safe_member_name}_color_")]
                for old_role in existing_color_roles:
                    if old_role.name != role_name: 
                        try:
                            await member.remove_roles(old_role, reason="Applying new custom color role.")
                            if not old_role.members: 
                                await old_role.delete(reason="Custom color role no longer in use.")
                                logger.info(f"Deleted unused old color role {old_role.name} for {member.id}")
                        except discord.HTTPException as e:
                            logger.warning(f"Could not remove/delete old color role {old_role.name} for {member.id}: {e}")
                
                custom_role = discord.utils.get(guild.roles, name=role_name)
                if custom_role:
                    await custom_role.edit(colour=color, reason=f"Updating custom color for {member.name}")
                    if custom_role not in member.roles: 
                        await member.add_roles(custom_role)
                else:
                    custom_role = await guild.create_role(name=role_name, colour=color, reason=f"Creating custom color for {member.name}")
                    await member.add_roles(custom_role)
                
                logger.info(f"Applied color {hex_color_str} to {member.id} via role '{custom_role.name}'.")
                return True

            elif item_type == "badge":
                badge_url = str(item_data)
                logger.info(f"User {member.id} purchased badge '{item_name}' with URL: {badge_url}. (Badge display logic needed)")
                # The confirmation message is sent by the buy_button_callback
                return True 

            elif item_type == "nickname":
                # This is now fully handled by NicknameModal's on_submit, including cost and confirmation.
                # This function should not be called for 'nickname' type by StoreView's buy_button_callback.
                logger.error("apply_item_effect was called for 'nickname' type unexpectedly.")
                return False # Should not happen

            else: # Unknown item type
                msg = getattr(config, 'STORE_MSG_UNKNOWN_ITEM_TYPE_EFFECT', "❓ Don't know how to apply this item type. Your {currency} have been refunded if deducted.").format(currency=currency_name)
                await response_method(msg, ephemeral=True)
                return False

        except discord.Forbidden:
            logger.warning(f"Permission error applying item '{item_name}' for {member.id}: Bot lacks permissions.")
            msg = getattr(config, 'STORE_MSG_APPLY_EFFECT_FORBIDDEN', "❌ I don't have the necessary permissions. Your {currency} have been refunded if deducted.").format(currency=currency_name)
            await response_method(msg, ephemeral=True)
            return False
        except discord.HTTPException as e:
            logger.error(f"HTTP error applying item '{item_name}' for {member.id}: {e}", exc_info=True)
            msg = getattr(config, 'STORE_MSG_APPLY_EFFECT_HTTP_ERROR', "❌ A Discord error occurred. Your {currency} have been refunded if deducted.").format(currency=currency_name)
            await response_method(msg, ephemeral=True)
            return False
        except ValueError as e: 
             logger.warning(f"ValueError applying item '{item_name}' for {member.id}: {e}")
             await response_method(f"❌ Invalid data for item effect: {e}. Your {currency_name} have been refunded if deducted.", ephemeral=True)
             return False
        except Exception as e:
            logger.error(f"Unexpected error applying item '{item_name}' for {member.id}: {e}", exc_info=True)
            msg = getattr(config, 'STORE_MSG_APPLY_EFFECT_UNEXPECTED_ERROR', "❌ An unexpected error occurred. Your {currency} have been refunded if deducted.").format(currency=currency_name)
            await response_method(msg, ephemeral=True)
            return False

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing argument: `{error.param.name}`. Usage: `{ctx.prefix}help {ctx.command.qualified_name}`")
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"Invalid argument provided for `{error.param.name if hasattr(error, 'param') else 'argument'}`. Please check command usage.")
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
    """Sets up the StoreCog, ensuring EconomyManager is available on the bot instance."""
    if not hasattr(bot, 'economy_manager'):
        logger.critical(
            "StoreCog setup FAILURE: `bot.economy_manager` not found! "
            "The GamesCog (or your main bot file) MUST initialize and attach the EconomyManager "
            "to the bot instance (e.g., `bot.economy_manager = an_economy_manager_instance`) "
            "BEFORE this StoreCog is loaded. Please check your cog loading order and GamesCog setup."
        )
        # To prevent the bot from fully crashing here, but StoreCog will be non-functional for economy.
        # It's better to raise an error to make the problem obvious.
        raise RuntimeError("EconomyManager dependency not met for StoreCog. Ensure GamesCog or main bot setup provides bot.economy_manager.")

    store_dir = os.path.dirname(getattr(config, 'STORE_FILE_PATH', 'data/store.json'))
    if store_dir and not os.path.exists(store_dir):
        try:
            os.makedirs(store_dir, exist_ok=True)
            logger.info(f"Created directory for store file: {store_dir}")
        except OSError as e:
            logger.error(f"Could not create directory {store_dir} for store file: {e}")

    await bot.add_cog(StoreCog(bot)) 
    logger.info("StoreCog has been setup and added to the bot.")

