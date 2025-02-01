import asyncio
import discord.opus

if not discord.opus.is_loaded():
    discord.opus.load_opus("/opt/homebrew/lib/libopus.dylib")

import discord
import yt_dlp
from discord.ext import commands

import token1

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
queue = []

# yt-dlp option
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl_format_options = {
    'format': 'bestaudio/best',
    'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'opus', 'preferredquality': '192'}],
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'noplaylist': True,
    'quiet': True
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')


async def play_next(ctx):
    if queue and ctx.voice_client:
        url = queue.pop(0)
        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
            ctx.voice_client.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
        await ctx.send(f'Now playing: {player.title}')


@bot.command(name="play")
async def play(ctx, url: str):
    if not ctx.message.author.voice:
        await ctx.send("You must join a voice channel first.")
        return

    channel = ctx.message.author.voice.channel
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    if not voice_client:
        voice_client = await channel.connect()


    async with ctx.typing():
        player = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
        if ctx.voice_client.is_playing():
            queue.append(url)
            await ctx.send(f"A song is already playing. Added to queue: {player.title}")
        else:
            ctx.voice_client.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
            await ctx.send(f'Now playing :{player.title}')


@bot.command(name="stop")
async def stop(ctx):
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    if voice_client and voice_client.is_connected():
        await voice_client.disconnect()
        await ctx.send("Stopped music and disconnected the bot.")
    else:
        await ctx.send("The bot is not in a voice channel.")


@bot.command(name="list")
async def waitlist(ctx):
    if queue:
        await ctx.send("Queue: " + "\n".join(queue))
    else:
        await ctx.send("The queue is currently empty.")



@bot.command(name="skip")
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("Skipped the current song.")

    else:
        await ctx.send("No song is currently playing..")

@bot.command(name="quit")
async def quitChat(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("Goodbye!")

bot.run(token1.tokenval)
