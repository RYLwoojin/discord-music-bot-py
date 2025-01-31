import discord
from discord.ext import commands
import yt_dlp
import asyncio
import token1
import youtube_dl

intents = discord.Intents.default()
intents.message_content = True  # message reading access 
bot = commands.Bot(command_prefix="!", intents=intents)
queue = []

#  yt dl option
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
    'source_address': '0.0.0.0'  # ipv6 problem prevent
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
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

def play_next(ctx):
    if queue and ctx.voice_client:
        url = queue.pop(0)
        FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
        YDL_OPTIONS = {'format': 'bestaudio'}
        with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(url, download=False)
            url2 = info['url']
            source = discord.FFmpegOpusAudio.from_probe(url2, **FFMPEG_OPTIONS)
            ctx.voice_client.play(source, after=lambda e: play_next(ctx))


# command
@bot.command(name="play")
async def play(ctx, url: str):
    if not ctx.message.author.voice:
        await ctx.send("먼저 음성 채널에 입장해야 합니다.")
        return

    channel = ctx.message.author.voice.channel
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    if not voice_client:
        voice_client = await channel.connect()

    async with ctx.typing():
        player = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
        if ctx.voice_client.is_playing():
            queue.append(url)
            await ctx.send(f"현재 음악이 재생 중입니다. 대기열에 추가됨: {player.title}")
        else:
            voice_client.play(player, after=lambda e: play_next(ctx))
            await ctx.send(f'재생 중: {player.title}')

@bot.command(name="stop")
async def stop(ctx):
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    
    if voice_client and voice_client.is_connected():
        await voice_client.disconnect()
        await ctx.send("음악을 멈추고 봇이 퇴장했습니다.")
    else:
        await ctx.send("봇이 음성 채널에 있지 않습니다.")

@bot.command(name="list")
async def waitlist(ctx):
    if queue:
        await ctx.send("대기열: " + "\n".join(queue))
    else:
        await ctx.send("현재 대기열이 비어 있습니다.")
        
@bot.command(name="skip")
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()  
        play_next(ctx)  
        await ctx.send("현재 곡을 스킵했습니다.")
    else:
        await ctx.send("현재 재생 중인 곡이 없습니다.")
        
# 토큰으로 봇 실행
bot.run(token1.tokenval)