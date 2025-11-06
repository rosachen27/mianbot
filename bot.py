import discord
from discord import app_commands
from discord.ext import tasks
from gtts import gTTS
import json
import datetime
import asyncio
import os

CONFIG_FILE = "config.json"
import os

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError("⚠️ Thiếu biến môi trường DISCORD_TOKEN. Hãy đặt trong Render.")


intents = discord.Intents.all()
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# ================== HÀM HỖ TRỢ ==================

def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ================== SỰ KIỆN BOT ==================

@bot.event
async def on_ready():
    print(f"✅ Bot đã đăng nhập: {bot.user}")
    await tree.sync()
    cfg = load_config()
    # Tự join voice channel
    if cfg["voice_channel_id"]:
        channel = bot.get_channel(cfg["voice_channel_id"])
        if channel:
            try:
                await channel.connect()
                print(f"🎧 Đã kết nối tới voice channel: {channel.name}")
            except discord.ClientException:
                pass
    check_announcements.start()

# ================== NHIỆM VỤ LẶP ==================

@tasks.loop(seconds=30)
async def check_announcements():
    cfg = load_config()
    now = datetime.datetime.now().strftime("%H:%M")

    for ann in cfg["announcements"]:
        if ann["time"] == now:
            await send_announcement(ann["content"])
            await asyncio.sleep(60)  # tránh lặp lại trong cùng phút

async def send_announcement(text):
    cfg = load_config()
    voice_channel_id = cfg.get("voice_channel_id")
    text_channel_id = cfg.get("text_channel_id")

    if voice_channel_id:
        vc = discord.utils.get(bot.voice_clients)
        if not vc or not vc.is_connected():
            channel = bot.get_channel(voice_channel_id)
            if channel:
                vc = await channel.connect()

        # Phát TTS
        tts = gTTS(text=text, lang="vi")
        tts.save("tts.mp3")
        vc.play(discord.FFmpegPCMAudio("tts.mp3"))
        while vc.is_playing():
            await asyncio.sleep(1)
        os.remove("tts.mp3")

    if text_channel_id:
        text_channel = bot.get_channel(text_channel_id)
        if text_channel:
            await text_channel.send(f"📢 **Thông báo:** {text}")

# ================== SLASH COMMANDS ==================

@tree.command(name="thongbao", description="Cấu hình và quản lý thông báo tự động")
@app_commands.describe(action="setup/add/list/remove")
async def thongbao(interaction: discord.Interaction, action: str):
    await interaction.response.send_message(
        "Dùng subcommand cụ thể: `/thongbao setup`, `/thongbao add`, `/thongbao list`, `/thongbao remove`",
        ephemeral=True
    )

# ---- /thongbao setup ----
@tree.command(name="thongbao_setup", description="Chọn kênh voice & text cho thông báo")
@app_commands.describe(voice_channel="Chọn kênh voice", text_channel="Chọn kênh text")
async def thongbao_setup(interaction: discord.Interaction, voice_channel: discord.VoiceChannel, text_channel: discord.TextChannel):
    cfg = load_config()
    cfg["voice_channel_id"] = voice_channel.id
    cfg["text_channel_id"] = text_channel.id
    save_config(cfg)
    await interaction.response.send_message(f"✅ Đã thiết lập kênh voice `{voice_channel.name}` và text `{text_channel.name}`")

# ---- /thongbao add ----
@tree.command(name="thongbao_add", description="Thêm thông báo mới")
@app_commands.describe(time="Giờ (HH:MM)", content="Nội dung thông báo")
async def thongbao_add(interaction: discord.Interaction, time: str, content: str):
    cfg = load_config()
    cfg["announcements"].append({"time": time, "content": content})
    save_config(cfg)
    await interaction.response.send_message(f"✅ Đã thêm thông báo lúc **{time}**: {content}")

# ---- /thongbao list ----
@tree.command(name="thongbao_list", description="Xem danh sách thông báo")
async def thongbao_list(interaction: discord.Interaction):
    cfg = load_config()
    if not cfg["announcements"]:
        await interaction.response.send_message("📭 Chưa có thông báo nào.")
        return

    msg = "**📅 Danh sách thông báo:**\n"
    for ann in cfg["announcements"]:
        msg += f"- ⏰ `{ann['time']}` → {ann['content']}\n"
    await interaction.response.send_message(msg)

# ---- /thongbao remove ----
@tree.command(name="thongbao_remove", description="Xóa thông báo theo giờ")
@app_commands.describe(time="Giờ (HH:MM) cần xóa")
async def thongbao_remove(interaction: discord.Interaction, time: str):
    cfg = load_config()
    before = len(cfg["announcements"])
    cfg["announcements"] = [a for a in cfg["announcements"] if a["time"] != time]
    save_config(cfg)
    after = len(cfg["announcements"])

    if before == after:
        await interaction.response.send_message(f"⚠️ Không tìm thấy thông báo lúc {time}.")
    else:
        await interaction.response.send_message(f"🗑️ Đã xóa thông báo lúc {time}.")# ---- /thongbao test ----
@tree.command(name="thongbao_test", description="Kiểm tra bot phát thử thông báo TTS")
async def thongbao_test(interaction: discord.Interaction):
    cfg = load_config()

    voice_channel_id = cfg.get("voice_channel_id")
    text_channel_id = cfg.get("text_channel_id")

    if not voice_channel_id or not text_channel_id:
        await interaction.response.send_message("⚠️ Bạn chưa thiết lập kênh bằng `/thongbao_setup`!", ephemeral=True)
        return

    await interaction.response.send_message("🔊 Đang phát thử thông báo...", ephemeral=True)
    test_text = "Đây là thông báo kiểm tra. Bot hoạt động bình thường!"

    # Phát TTS trong voice
    vc = discord.utils.get(bot.voice_clients)
    if not vc or not vc.is_connected():
        channel = bot.get_channel(voice_channel_id)
        if channel:
            vc = await channel.connect()

    tts = gTTS(text=test_text, lang="vi")
    tts.save("tts_test.mp3")
    vc.play(discord.FFmpegPCMAudio("tts_test.mp3"))
    while vc.is_playing():
        await asyncio.sleep(1)
    os.remove("tts_test.mp3")

    # Gửi text song song
    text_channel = bot.get_channel(text_channel_id)
    if text_channel:
        await text_channel.send(f"✅ **Test TTS thành công!**\n> {test_text}")

# ================== CHẠY BOT ==================
bot.run(TOKEN)
