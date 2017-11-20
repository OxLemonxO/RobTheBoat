import asyncio
import traceback
import shutil
import discord
import youtube_dl

from discord.ext import commands
from utils.mysql import *
from utils.logger import log
from utils.opus_loader import load_opus_lib
from utils.config import Config

load_opus_lib()
config = Config()

ytdl_format_options = {"format": "bestaudio/best", "extractaudio": True, "audioformat": "mp3", "noplaylist": True, "nocheckcertificate": True, "ignoreerrors": False, "logtostderr": False, "quiet": True, "no_warnings": True, "default_search": "auto", "source_address": "0.0.0.0", "preferredcodec": "libmp3lame"}

def get_ytdl(id):
    format = ytdl_format_options
    format["outtmpl"] = "data/music/{}/%(id)s.mp3".format(id)
    return youtube_dl.YoutubeDL(format)

class Song():
    def __init__(self, entry, path, title, duration, requester):
        self.entry = entry
        self.path = path
        self.title = title
        self.duration = duration
        self.requester = requester
        if self.duration:
            m, s = divmod(duration, 60)
            h, m = divmod(m, 60)
            self.duration = "%02d:%02d:%02d" % (h, m, s)

    def __str__(self):
        return "**{}** `[{}]`".format(self.title, self.duration)

    def title_with_requester(self):
        return "{} ({})".format(self.__str__(), self.requester)


class Queue():
    def __init__(self, bot, voice_client, text_channel):
        self.bot = bot
        self.voice_client = voice_client
        self.text_channel = text_channel
        self.play_next_song = asyncio.Event()
        self.song_list = []
        self.current = None
        self.songs = asyncio.Queue()
        self.audio_player = self.bot.loop.create_task(self.audio_change_task())
        self.skip_votes = []

    def toggle_next(self):
        self.bot.loop.call_soon_threadsafe(self.play_next_song.set())

    async def audio_change_task(self):
        while True:
            self.play_next_song.clear()
            self.current = await self.songs.get()
            log.debug("got next song")
            self.song_list.remove(str(self.current))
            self.skip_votes.clear()
            log.debug("sending msg")
            await self.text_channel.send("Now playing {}".format(self.current.title_with_requester()))
            self.voice_client.play(self.current.entry, after=lambda e: self.play_next_song.set())
            log.debug("waiting...")
            await self.play_next_song.wait()
            log.debug("passed")

class Music:
    def __init__(self, bot):
        self.bot = bot
        self.queues = {}

    def get_queue(self, ctx):
        queue = self.queues.get(ctx.guild.id)
        if queue is None:
            queue = Queue(self.bot, ctx.voice_client, ctx.channel)
            self.queues[ctx.guild.id] = queue
        return queue

    async def disconnect_all_voice_clients(self):
        queues = self.queues
        for id in queues:
            try:
                await self.queues[id].voice_client.disconnect()
                self.clear_data(id)
                del self.queues[id]
            except:
                pass

    @staticmethod
    def clear_data(id=None):
        if id is None:
            shutil.rmtree("data/music")
        else:
            shutil.rmtree("data/music/{}".format(id))

    @staticmethod
    def download_video(ctx, url):
        ytdl = get_ytdl(ctx.guild.id)
        data = ytdl.extract_info(url, download=True)
        if "entries" in data:
            data = data["entries"][0]
        title = data["title"]
        id = data["id"]
        duration = None
        # Some things like directly playing an audio file might not have duration data
        try:
            duration = data["duration"]
        except KeyError:
            pass
        path = "data/music/{}".format(ctx.guild.id)
        filepath = "{}/{}.mp3".format(path, id)
        entry = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(filepath))
        # if the volume is too high it will sound like ear rape
        entry.volume = 0.4
        song = Song(entry, path, title, duration, ctx.author)
        return song

    @commands.command()
    async def connect(self, ctx):
        await ctx.send("Summon is now defunct. Please use the .play command so I can join.")

    @commands.command()
    async def play(self, ctx, *, url:str):
        """Enqueues a song to be played"""
        queue = self.get_queue(ctx)
        await ctx.channel.trigger_typing()
        if ctx.voice_client is not None and queue is None:
            if ctx.author.voice.channel:
                try:
                    await ctx.voice_client.disconnect()
                    await ctx.author.voice.channel.connect()
                except:
                    await ctx.send("oop make sure to report this with .notifydev")
                    await ctx.send(traceback.format_exc())
                    return
            else:
                await ctx.send("You're not in a music channel, fool.")
        if ctx.voice_client is None:
            if ctx.author.voice.channel:
                try:
                    await ctx.author.voice.channel.connect()
                except discord.errors.Forbidden:
                    await ctx.send("I can't connect to this channel if I don't have any permissions for it first.")
                    return
            else:
                await ctx.send("You're not in a music channel, fool.")
                return
        url = url.strip(".play <>")# ?
        try:
            song = self.download_video(ctx, url)
        except youtube_dl.utils.DownloadError as error:
            await ctx.send("YoutubeDL broke. Error entry: {}".format(str(error.exc_info[1]).strip("[youtube] ")))
            return
        except:
            await ctx.send(traceback.format_exc())
            return
        await queue.songs.put(song)
        queue.song_list.append(str(song))
        await ctx.send("Added {} to the queue".format(song))

    @commands.command()
    async def disconnect(self, ctx):
        """Disconnects the bot from the voice channel"""
        try:
            await ctx.voice_client.disconnect()
            self.clear_data(ctx.guild.id)
            try:
                del self.queues[ctx.guild.id]
            except KeyError:
                pass
            await ctx.send("Alright, see ya.")
        except:
            await ctx.send(traceback.format_exc())

    @commands.command()
    async def pause(self, ctx):
        """Pauses the current song"""
        self.get_queue(ctx).voice_client.pause()
        await ctx.send("I paused it. Go do your thing.")

    @commands.command()
    async def resume(self, ctx):
        """Resumes playing the current song"""
        self.get_queue(ctx).voice_client.resume()
        await ctx.send("Resumed the song. Had fun doing your thing?")

    @commands.command()
    async def skip(self, ctx):
        """Skips a song"""
        queue = self.get_queue(ctx)
        if ctx.author.id in config.dev_ids or ctx.author.id == config.owner_id:
            queue.voice_client.stop()
            await ctx.send("One of my owners skipped the song.")
        elif ctx.author == queue.current.requester:
            queue.voice_client.stop()
            await ctx.send("The person who wanted to skip in the first place skipped it.")
        else:
            needed = int(4)
            channel_members = len([member for member in queue.voice_client.channel.members if not member.bot])
            if channel_members <= needed:
                needed = channel_members - 1
            if ctx.author.id not in queue.skip_votes:
                queue.skip_votes.append(ctx.author.id)
            else:
                await ctx.send("You already voted, fool. Can't vote again.")
                return
            if len(queue.skip_votes) >= int(needed):
                queue.voice_client.stop()
                await ctx.send("Song has been skipped by popular vote")
            else:
                await ctx.send("Alright, I've added your vote. There's {} votes to skip, I must have {} more.".format(len(queue.skip_votes), needed))

    @commands.command()
    async def queue(self, ctx):
        """Displays the server's song queue"""
        queue = self.get_queue(ctx)
        if queue.current:
            if not queue.voice_client.is_paused() and not queue.voice_client.is_playing():
                await ctx.send("Hmm... There's nothing in the list.")
                return
            else:
                song_list = "Now playing: {}".format(queue.current)
        else:
            await ctx.send(":thinking:... Nothing's in the queue.")
            return
        if len(queue.song_list) != 0:
            song_list += "\n\n{}".format("\n".join(queue.song_list))
        await ctx.send(song_list)

    @commands.command()
    async def volume(self, ctx, amount:float=None):
        """changes bot volume for music""" #if they fuck up, this can be gone asf
        queue = self.get_queue(ctx)
        if not amount:
            await ctx.send("The current volume is `{:.0%}`".format(queue.voice_client.source.volume))
            return
        queue.voice_client.source.volume = amount / 100
        await ctx.send("Set the internal volume to `{:.0%}`".format(queue.voice_client.source.volume))

    @commands.command()
    async def np(self, ctx):
        """Shows the song that is currently playing"""
        await ctx.send("Now playing: {}".format(self.get_queue(ctx).current.title_with_requester))

def setup(bot):
    bot.add_cog(Music(bot))