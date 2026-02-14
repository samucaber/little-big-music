import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import asyncio
import os
import uuid

# ================= CONFIG =================

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.voice_states = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

AUTO_DISCONNECT_DELAY = 60

os.makedirs("downloads", exist_ok=True)

# ================= YTDLP =================

def download_music(query: str):
    unique_id = str(uuid.uuid4())

    ytdl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "default_search": "ytsearch",
        "outtmpl": f"downloads/{unique_id}_%(title)s.%(ext)s",
        "nocheckcertificate": True,
        "ignoreerrors": True,
    }

    with yt_dlp.YoutubeDL(ytdl_opts) as ydl:
        info = ydl.extract_info(query, download=True)

        if not info:
            return []

        results = []

        if "entries" in info:
            for entry in info["entries"]:
                if entry:
                    filename = ydl.prepare_filename(entry)
                    results.append((filename, entry["title"]))
        else:
            filename = ydl.prepare_filename(info)
            results.append((filename, info["title"]))

        return results


# ================= CONTROLE =================

queues = {}
loops = {}
current_music = {}


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


async def play_next(guild: discord.Guild):
    guild_id = guild.id
    vc = guild.voice_client

    if not vc:
        return

    if not queues.get(guild_id):
        current_music[guild_id] = None
        await asyncio.sleep(AUTO_DISCONNECT_DELAY)

        if not queues.get(guild_id) and vc.is_connected():
            await vc.disconnect()

        return

    filename, title = queues[guild_id][0]
    current_music[guild_id] = title

    if not loops.get(guild_id, False):
        queues[guild_id].pop(0)

    def after_play(error):
        try:
            if os.path.exists(filename):
                os.remove(filename)
        except Exception as e:
            print("Erro ao deletar arquivo:", e)

        asyncio.run_coroutine_threadsafe(
            play_next(guild), bot.loop
        )

    try:
        vc.play(
            discord.FFmpegOpusAudio(filename),
            after=after_play
        )
    except Exception as e:
        print("Erro ao tocar:", e)
        await play_next(guild)


# ================= COMANDOS =================

@tree.command(name="play", description="Toca música pelo nome, link ou playlist")
@app_commands.describe(musica="Nome ou link do YouTube")
async def play(interaction: discord.Interaction, musica: str):
    guild_id = interaction.guild.id

    vc = await ensure_voice(interaction)
    if not vc:
        return

    await interaction.response.defer()

    try:
        results = download_music(musica)
    except Exception as e:
        print("Erro download:", e)
        await interaction.followup.send("❌ Não consegui baixar essa música.")
        return

    if not results:
        await interaction.followup.send("❌ Não encontrei resultados.")
        return

    if guild_id not in queues:
        queues[guild_id] = []

    for item in results:
        queues[guild_id].append(item)

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


@tree.command(name="skip", description="Pula a música")
async def skip(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_playing():
        vc.stop()
        await interaction.response.send_message("⏭️ Música pulada")
    else:
        await interaction.response.send_message("❌ Nada tocando")


@tree.command(name="queue", description="Mostra a fila")
async def show_queue(interaction: discord.Interaction):
    guild_id = interaction.guild.id

    if not queues.get(guild_id):
        await interaction.response.send_message("📭 Fila vazia")
        return

    text = ""
    for i, (_, title) in enumerate(queues[guild_id], start=1):
        text += f"{i}. {title}\n"

    await interaction.response.send_message(f"📜 **Fila:**\n{text}")


@tree.command(name="clearqueue", description="Limpa a fila")
async def clearqueue(interaction: discord.Interaction):
    guild_id = interaction.guild.id

    if not queues.get(guild_id):
        await interaction.response.send_message("📭 A fila já está vazia")
        return

    queues[guild_id].clear()
    await interaction.response.send_message("🗑️ Fila limpa")


@tree.command(name="musicaatual", description="Mostra a música atual")
async def musicaatual(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    vc = interaction.guild.voice_client

    if vc and vc.is_playing() and current_music.get(guild_id):
        await interaction.response.send_message(
            f"🎶 Tocando agora: **{current_music[guild_id]}**"
        )
    else:
        await interaction.response.send_message("❌ Nenhuma música tocando")


@tree.command(name="loop", description="Ativa ou desativa o loop")
async def loop(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    loops[guild_id] = not loops.get(guild_id, False)

    status = "ativado" if loops[guild_id] else "desativado"
    await interaction.response.send_message(f"🔁 Loop {status}")


@tree.command(name="stop", description="Para e sai do canal")
async def stop(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    vc = interaction.guild.voice_client

    if vc:
        await vc.disconnect()
        queues[guild_id] = []
        current_music[guild_id] = None
        await interaction.response.send_message("🛑 Música parada e desconectado")
    else:
        await interaction.response.send_message("❌ Não estou em um canal")


# ================= READY =================

@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Bot conectado como {bot.user}")


# ================= RUN =================

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN não configurado")

bot.run(TOKEN)
