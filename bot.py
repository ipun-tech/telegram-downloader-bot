from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp
import os

TOKEN = os.getenv("TOKEN")

# ===== MENU =====
keyboard = [
    ["🎬 Download Video", "🎧 Convert to MP3"],
    ["🔄 Reset"]
]

reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ===== CLEAN URL =====
def clean_url(url):
    return url.split("?")[0]

# ===== GET OPTIONS =====
def get_opts(mode, quality="best"):
    if mode == "audio":
        return {
            'format': 'bestaudio',
            'outtmpl': 'audio.%(ext)s',
            'quiet': True
        }
    else:
        if quality == "hd":
            return {
                'format': 'bestvideo[height<=1080]+bestaudio/best',
                'outtmpl': 'video.%(ext)s',
                'quiet': True
            }
        else:
            return {
                'format': 'best',
                'outtmpl': 'video.%(ext)s',
                'quiet': True
            }

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✨ *Ipun Downloader Pro*\n\n"
        "⚡ Cepat • Tanpa Ribet • Kualitas Tinggi\n\n"
        "📥 Support:\nTikTok • YouTube • Instagram • Facebook\n\n"
        "👇 Pilih menu atau langsung kirim link",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

# ===== MAIN HANDLER =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    # ===== MODE =====
    if text == "🎬 Download Video":
        context.user_data["mode"] = "video"
        await update.message.reply_text("🔗 Kirim link video")

    elif text == "🎧 Convert to MP3":
        context.user_data["mode"] = "audio"
        await update.message.reply_text("🎧 Kirim link untuk MP3")

    elif text == "🔄 Reset":
        context.user_data.clear()
        await update.message.reply_text("♻️ Mode direset")

    # ===== HANDLE LINK =====
    elif text.startswith("http"):
        mode = context.user_data.get("mode")

        if not mode:
            await update.message.reply_text("⚠️ Pilih menu dulu ya 👇")
            return

        url = clean_url(text)
        msg = await update.message.reply_text("⏳ Mengambil data...")

        try:
            # ambil info video
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                title = info.get("title", "Media")

            await msg.edit_text(f"📥 Downloading:\n{title}")

            # coba HD dulu
            try:
                ydl_opts = get_opts(mode, "hd")
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
            except:
                # fallback
                ydl_opts = get_opts(mode, "best")
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

            await msg.edit_text("📤 Mengirim file...")

            # ===== KIRIM FILE =====
if mode == "audio":
    try:
        # ===== COBA DOWNLOAD MP3 =====
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': 'audio.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        file = [f for f in os.listdir() if f.endswith(".mp3")][0]

        with open(file, "rb") as f:
            await update.message.reply_audio(audio=f, title=title)

        os.remove(file)

    except Exception as e:
        print(e)  # ini buat kamu lihat error di logs

        # ===== FALLBACK =====
        await update.message.reply_text("⚠️ MP3 gagal, kirim video...")

        ydl_opts = {
            'format': 'best',
            'outtmpl': 'video.%(ext)s',
            'quiet': True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        file = [f for f in os.listdir() if f.startswith("video")][0]

        with open(file, "rb") as f:
            await update.message.reply_video(video=f, caption=f"🎬 {title}")

        os.remove(file)

    except:
        # ===== FALLBACK KE VIDEO =====
        await update.message.reply_text("⚠️ MP3 tidak tersedia, mengirim video...")

        ydl_opts = {
            'format': 'best',
            'outtmpl': 'video.%(ext)s',
            'quiet': True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        file = [f for f in os.listdir() if f.startswith("video")][0]

        with open(file, "rb") as f:
            await update.message.reply_video(video=f, caption=f"🎬 {title}")

        os.remove(file)

# ===== RUN =====
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, handle_message))

app.run_polling()
