# cogs/help.py
"""
A custom help command cog for the Discord bot.
Provides a more detailed and user-friendly help interface.
"""
import discord
from discord.ext import commands
import logging
from typing import List, Optional, Mapping, Union
import os
# Ensure the config module is imported correctly

# Assuming your config.py is in the parent directory
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

logger = logging.getLogger(__name__)

class CustomHelpCommand(commands.HelpCommand):
    """Custom help command override."""

    def __init__(self):
        super().__init__(command_attrs={
            'help': 'Shows this help message.',
            'aliases': ['h', 'commands']
        })
        self.command_prefix = getattr(config, 'COMMAND_PREFIX', '!') # Get prefix from config

    async def send_bot_help(self, mapping: Mapping[Optional[commands.Cog], List[commands.Command]]):
        """Sends help for all commands, grouped by cog."""
        ctx = self.context
        embed_color = getattr(config, 'HELP_EMBED_COLOR', discord.Color.blue()) # Configurable color
        embed = discord.Embed(title=f"{getattr(config, 'BOT_NAME', 'Bot')} Commands",
                              description=f"Use `{self.command_prefix}help [command]` or `{self.command_prefix}help [category]` for more info.",
                              color=embed_color)

        # Filter out cogs with no commands or commands that shouldn't be shown
        filtered_mapping = {}
        for cog, cog_commands in mapping.items():
            # Filter out hidden commands and checks failed commands
            # Also filter out commands the user can't run (check permissions)
            # For simplicity, this example doesn't do extensive permission checks here,
            # but relies on command checks.
            # command.can_run(ctx) would be more thorough but can be slow for many commands.
            
            # Filter out commands that are hidden or the user cannot run
            # For simplicity, we'll just filter hidden ones for now.
            # A more robust check would involve `cmd.can_run(ctx)`
            usable_commands = [c for c in cog_commands if not c.hidden]
            if usable_commands:
                 # Use cog.qualified_name or a custom attribute for display name
                cog_name = cog.qualified_name if cog else "No Category"
                if hasattr(cog, 'display_name'): # Allow cogs to define a nicer display name
                    cog_name = cog.display_name
                filtered_mapping[cog_name] = sorted(usable_commands, key=lambda c: c.name)


        for cog_name, cog_commands in sorted(filtered_mapping.items()):
            if not cog_commands:
                continue

            command_signatures = [f"`{self.command_prefix}{c.name}` - {c.short_doc or 'No description'}" for c in cog_commands]
            if command_signatures:
                embed.add_field(name=cog_name, value="\n".join(command_signatures), inline=False)

        channel = self.get_destination()
        await channel.send(embed=embed)

    async def send_cog_help(self, cog: commands.Cog):
        """Sends help for a specific cog."""
        embed_color = getattr(config, 'HELP_EMBED_COLOR', discord.Color.blue())
        cog_display_name = cog.qualified_name
        if hasattr(cog, 'display_name'):
            cog_display_name = cog.display_name

        embed = discord.Embed(title=f"{cog_display_name} Commands",
                              description=cog.description or "No description for this category.",
                              color=embed_color)

        # Filter out hidden commands
        cog_commands = [c for c in cog.get_commands() if not c.hidden]

        if not cog_commands:
            embed.description = "No available commands in this category."
        else:
            for command in sorted(cog_commands, key=lambda c: c.name):
                embed.add_field(name=f"{self.command_prefix}{command.name} {command.signature}",
                                value=command.short_doc or command.help or "No detailed help.",
                                inline=False)

        channel = self.get_destination()
        await channel.send(embed=embed)

    async def send_group_help(self, group: commands.Group):
        """Sends help for a command group."""
        embed_color = getattr(config, 'HELP_EMBED_COLOR', discord.Color.blue())
        embed = discord.Embed(title=f"Help for Group: {self.command_prefix}{group.qualified_name}",
                              description=group.help or group.short_doc or "No description for this group.",
                              color=embed_color)

        embed.add_field(name="Usage", value=f"`{self.command_prefix}{group.qualified_name} {group.signature}`", inline=False)

        if group.aliases:
            embed.add_field(name="Aliases", value=", ".join(f"`{alias}`" for alias in group.aliases), inline=False)

        # Filter out hidden subcommands
        subcommands = [c for c in group.commands if not c.hidden]
        if subcommands:
            sub_command_help = []
            for subcommand in sorted(subcommands, key=lambda c: c.name):
                sub_command_help.append(f"`{self.command_prefix}{subcommand.qualified_name}` - {subcommand.short_doc or 'No description'}")
            embed.add_field(name="Subcommands", value="\n".join(sub_command_help), inline=False)

        channel = self.get_destination()
        await channel.send(embed=embed)

    async def send_command_help(self, command: commands.Command):
        """Sends help for a specific command."""
        embed_color = getattr(config, 'HELP_EMBED_COLOR', discord.Color.blue())
        embed = discord.Embed(title=f"Help for Command: {self.command_prefix}{command.qualified_name}",
                              description=command.help or command.short_doc or "No detailed help available.",
                              color=embed_color)
        
        parent = command.full_parent_name
        if len(command.aliases) > 0:
            aliases = ', '.join(f"`{alias}`" for alias in command.aliases)
            embed.add_field(name="Aliases", value=aliases, inline=False)

        usage = f"{self.command_prefix}{parent} {command.name} {command.signature}".strip()
        embed.add_field(name="Usage", value=f"`{usage}`", inline=False)

        if command.description: # Add full description if available
            embed.add_field(name="Description", value=command.description, inline=False)
            
        # Cooldown information (if any)
        if command._buckets and command._buckets._cooldown:
            cooldown = command._buckets._cooldown
            per = cooldown.per
            rate = cooldown.rate
            cooldown_type = str(cooldown.type).split('.')[-1].capitalize() # e.g., User, Guild
            embed.set_footer(text=f"Cooldown: {rate} use(s) per {per:.0f} seconds ({cooldown_type})")


        channel = self.get_destination()
        await channel.send(embed=embed)

    async def send_error_message(self, error: str):
        """Sends an error message if help lookup fails."""
        embed_color = getattr(config, 'ERROR_EMBED_COLOR', discord.Color.red()) # Use a general error color
        embed = discord.Embed(title="Help Error", description=error, color=embed_color)
        channel = self.get_destination()
        await channel.send(embed=embed)

    def get_command_signature(self, command: commands.Command) -> str:
        """Returns a string representing the command's signature."""
        return f'{self.command_prefix}{command.qualified_name} {command.signature}'

class HelpCog(commands.Cog, name="Help"): # Give the cog a display name
    """Provides the custom help command."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._original_help_command = bot.help_command # Store original help command
        bot.help_command = CustomHelpCommand() # Set the custom help command
        bot.help_command.cog = self # Link the help command to this cog

    async def cog_unload(self):
        """Revert to original help command when cog is unloaded."""
        self.bot.help_command = self._original_help_command
        logger.info("HelpCog unloaded, help command reverted.")

async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCog(bot))
    logger.info("HelpCog loaded and custom help command is active.")

