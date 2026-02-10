import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='/', intents=intents)

@bot.event
async def on_ready():
    print(f'✅ Bot conectado como {bot.user}')

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'quiet': True,
    'noplaylist': True,
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

@bot.command()
async def play(ctx, *, search: str):
    if not ctx.author.voice:
        await ctx.send("❌ Entre em um canal de voz primeiro.")
        return

    channel = ctx.author.voice.channel

    if ctx.voice_client is None:
        vc = await channel.connect()
    else:
        vc = ctx.voice_client

    await ctx.send("🔎 Procurando música...")

    loop = asyncio.get_event_loop()

    with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
        info = await loop.run_in_executor(
            None, lambda: ydl.extract_info(search, download=False)
        )

    if 'entries' in info:
        info = info['entries'][0]

    url = info['url']
    title = info.get('title', 'Música')

    source = await discord.FFmpegOpusAudio.from_probe(
        url, **FFMPEG_OPTIONS
    )

    vc.play(source)

    await ctx.send(f"🎶 Tocando agora: **{title}**")

@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("⏹️ Desconectado do canal.")
    else:
        await ctx.send("❌ Não estou em um canal de voz.")

bot.run(TOKEN)
