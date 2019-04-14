import discord

from utils import checks
from discord.ext import commands

class Terminal(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @checks.is_terminal_existent()
    @commands.command(aliases=['robin', 'pensivr'])
    async def pensive(self, ctx):
        """pensivr"""
        await ctx.send("<@117678528220233731> <@372078453236957185> terminal is dead :crab:")
    
    @checks.is_terminal_existent()
    @commands.command(aliases=['emoeuropean'])
    async def epic(self, ctx):
        """bruh"""
        await ctx.send("ok... now THIS is epic...")

def setup(bot):
    bot.add_cog(Terminal(bot))
