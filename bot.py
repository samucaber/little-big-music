import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import asyncio
import os

# ================= CONFIG =================

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ================= YTDLP CONFIG =================

ytdl_opts = {
    "format": "bestaudio/best",
    "quiet": True,
    "default_search": "ytsearch",
    "noplaylist": False,  # Agora aceita playlist
}

ffmpeg_opts = {
    "options": "-vn"
}

ytdl = yt_dlp.YoutubeDL(ytdl_opts)

# ================= VARIÁVEIS =================

queue = []
loop_music = False
AUTO_DISCONNECT_DELAY = 60  # 1 minuto
disconnect_task = None

# ================= FUNÇÕES =================

async def ensure_voice(interaction: discord.Interaction):
    vc = interaction.guild.voice_client

    if vc:
        return vc

    if interaction.user.voice:
        return await interaction.user.voice.channel.connect()

    await interaction.response.send_message(
        "❌ Você precisa entrar em um canal de voz.",
        ephemeral=True
    )
    return None


def get_music(query: str):
    if not query.startswith("http"):
        query = f"ytsearch1:{query}"

    info = ytdl.extract_info(query, download=False)

    musics = []

    if "entries" in info:
        for entry in info["entries"]:
            if entry:
                musics.append((entry["url"], entry["title"]))
    else:
        musics.append((info["url"], info["title"]))

    return musics


async def auto_disconnect(guild):
    global disconnect_task

    await asyncio.sleep(AUTO_DISCONNECT_DELAY)

    vc = guild.voice_client
    if vc and not vc.is_playing() and not queue:
        await vc.disconnect()
        print("🔌 Desconectado automaticamente por inatividade")

    disconnect_task = None


async def play_next(guild: discord.Guild):
    global loop_music, disconnect_task

    vc = guild.voice_client
    if not vc:
        return

    if not queue:
        if not disconnect_task:
            disconnect_task = bot.loop.create_task(auto_disconnect(guild))
        return

    if disconnect_task:
        disconnect_task.cancel()
        disconnect_task = None

    url, title = queue[0]

    if not loop_music:
        queue.pop(0)

    vc.play(
        discord.FFmpegPCMAudio(url, **ffmpeg_opts),
        after=lambda e: asyncio.run_coroutine_threadsafe(
            play_next(guild), bot.loop
        )
    )

# ================= SLASH COMMANDS =================

@tree.command(name="play", description="Toca música ou playlist")
@app_commands.describe(musica="Nome ou link do YouTube")
async def play(interaction: discord.Interaction, musica: str):

    await interaction.response.defer()

    vc = await ensure_voice(interaction)
    if not vc:
        return

    try:
        musics = get_music(musica)
    except Exception as e:
        await interaction.followup.send("❌ Não consegui encontrar essa música.")
        print("Erro yt-dlp:", e)
        return

    for music in musics:
        queue.append(music)

    if not vc.is_playing():
        await interaction.followup.send(
            f"🎶 Tocando: **{musics[0][1]}**"
        )
        await play_next(interaction.guild)
    else:
        await interaction.followup.send(
            f"➕ {len(musics)} música(s) adicionada(s) à fila"
        )


@tree.command(name="pause", description="Pausa a música")
async def pause(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_playing():
        vc.pause()
        await interaction.response.send_message("⏸️ Música pausada")
    else:
        await interaction.response.send_message("❌ Nada tocando")


@tree.command(name="resume", description="Continua a música")
async def resume(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_paused():
        vc.resume()
        await interaction.response.send_message("▶️ Música retomada")
    else:
        await interaction.response.send_message("❌ Música não está pausada")


@tree.command(name="skip", description="Pula a música atual")
async def skip(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_playing():
        vc.stop()
        await interaction.response.send_message("⏭️ Música pulada")
    else:
        await interaction.response.send_message("❌ Nada tocando")


@tree.command(name="queue", description="Mostra a fila")
async def show_queue(interaction: discord.Interaction):

    if not queue:
        await interaction.response.send_message("📭 Fila vazia")
        return

    text = ""
    for i, (_, title) in enumerate(queue[:10], start=1):
        text += f"{i}. {title}\n"

    await interaction.response.send_message(f"📜 **Fila:**\n{text}")


@tree.command(name="loop", description="Ativa ou desativa loop")
async def loop(interaction: discord.Interaction):
    global loop_music
    loop_music = not loop_music
    status = "ativado" if loop_music else "desativado"
    await interaction.response.send_message(f"🔁 Loop {status}")


@tree.command(name="stop", description="Para e desconecta")
async def stop(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc:
        queue.clear()
        await vc.disconnect()
        await interaction.response.send_message("🛑 Desconectado")
    else:
        await interaction.response.send_message("❌ Não estou em um canal")


# ================= READY =================

@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Conectado como {bot.user}")

# ================= RUN =================

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN não encontrado")

bot.run(TOKEN)
