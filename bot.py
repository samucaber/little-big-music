import discord
from discord import app_commands
import yt_dlp
import asyncio
import os

TOKEN = os.getenv("DISCORD_TOKEN")

# -------- INTENTS --------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# -------- YT-DLP / FFMPEG --------
YDL_OPTIONS = {
    'format': 'bestaudio',
    'noplaylist': True,
    'quiet': True
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

# -------- CONTROLE --------
queues = {}      # {guild_id: [(url, title), ...]}
looping = {}     # {guild_id: bool}

@client.event
async def on_ready():
    await tree.sync()
    print(f"✅ Bot online como {client.user}")

# -------- FUNÇÃO PARA TOCAR PRÓXIMA --------
async def play_next(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    vc = interaction.guild.voice_client

    if not vc:
        return

    if queues.get(guild_id):
        url, title = queues[guild_id].pop(0)

        source = discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS)

        def after_playing(error):
            if looping.get(guild_id):
                queues[guild_id].insert(0, (url, title))

            fut = asyncio.run_coroutine_threadsafe(
                play_next(interaction),
                client.loop
            )
            try:
                fut.result()
            except:
                pass

        vc.play(source, after=after_playing)

# -------- SLASH COMMANDS --------

@tree.command(name="play", description="Tocar música (nome ou link)")
async def play(interaction: discord.Interaction, busca: str):
    if not interaction.user.voice:
        await interaction.response.send_message(
            "❌ Entre em um canal de voz primeiro.", ephemeral=True
        )
        return

    await interaction.response.defer()

    channel = interaction.user.voice.channel

    if interaction.guild.voice_client is None:
        await channel.connect()

    with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
        info = ydl.extract_info(busca, download=False)
        if 'entries' in info:
            info = info['entries'][0]

    url = info['url']
    title = info.get('title', 'Música')

    guild_id = interaction.guild.id
    queues.setdefault(guild_id, []).append((url, title))

    await interaction.followup.send(f"🎵 Adicionado à fila: {title}")

    vc = interaction.guild.voice_client
    if not vc.is_playing():
        await play_next(interaction)

@tree.command(name="queue", description="Mostrar fila de músicas")
async def queue_cmd(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    fila = queues.get(guild_id, [])

    if not fila:
        await interaction.response.send_message("📭 A fila está vazia.")
        return

    texto = "🎶 **Fila de músicas:**\n"
    for i, (_, title) in enumerate(fila, start=1):
        texto += f"{i}. {title}\n"

    await interaction.response.send_message(texto)

@tree.command(name="pause", description="Pausar música")
async def pause(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_playing():
        vc.pause()
        await interaction.response.send_message("⏸️ Música pausada.")
    else:
        await interaction.response.send_message("❌ Nada tocando.", ephemeral=True)

@tree.command(name="resume", description="Retomar música")
async def resume(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_paused():
        vc.resume()
        await interaction.response.send_message("▶️ Música retomada.")
    else:
        await interaction.response.send_message("❌ Nada pausado.", ephemeral=True)

@tree.command(name="skip", description="Pular música atual")
async def skip(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_playing():
        vc.stop()
        await interaction.response.send_message("⏭️ Música pulada.")
    else:
        await interaction.response.send_message("❌ Nada tocando.", ephemeral=True)

@tree.command(name="loop", description="Ativar ou desativar loop")
async def loop(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    looping[guild_id] = not looping.get(guild_id, False)
    estado = "ativado 🔁" if looping[guild_id] else "desativado ❌"
    await interaction.response.send_message(f"Loop {estado}")

@tree.command(name="stop", description="Parar tudo e sair do canal")
async def stop(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc:
        queues[interaction.guild.id] = []
        looping[interaction.guild.id] = False
        await vc.disconnect()
        await interaction.response.send_message("⏹️ Bot desconectado.")
    else:
        await interaction.response.send_message("❌ Não estou em um canal.", ephemeral=True)

client.run(TOKEN)
