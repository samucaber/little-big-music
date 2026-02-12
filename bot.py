import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import asyncio
import os

# ================= CONFIG =================

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ================= YTDLP / FFMPEG =================

ytdl_opts = {
    "format": "bestaudio/best",
    "quiet": True,
    "default_search": "ytsearch",
    "ignoreerrors": True,
    "extract_flat": False
}

ffmpeg_opts = {
    "options": "-vn"
}

# ================= VARIÁVEIS =================

queue = []
loop_music = False
current_music = None
AUTO_DISCONNECT_DELAY = 60  # 1 minuto

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
    with yt_dlp.YoutubeDL(ytdl_opts) as ydl:
        info = ydl.extract_info(query, download=False)

        # Se for playlist
        if "entries" in info:
            results = []
            for entry in info["entries"]:
                if entry:
                    results.append((entry["url"], entry["title"]))
            return results

        # Música única
        return [(info["url"], info["title"])]


async def play_next(guild: discord.Guild):
    global loop_music, current_music

    vc = guild.voice_client
    if not vc:
        return

    if not queue:
        await asyncio.sleep(AUTO_DISCONNECT_DELAY)
        if not queue and vc.is_connected():
            await vc.disconnect()
        return

    url, title = queue[0]
    current_music = title

    if not loop_music:
        queue.pop(0)

    vc.play(
        discord.FFmpegPCMAudio(url, **ffmpeg_opts),
        after=lambda e: asyncio.run_coroutine_threadsafe(
            play_next(guild), bot.loop
        )
    )

# ================= SLASH COMMANDS =================

@tree.command(name="play", description="Toca música pelo nome, link ou playlist")
@app_commands.describe(musica="Nome da música ou link do YouTube")
async def play(interaction: discord.Interaction, musica: str):
    vc = await ensure_voice(interaction)
    if not vc:
        return

    await interaction.response.defer()

    try:
        results = get_music(musica)
    except Exception:
        await interaction.followup.send("❌ Não consegui encontrar essa música.")
        return

    for item in results:
        queue.append(item)

    if not vc.is_playing():
        await interaction.followup.send(
            f"🎶 Tocando agora: **{results[0][1]}**"
        )
        await play_next(interaction.guild)
    else:
        await interaction.followup.send(
            f"➕ {len(results)} música(s) adicionada(s) à fila"
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
async def skip(interaction: discord.Interation):
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
    for i, (_, title) in enumerate(queue, start=1):
        text += f"{i}. {title}\n"

    await interaction.response.send_message(
        f"📜 **Fila:**\n{text}"
    )


@tree.command(name="clearqueue", description="Limpa a fila de músicas")
async def clearqueue(interaction: discord.Interaction):
    if not queue:
        await interaction.response.send_message("📭 A fila já está vazia")
        return

    queue.clear()
    await interaction.response.send_message("🗑️ Fila limpa com sucesso")


@tree.command(name="musicaatual", description="Mostra a música atual")
async def musicaatual(interaction: discord.Interaction):
    vc = interaction.guild.voice_client

    if vc and vc.is_playing() and current_music:
        await interaction.response.send_message(
            f"🎶 Tocando agora: **{current_music}**"
        )
    else:
        await interaction.response.send_message("❌ Nenhuma música está tocando")


@tree.command(name="loop", description="Ativa ou desativa o loop")
async def loop(interaction: discord.Interaction):
    global loop_music
    loop_music = not loop_music
    status = "ativado" if loop_music else "desativado"
    await interaction.response.send_message(f"🔁 Loop {status}")


@tree.command(name="stop", description="Para a música e sai do canal")
async def stop(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc:
        await vc.disconnect()
        queue.clear()
        await interaction.response.send_message("🛑 Música parada e saí do canal")
    else:
        await interaction.response.send_message("❌ Não estou em um canal")


# ================= READY =================

@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Bot conectado como {bot.user}")


# ================= RUN =================

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN não encontrado nas variáveis de ambiente")

bot.run(TOKEN)
