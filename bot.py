import discord
from discord import app_commands
import yt_dlp as youtube_dl
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os

# ========================
# VARIÁVEIS DE AMBIENTE
# ========================
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

# ========================
# SPOTIFY (opcional)
# ========================
sp = None
if SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET:
    sp = spotipy.Spotify(
        auth_manager=SpotifyClientCredentials(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET
        )
    )

# ========================
# YT-DLP (streaming)
# ========================
ydl_opts = {
    "format": "bestaudio",
    "noplaylist": True,
    "quiet": True,
}

# ========================
# DISCORD CLIENT
# ========================
intents = discord.Intents.default()
intents.voice_states = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# ========================
# EVENTOS
# ========================
@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Bot {bot.user} está online e pronto!")

# ========================
# /play
# ========================
@tree.command(name="play", description="Toca uma música do YouTube ou Spotify")
async def play(interaction: discord.Interaction, url: str):

    if not interaction.user.voice:
        await interaction.response.send_message(
            "❌ Você precisa estar em um canal de voz!",
            ephemeral=True
        )
        return

    await interaction.response.defer()

    channel = interaction.user.voice.channel

    vc = interaction.guild.voice_client
    if vc is None:
        vc = await channel.connect()

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:

            # ========= SPOTIFY =========
            if "spotify.com" in url:
                if sp is None:
                    await vc.disconnect()
                    await interaction.followup.send(
                        "⚠️ Spotify não configurado. Use link do YouTube."
                    )
                    return

                track_id = url.split("/")[-1].split("?")[0]
                track = sp.track(track_id)
                search = f"{track['name']} {track['artists'][0]['name']}"

                data = ydl.extract_info(
                    f"ytsearch:{search}", download=False
                )

                if not data["entries"]:
                    await vc.disconnect()
                    await interaction.followup.send(
                        "❌ Música não encontrada no YouTube."
                    )
                    return

                info = data["entries"][0]

            # ========= YOUTUBE =========
            else:
                info = ydl.extract_info(url, download=False)

        audio_url = info["url"]

        vc.play(discord.FFmpegPCMAudio(audio_url))

        await interaction.followup.send(
            f"🎵 **Tocando:** {info.get('title', 'Desconhecido')}"
        )

    except Exception as e:
        await vc.disconnect()
        await interaction.followup.send(
            f"❌ Erro ao tocar música:\n```{e}```"
        )

# ========================
# /stop
# ========================
@tree.command(name="stop", description="Para a música e desconecta")
async def stop(interaction: discord.Interaction):

    vc = interaction.guild.voice_client

    if vc:
        await vc.disconnect()
        await interaction.response.send_message("⏹️ Música parada!")
    else:
        await interaction.response.send_message(
            "⚠️ Não estou em um canal de voz.",
            ephemeral=True
        )

# ========================
# RUN
# ========================
bot.run(DISCORD_TOKEN)
