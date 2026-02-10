import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os

# Variáveis de ambiente
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')

# Inicializar Spotify apenas se as credenciais estiverem definidas (opcional)
if SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET:
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET))
else:
    sp = None  # Spotify não disponível

# Configuração do YouTube
ydl_opts = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
}

# Adicionar intents para discord.py v2
intents = discord.Intents.default()
intents.message_content = True  # Necessário para comandos baseados em mensagens

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Bot {bot.user} está online!')

@bot.command()
async def play(ctx, url):
    if not ctx.author.voice:
        await ctx.send("Você precisa estar em um canal de voz!")
        return
    
    channel = ctx.author.voice.channel
    vc = await channel.connect()
    
    if 'spotify.com' in url:
        if sp is None:
            await ctx.send("Spotify não configurado. Use links do YouTube.")
            return
        # Extrair ID da música do Spotify
        track_id = url.split('/')[-1].split('?')[0]
        track = sp.track(track_id)
        search_query = f"{track['name']} {track['artists'][0]['name']}"
        # Buscar no YouTube
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch:{search_query}", download=False)['entries'][0]
            url = info['url']
    else:
        # Para YouTube direto
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            url = info['url']
    
    vc.play(discord.FFmpegPCMAudio(url))
    await ctx.send(f"Tocando: {info['title']}")

@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()

bot.run(DISCORD_TOKEN)
