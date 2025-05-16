import discord
from discord.ext import commands

class VoiceKick(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='vckick', aliases=['voicekick'])
    @commands.is_owner()
    @commands.bot_has_permissions(move_members=True)
    async def vckick_command(self, ctx, member: discord.Member):
        """Owner-only silent voice kick"""
        try:
            await ctx.message.delete()
        except:
            pass
        
        if member == self.bot.user:
            return
        
        try:
            await member.move_to(None)
        except:
            pass

async def setup(bot):
    await bot.add_cog(VoiceKick(bot))