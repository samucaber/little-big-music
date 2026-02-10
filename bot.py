import os
import discord
from discord import app_commands
import yt_dlp

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.voice_states = True

class MyClient(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        print("✅ Slash commands sincronizados")

bot = MyClient()

@bot.event
async def on_ready():
    print(f"🤖 Bot conectado como {bot.user}")

@bot.tree.command(name="play", description="Toca música do YouTube")
async def play(interaction: discord.Interaction, url: str):
    await interaction.response.defer()

    # Verifica se o usuário está em canal de voz
    if interaction.user.voice is None:
        await interaction.followup.send("❌ Entre em um canal de voz primeiro.")
        return

    channel = interaction.user.voice.channel

    # Conecta ao canal
    if interaction.guild.voice_client is None:
        vc = await channel.connect()
    else:
        vc = interaction.guild.voice_client

    # yt-dlp
    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info["url"]
        title = info.get("title", "Música")

    source = discord.FFmpegPCMAudio(
        audio_url,
        before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
        options="-vn",
    )

    vc.play(source)

    await interaction.followup.send(f"🎶 Tocando: **{title}**")

@bot.tree.command(name="stop", description="Para a música e sai do canal")
async def stop(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc:
        await vc.disconnect()
        await interaction.response.send_message("⏹️ Música parada.")
    else:
        await interaction.response.send_message("❌ Não estou em canal de voz.")

bot.run(TOKEN)
