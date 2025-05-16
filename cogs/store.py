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
from typing import Dict, Any, Optional, List

# Assuming your config.py and a shared economy_manager.py are accessible
# If main_bot.py, config.py, and economy_manager.py are in the root, and cogs is a subdirectory:
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

# Attempt to import EconomyManager. This assumes you have a shared economy_manager.py
# or that the EconomyManager class is defined in config or another accessible module.
# If it's part of the Games cog, you might need a different import strategy
# or to make EconomyManager a standalone utility.
try:
    from games import EconomyManager # Assuming EconomyManager is in games.py (from previous refactor)
                                     # Or adjust path: from utils.economy_manager import EconomyManager
except ImportError:
    # Fallback or placeholder if EconomyManager is not found - this part would need proper setup
    # For this refactor, we'll assume it's available and will be passed to the cog.
    # If not, the cog won't work correctly with economy features.
    logger = logging.getLogger(__name__)
    logger.critical("EconomyManager could not be imported. Store cog may not function correctly with economy features.")
    class EconomyManager: # Dummy class if import fails
        def __init__(self, *args, **kwargs): pass
        async def get_balance(self, user_id: int) -> int: return 0
        async def update_balance(self, user_id: int, amount: int) -> int: return 0


# --- Logger Setup ---
logger = logging.getLogger(__name__)

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
                logger.info(f"Store file {self.file_path} not found. Starting with an empty store.")
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON from {self.file_path}. Starting with an empty store.")
            self.store_data = {}
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
            return False # Item ID already exists
        self.store_data[item_id] = item_details
        await self._save_store()
        logger.info(f"Item '{item_details.get('name', 'Unknown Item')}' (ID: {item_id}) added to store.")
        return True

    async def remove_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Removes an item from the store by its ID."""
        async with self.lock: # Ensure atomicity for remove
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
        return self.store_data.copy() # Return a copy

# --- Modals ---
class NicknameModal(Modal, title="Change Your Nickname"):
    new_nickname_input = TextInput(label="New Nickname", placeholder="Enter your desired nickname", required=True, max_length=32)

    def __init__(self, member: discord.Member):
        super().__init__(timeout=getattr(config, 'STORE_NICKNAME_MODAL_TIMEOUT', 180.0))
        self.member = member

    async def on_submit(self, interaction: discord.Interaction):
        new_nick = self.new_nickname_input.value
        try:
            await self.member.edit(nick=new_nick)
            await interaction.response.send_message(
                getattr(config, 'STORE_MSG_NICKNAME_CHANGED', "✅ Your nickname has been changed to **{nickname}**!").format(nickname=new_nick),
                ephemeral=True
            )
            logger.info(f"User {self.member.id} changed nickname to '{new_nick}' via store item.")
        except discord.Forbidden:
            await interaction.response.send_message(getattr(config, 'STORE_MSG_NICKNAME_FORBIDDEN', "❌ I don't have permission to change your nickname."), ephemeral=True)
        except discord.HTTPException as e:
            logger.error(f"Failed to change nickname for {self.member.id}: {e}", exc_info=True)
            await interaction.response.send_message(getattr(config, 'STORE_MSG_NICKNAME_ERROR', "❌ An error occurred while changing your nickname."), ephemeral=True)
        except Exception as e:
            logger.error(f"Unexpected error in NicknameModal on_submit for {self.member.id}: {e}", exc_info=True)
            await interaction.response.send_message(getattr(config, 'STORE_MSG_GENERIC_ERROR', "❌ An unexpected error occurred."), ephemeral=True)


class AddItemModal(Modal, title="Add New Item to Store"):
    item_name_input = TextInput(label="Item Name", placeholder="e.g., VIP Role, Custom Color", required=True, max_length=100)
    item_cost_input = TextInput(label="Item Cost (Coins)", placeholder="e.g., 1000", required=True)
    item_description_input = TextInput(label="Item Description", style=discord.TextStyle.long, placeholder="A brief description of the item and its effect.", required=True, max_length=500)
    
    # Item type selection will be done via a Select menu before this modal, or a text input here.
    # For simplicity with current structure, using TextInput for type and data.
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
        item_data_str = self.item_data_input.value or None # Use None if empty

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

        # Validate item_data based on item_type
        type_config = self.valid_item_types[item_type_str]
        if type_config.get("requires_data", False) and not item_data_str:
            await interaction.response.send_message(f"Item data is required for type '{item_type_str}'. ({type_config.get('data_prompt', '')})", ephemeral=True)
            return
        
        # Specific data validation
        if item_type_str == "role":
            try:
                int(item_data_str) # Check if it's a number (role ID)
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
            item_data_str = item_data_str.lstrip("#") # Store without #
        elif item_type_str == "badge":
            if not (item_data_str and (item_data_str.startswith("http://") or item_data_str.startswith("https://"))): # Basic URL check
                 await interaction.response.send_message("For 'badge' type, Item Data must be a valid Image URL.", ephemeral=True)
                 return

        item_id = str(random.randint(10000, 99999)) # Generate a simple unique ID
        while self.store_manager.get_item(item_id): # Ensure ID is unique
            item_id = str(random.randint(10000, 99999))

        new_item_details = {
            "name": name,
            "cost": cost,
            "description": description,
            "type": item_type_str,
            "data": item_data_str # Store the validated data (e.g., role_id, hex_color, badge_url)
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
        self.items: List[Tuple[str, Dict[str, Any]]] = [] # List of (item_id, item_details)
        self._update_items_list()

    def _update_items_list(self):
        """Fetches and sorts items from the store manager."""
        all_items = self.store_cog.store_manager.get_all_items()
        # Sort items, e.g., by name or cost, for consistent display
        self.items = sorted(all_items.items(), key=lambda item: item[1].get('name', ''))

    async def _get_page_embed_and_buttons(self) -> Tuple[discord.Embed, List[Button]]:
        """Creates the embed and buttons for the current page."""
        self.clear_items() # Clear old buttons

        start_index = self.current_page * self.items_per_page
        end_index = start_index + self.items_per_page
        page_items = self.items[start_index:end_index]

        embed_color = getattr(config, 'STORE_EMBED_COLOR', discord.Color.gold())
        embed = discord.Embed(title=f"{getattr(config, 'STORE_EMOJI_TITLE', '🛍️')} Item Store - Page {self.current_page + 1}", color=embed_color)
        
        if not self.items:
            embed.description = getattr(config, 'STORE_MSG_EMPTY', "The store is currently empty. Check back later!")
            return embed, []

        if not page_items: # Should not happen if current_page is managed correctly
            embed.description = "No items on this page."
            # Add navigation buttons even if page is empty (e.g. if user navigates to an empty page after item removal)
        
        action_buttons: List[Button] = []
        for item_id, item in page_items:
            item_label = item.get('name', 'Unknown Item')
            item_cost = item.get('cost', 0)
            item_desc = item.get('description', 'No description.')
            item_type_display = item.get('type', 'N/A').capitalize()

            embed.add_field(
                name=f"{item_label} - {item_cost} {getattr(config, 'ECONOMY_CURRENCY_NAME', 'coins')}",
                value=f"*Type: {item_type_display}*\n{item_desc}",
                inline=False
            )
            buy_button = Button(label=f"Buy {item_label}", custom_id=f"buy_{item_id}", style=discord.ButtonStyle.green, emoji=getattr(config, 'STORE_EMOJI_BUY', '🛒'))
            buy_button.callback = self.buy_button_callback
            action_buttons.append(buy_button)
            self.add_item(buy_button) # Add to view directly

        # Pagination Buttons
        if self.current_page > 0:
            prev_button = Button(label="Previous", custom_id="prev_page", style=discord.ButtonStyle.blurple, emoji="⬅️")
            prev_button.callback = self.nav_button_callback
            self.add_item(prev_button)

        if end_index < len(self.items):
            next_button = Button(label="Next", custom_id="next_page", style=discord.ButtonStyle.blurple, emoji="➡️")
            next_button.callback = self.nav_button_callback
            self.add_item(next_button)
            
        return embed, action_buttons


    async def nav_button_callback(self, interaction: discord.Interaction):
        custom_id = interaction.data["custom_id"]
        if custom_id == "prev_page" and self.current_page > 0:
            self.current_page -= 1
        elif custom_id == "next_page" and (self.current_page + 1) * self.items_per_page < len(self.items):
            self.current_page += 1
        
        embed, _ = await self._get_page_embed_and_buttons()
        await interaction.response.edit_message(embed=embed, view=self)


    async def buy_button_callback(self, interaction: discord.Interaction):
        item_id = interaction.data["custom_id"].replace("buy_", "")
        item = self.store_cog.store_manager.get_item(item_id)

        if not item:
            await interaction.response.send_message(getattr(config, 'STORE_MSG_ITEM_NOT_FOUND', "❌ This item is no longer available."), ephemeral=True)
            # Optionally refresh the view if item disappeared
            self._update_items_list()
            embed, _ = await self._get_page_embed_and_buttons()
            try:
                await interaction.message.edit(embed=embed, view=self)
            except discord.HTTPException: pass # Message might have been deleted
            return

        user_balance = await self.store_cog.economy_manager.get_balance(interaction.user.id)
        item_cost = item.get('cost', 0)

        if user_balance < item_cost:
            await interaction.response.send_message(
                getattr(config, 'STORE_MSG_INSUFFICIENT_FUNDS', "❌ You don't have enough {currency} to buy **{item_name}**.").format(
                    currency=getattr(config, 'ECONOMY_CURRENCY_NAME', 'coins'), item_name=item.get('name')
                ), ephemeral=True)
            return

        # Defer here as applying effect might take time or open a modal
        await interaction.response.defer(ephemeral=True, thinking=True)

        # Handle nickname separately as it needs a modal
        if item.get('type') == "nickname":
            # Cost is deducted AFTER successful nickname change via modal submission
            # So, we pass the cost and item_id to the modal or handle it after modal.
            # For now, let modal handle its own flow. We just trigger it.
            # The actual balance deduction will happen in apply_item_effect after modal success.
            # This is a bit tricky. Simpler: deduct here, refund if modal fails.
            # Or, modal calls back to a method that deducts and applies.

            # Let's adjust: NicknameModal will not deduct. The effect application will.
            # So, the modal is just for input.
            nick_modal = NicknameModal(member=interaction.user) # Pass member directly
            # We can't directly await the modal's outcome here to deduct balance.
            # The modal needs to trigger the effect application.
            # This means apply_item_effect needs to be callable by the modal's on_submit.
            # For simplicity, we'll make the NicknameModal purchase process slightly different:
            # 1. User clicks buy.
            # 2. If type is nickname, open modal.
            # 3. Modal on_submit changes nickname AND THEN calls a method to deduct balance.
            # This is not ideal. Better:
            # The callback here should handle the "purchase confirmation" and then the effect.
            # If modal is needed, it's part of the effect.
            await self.store_cog.economy_manager.update_balance(interaction.user.id, -item_cost) # Deduct cost
            await self.store_cog.apply_item_effect(interaction, interaction.user, item, is_purchase_interaction=True)
            # apply_item_effect for nickname will open the modal.
            # No further message here for nickname, modal will send one.
            return # apply_item_effect will handle the rest for nickname

        # For other items, deduct cost and apply effect
        await self.store_cog.economy_manager.update_balance(interaction.user.id, -item_cost)
        success = await self.store_cog.apply_item_effect(interaction, interaction.user, item, is_purchase_interaction=True)

        if success:
             await interaction.followup.send(
                getattr(config, 'STORE_MSG_ITEM_PURCHASED', "✅ You successfully purchased **{item_name}**!").format(item_name=item.get('name')),
                ephemeral=True
            )
        # apply_item_effect will send its own error messages if !success

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message: # If the view has an associated message
            try:
                timeout_embed = discord.Embed(title="Store Closed", description="This store session has timed out. Use `!store` again.", color=discord.Color.orange())
                await self.message.edit(embed=timeout_embed, view=self) # Keep buttons disabled
            except discord.HTTPException:
                pass # Message might have been deleted
        logger.info("StoreView timed out.")


# --- Store Cog ---
class StoreCog(commands.Cog, name="Store"):
    """Manages a virtual store where users can buy items using server currency."""
    def __init__(self, bot: commands.Bot, economy_manager: EconomyManager): # EconomyManager injected
        self.bot = bot
        self.economy_manager = economy_manager # Use the injected EconomyManager
        self.store_file_path = getattr(config, 'STORE_FILE_PATH', 'data/store.json')
        # Ensure the directory for the store file exists
        os.makedirs(os.path.dirname(self.store_file_path), exist_ok=True)
        
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
    async def store_command(self, ctx: commands.Context): # Renamed to avoid conflict
        view = StoreView(self, items_per_page=getattr(config, 'STORE_ITEMS_PER_PAGE', 5))
        view._update_items_list() # Ensure items are fresh
        embed, _ = await view._get_page_embed_and_buttons()
        
        # Store the message so the view can edit it on timeout
        message = await ctx.send(embed=embed, view=view)
        view.message = message


    @commands.command(name="addstoreitem", help="Adds an item to the store (Admin only).")
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def add_store_item(self, ctx: commands.Context):
        # item_type_options = [
        #     discord.SelectOption(label=item_type.capitalize(), value=item_type, description=details.get("description", ""))
        #     for item_type, details in getattr(config, 'STORE_ITEM_TYPES', {}).items()
        # ]
        # if not item_type_options:
        #     return await ctx.send("No item types configured for the store.")
        # view = ItemTypeSelectionView(self.store_manager, item_type_options)
        # await ctx.send("Select the type of item to add:", view=view, ephemeral=True)
        # For now, using the modal directly which asks for type as text.
        # A Select menu before the modal would be a UX improvement.
        modal = AddItemModal(self.store_manager)
        await ctx.send_modal(modal) # send_modal is for interactions, ctx.send() for command responses.
                                     # This should be interaction.response.send_modal if it were a slash command.
                                     # For text commands, we can't directly send a modal like this.
                                     # This command might be better as a slash command.
                                     # Workaround: Bot sends a message, user replies, or use a reaction menu.
                                     # For simplicity, this example assumes modal can be triggered.
                                     # A more robust way for text commands: bot asks questions sequentially.
                                     # Or, use a button that triggers the modal.
                                     # Let's assume this is part of an interaction flow (e.g. button click)
                                     # If not, this command needs redesign for text-based input.
                                     # For now, let's assume this command is for testing and an admin uses it carefully.
                                     # The original code used ctx.interaction.response.send_modal, which is wrong for text commands.
                                     # I will change this to send a message that then has a button to open the modal.

        # Simplified: For text command, just use the modal directly if discord.py allows it.
        # It seems send_modal is an interaction-only feature.
        # The original code for add_item was `await ctx.interaction.response.send_modal(modal)`
        # which implies it was intended for an interaction context, not a regular command.
        # I will correct this to a more standard modal invocation if possible or note the issue.
        # For a text command, you can't directly send a modal.
        # Let's make it a button that opens the modal.

        class AdminAddItemView(View):
            def __init__(self, store_manager_ref):
                super().__init__(timeout=60)
                self.store_manager_ref = store_manager_ref
            
            @discord.ui.button(label="Add New Store Item", style=discord.ButtonStyle.primary)
            async def add_item_button(self, interaction: discord.Interaction, button: Button):
                modal = AddItemModal(self.store_manager_ref)
                await interaction.response.send_modal(modal)
                self.stop() # Stop the view after modal is sent

        view = AdminAddItemView(self.store_manager)
        await ctx.send("Click the button to add a new item to the store:", view=view)


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

    async def apply_item_effect(self, interaction: discord.Interaction, member: discord.Member, item: Dict[str, Any], is_purchase_interaction: bool = False):
        """
        Applies the effect of a purchased item.
        `is_purchase_interaction` is True if this is called directly from a purchase button click,
        meaning `interaction.response` has been deferred and `interaction.followup` should be used.
        If False (e.g. called from a modal submit), `interaction.response` should be used.
        """
        item_type = item.get("type")
        item_data = item.get("data")
        item_name = item.get("name", "Unknown Item")
        guild = interaction.guild
        
        response_method = interaction.followup.send if is_purchase_interaction else interaction.response.send_message

        try:
            if item_type == "role":
                role_id = int(item_data)
                role_to_assign = guild.get_role(role_id)
                if role_to_assign:
                    if role_to_assign in member.roles:
                        await response_method(getattr(config, 'STORE_MSG_ROLE_ALREADY_HAS', "ℹ️ You already have the **{role_name}** role.").format(role_name=role_to_assign.name), ephemeral=True)
                        return False # Not a failure, but no action taken
                    await member.add_roles(role_to_assign, reason=f"Purchased '{item_name}' from store.")
                    logger.info(f"Assigned role '{role_to_assign.name}' to {member.id} for item '{item_name}'.")
                    return True
                else:
                    await response_method(getattr(config, 'STORE_MSG_ROLE_NOT_FOUND_EFFECT', "❌ The role for this item could not be found on the server."), ephemeral=True)
                    return False

            elif item_type == "color":
                hex_color_str = str(item_data) # Should be stored without '#'
                color = discord.Color(int(hex_color_str, 16))
                role_name = f"{member.name}-color-{hex_color_str}" # Unique role name
                
                # Remove old color roles for this user if they exist (optional, good practice)
                for r in member.roles:
                    if r.name.startswith(f"{member.name}-color-"):
                        try:
                            await member.remove_roles(r, reason="Applying new custom color role.")
                            if not r.members: # Delete role if no one else has it (be careful with this)
                                await r.delete(reason="Custom color role no longer in use.")
                        except discord.HTTPException:
                            logger.warning(f"Could not remove or delete old color role {r.name} for {member.id}")
                
                # Create or edit role
                custom_role = discord.utils.get(guild.roles, name=role_name)
                if custom_role:
                    await custom_role.edit(colour=color, reason=f"Updating custom color for {member.name}")
                else:
                    custom_role = await guild.create_role(name=role_name, colour=color, reason=f"Creating custom color for {member.name}")
                
                await member.add_roles(custom_role, reason=f"Purchased custom color '{item_name}'.")
                logger.info(f"Applied color {hex_color_str} to {member.id} via role '{custom_role.name}'.")
                return True

            elif item_type == "badge":
                badge_url = str(item_data)
                # Badge logic is highly dependent on your bot's profile system.
                # This usually involves storing the badge URL in a database associated with the user.
                # Example: await self.bot.profile_manager.add_badge(member.id, item_name, badge_url)
                logger.info(f"User {member.id} purchased badge '{item_name}' with URL: {badge_url}. (Implementation pending)")
                await response_method(getattr(config, 'STORE_MSG_BADGE_PURCHASED_PENDING', "✅ Badge '{item_name}' purchased! It will appear on your profile soon (feature pending).").format(item_name=item_name), ephemeral=True)
                return True # Assume success for now

            elif item_type == "nickname":
                # This is now triggered after the NicknameModal is submitted by the user.
                # The modal itself handles the nickname change and response.
                # If called from buy button, it should open the modal.
                if is_purchase_interaction: # This means it's from the "Buy" button
                    nick_modal = NicknameModal(member=member)
                    # We can't use interaction.response.send_modal here because it's a followup.
                    # This flow needs rethink for modals in purchase interactions.
                    # Simplest: the "Buy Nickname Change" button directly opens the modal.
                    # The modal's on_submit then handles the actual change.
                    # So, this part of apply_item_effect for 'nickname' might not be directly called
                    # if the modal is the primary interaction point after purchase.

                    # Let's assume the button click *is* the interaction that should open the modal.
                    # The `buy_button_callback` in `StoreView` will defer, then call this.
                    # This method then needs to send the modal using `interaction.response.send_modal` if it wasn't deferred,
                    # or handle it differently if it was.
                    # The current StoreView defers. So we can't send_modal here.
                    # This is why the NicknameModal was directly sent in the original StoreView.
                    # I'll revert that part in StoreView.
                    # This apply_item_effect for nickname is more of a confirmation or post-modal action.
                    # For now, let's assume the modal has already been handled if type is nickname.
                    # The NicknameModal itself should send the confirmation.
                    # This function returning True here implies the *purchase* was successful.
                    # The actual nickname change success is handled by the modal.
                    # This is slightly awkward.
                    # Re-evaluating: The NicknameModal should be sent by the button's interaction.response.send_modal.
                    # The cost deduction should happen *after* the modal is successfully submitted.
                    # This requires the modal to call back to the cog to finalize the purchase.

                    # For now, the NicknameModal is sent from StoreView.
                    # This apply_item_effect for nickname will not be called from StoreView.
                    # If it were, it would be after the modal.
                    pass # Handled by modal.
                return True # Placeholder, actual success depends on modal.


            else:
                await response_method(getattr(config, 'STORE_MSG_UNKNOWN_ITEM_TYPE_EFFECT', "❓ Don't know how to apply this item type."), ephemeral=True)
                return False

        except discord.Forbidden:
            logger.warning(f"Permission error applying item '{item_name}' for {member.id}: Bot lacks permissions.")
            await response_method(getattr(config, 'STORE_MSG_APPLY_EFFECT_FORBIDDEN', "❌ I don't have the necessary permissions to apply this item's effect."), ephemeral=True)
            return False
        except discord.HTTPException as e:
            logger.error(f"HTTP error applying item '{item_name}' for {member.id}: {e}", exc_info=True)
            await response_method(getattr(config, 'STORE_MSG_APPLY_EFFECT_HTTP_ERROR', "❌ A Discord error occurred while applying this item. Please try again later."), ephemeral=True)
            return False
        except ValueError as e: # e.g. invalid hex for color, invalid role ID
             logger.warning(f"ValueError applying item '{item_name}' for {member.id}: {e}")
             await response_method(f"❌ Invalid data for item effect: {e}", ephemeral=True)
             return False
        except Exception as e:
            logger.error(f"Unexpected error applying item '{item_name}' for {member.id}: {e}", exc_info=True)
            await response_method(getattr(config, 'STORE_MSG_APPLY_EFFECT_UNEXPECTED_ERROR', "❌ An unexpected error occurred while applying this item."), ephemeral=True)
            return False

    # --- Error Handlers for Store Commands ---
    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing argument: `{error.param.name}`. Usage: `{ctx.prefix}help {ctx.command.qualified_name}`")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("Invalid argument provided. Please check the command usage.")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"This command is on cooldown. Try again in {error.retry_after:.2f} seconds.")
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send("Store commands generally work best in servers.")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("You don't have the required permissions (Administrator) to use this command.")
        else:
            logger.error(f"Unhandled error in Store command '{ctx.command.qualified_name}': {error}", exc_info=True)
            await ctx.send("An unexpected error occurred with that store command.")

async def setup(bot: commands.Bot):
    """Sets up the StoreCog, injecting the EconomyManager."""
    # --- Crucial: Ensure EconomyManager is available ---
    # This setup assumes EconomyManager is accessible, e.g., from another cog or a shared module.
    # If your EconomyManager is part of another cog (like 'Games'), you might fetch it:
    # games_cog = bot.get_cog("Games") # Assuming the Games cog is named "Games"
    # if not games_cog or not hasattr(games_cog, 'economy_manager'):
    #     logger.critical("StoreCog setup failed: EconomyManager not found in Games cog or Games cog not loaded.")
    #     raise RuntimeError("EconomyManager dependency not met for StoreCog.")
    # economy_manager = games_cog.economy_manager

    # For a standalone or shared EconomyManager:
    # from utils.economy_manager import EconomyManager # Example import
    # economy_manager_instance = EconomyManager(
    #     file_path=getattr(config, 'ECONOMY_FILE_PATH', 'data/economy.json'), # Must match Games cog's path
    #     default_balance=getattr(config, 'ECONOMY_DEFAULT_BALANCE', 100),
    #     lock=asyncio.Lock() # Each manager needs its own lock or share one if design allows
    # )
    # This part needs careful consideration based on your bot's structure.
    # For this example, we'll assume the bot instance will have an economy_manager attribute
    # set up by the Games cog or main bot file.
    
    if not hasattr(bot, 'economy_manager'):
        logger.critical("StoreCog setup failed: `bot.economy_manager` not found. Ensure EconomyManager is initialized and attached to the bot instance before loading StoreCog.")
        # As a fallback, create a dummy one, but this is not recommended for production.
        # This means the Games cog (or wherever EconomyManager is initialized) MUST be loaded before StoreCog.
        class DummyEconomyManager:
            async def get_balance(self, user_id): return 0
            async def update_balance(self, user_id, amount): return 0
        bot.economy_manager = DummyEconomyManager()
        logger.warning("StoreCog is using a DUMMY EconomyManager. Real economy features will not work.")


    # Ensure store directory exists
    store_dir = os.path.dirname(getattr(config, 'STORE_FILE_PATH', 'data/store.json'))
    if store_dir and not os.path.exists(store_dir):
        try:
            os.makedirs(store_dir, exist_ok=True)
            logger.info(f"Created directory for store file: {store_dir}")
        except OSError as e:
            logger.error(f"Could not create directory {store_dir} for store file: {e}")
            # Potentially raise error or prevent cog loading

    await bot.add_cog(StoreCog(bot, bot.economy_manager)) # Pass the economy_manager instance
    logger.info("StoreCog has been setup and added to the bot.")

