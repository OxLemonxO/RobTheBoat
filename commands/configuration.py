from discord.ext import commands
from utils.mysql import *
from utils.tools import *
from utils.config import Config
config = Config()

class Configuration():
    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True)
    async def config(self, ctx, type:str, *, value:str):
        """Modifies the server's local config"""
        if ctx.guild.author is not ctx.guild.server.owner:
            await ctx.send("Only my otp the server owner aka {} can use this command.".format(format_user(ctx.guild.server.owner)))
            return
        await ctx.channel.trigger_typing()
        if type == "mod-role" or type == "nsfw-channel" or type == "mute-role":
            if type == "nsfw-channel":
                value = value.lower().strip(" ")
            update_data_entry(ctx.guild.id, type, value)
            await ctx.send("Set the {} with value `{}`".format(type, value))
        else:
            await ctx.send("`{}` isn't a valid type. The only types available are mod-role, nsfw-channel, and mute-role.".format(type))

    @commands.command(pass_context=True)
    async def cfgbypass(self, ctx, type:str, *, value:str):
        """Modifies the server's local config (bot owner bypass)"""
        if ctx.guild.author.id != int(config.owner_id):
            await ctx.send("Back off. Only my masters can use this.")
            return
        await ctx.channel.trigger_typing()
        if type == "mod-role" or type == "nsfw-channel" or type == "mute-role":
            if type == "nsfw-channel":
                value = value.lower().strip(" ")
            update_data_entry(ctx.guild.id, type, value)
            await ctx.send("Set the {} with value `{}`.".format(type, value))
        else:
            await ctx.send("`{}` isn't a valid type. The only types available are mod-role, nsfw-channel, and mute-role.".format(type))

    @commands.command(pass_context=True)
    async def showconfig(self, ctx):
        """Shows the server's configuration"""
        await ctx.channel.trigger_typing()
        mod_role_name = read_data_entry(ctx.guild.id, "mod-role")
        nsfw_channel_name = read_data_entry(ctx.guild.id, "nsfw-channel")
        mute_role_name = read_data_entry(ctx.guild.id, "mute-role")
        em = discord.Embed(description="\u200b")
        em.color = ctx.message.server.me.color
        em.title = "Server Configuration for " + ctx.guild.server.name
        em.add_field(name='Mod Role Name', value=mod_role_name)
        em.add_field(name='NSFW Channel Name', value=nsfw_channel_name)
        em.add_field(name='Mute Role Name', value=mute_role_name)
        await ctx.send(embed=em)

    @commands.command(pass_context=True)
    async def joinleave(self, ctx, type:str, *, value:str):
        """Configures on user join and leave settings"""
        if ctx.guild.author is not ctx.guild.server.owner:
            await ctx.send("Only the server owner (`{}`) can use this command.".format(format_user(ctx.guild.server.owner)))
            return
        await ctx.channel.trigger_typing()
        if type == "join-message":
            update_data_entry(ctx.guild.id, type, value)
            await ctx.send("Successfully set the join message to: {}".format(value.replace("%user%", "@{}".format(ctx.guild.author.name)).replace("!SERVER!", ctx.guild.server.name)))
        elif type == "leave-message":
            update_data_entry(ctx.guild.id, type, value)
            await ctx.send("Successfully set the leave message to: {}".format(value.replace("%user%", "@{}".format(ctx.guild.author.name)).replace("!SERVER!", ctx.guild.server.name)))
        elif type == "join-leave-channel":
            if value == "remove":
                update_data_entry(ctx.guild.id, type, None)
                await ctx.send("Successfully disabled join-leave messages")
                return
            channel = discord.utils.get(ctx.guild.channels, name=value)
            if channel is None:
                await ctx.send("There is no channel on this server named `{}`".format(value))
                return
            update_data_entry(ctx.guild.id, type, channel.id)
            await ctx.send("Successfully set the join-leave-channel to: {}".format(channel.mention))
        elif type == "join-role":
            if value == "remove":
                update_data_entry(ctx.guild.id, type, None)
                await ctx.send("Successfully disabled the join-role")
                return
            role = discord.utils.get(ctx.guild.roles, name=value)
            if role is None:
                await ctx.send("There is no role on this server named `{}`".format(value))
                return
            update_data_entry(ctx.guild.id, type, role.id)
            await ctx.send("Successfully set the join-role to: {}".format(role.name))

    @commands.command(pass_context=True)
    async def showjoinleaveconfig(self, ctx):
        """Shows the on user join and leave config"""
        join_message = read_data_entry(ctx.guild.id, "join-message")
        if join_message is not None:
            join_message = join_message.replace("%user%", "@{}".format(ctx.guild.author.name)).replace("!SERVER!", ctx.guild.server.name)
        leave_message = read_data_entry(ctx.guild.id, "leave-message")
        if leave_message is not None:
            leave_message = leave_message.replace("%user%", "@{}".format(ctx.guild.author.name)).replace("!SERVER!", ctx.guild.server.name)
        join_leave_channel_id = read_data_entry(ctx.guild.id, "join-leave-channel")
        if join_leave_channel_id is not None:
            join_leave_channel = discord.utils.get(ctx.guild.channels, id=join_leave_channel_id).name
            if join_leave_channel is None:
                update_data_entry(ctx.guild.id, "join-leave-channel", None)
        else:
            join_leave_channel = None
        join_role_id = read_data_entry(ctx.guild.id, "join-role")
        if join_role_id is not None:
            join_role = discord.utils.get(ctx.guild.roles, id=join_role_id).name
            if join_role is None:
                update_data_entry(ctx.guild.id, "join-role", None)
        else:
            join_role = None
        msg = "```Join message: {}\nLeave message: {}\nJoin leave channel: {}\nJoin role: {}```".format(join_message, leave_message, join_leave_channel, join_role)
        await ctx.send(msg)


def setup(bot):
    bot.add_cog(Configuration(bot))
