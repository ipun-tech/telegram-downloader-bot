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

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✨ *Ipun Downloader Pro*\n\n"
        "📥 TikTok • YouTube • IG • FB\n\n"
        "👇 Pilih menu atau kirim link langsung",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

# ===== MAIN =====
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

            # ===== DOWNLOAD =====
            if mode == "audio":
    try:
        # download video dulu
        ydl_opts = {
            'format': 'best',
            'outtmpl': 'video.%(ext)s',
            'quiet': True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        video_file = [f for f in os.listdir() if f.startswith("video")][0]

        # convert ke mp3 pakai ffmpeg
        os.system(f'ffmpeg -i "{video_file}" -vn -ab 192k -ar 44100 -y audio.mp3')

        with open("audio.mp3", "rb") as f:
            await update.message.reply_audio(f)

        os.remove(video_file)
        os.remove("audio.mp3")

    except Exception as e:
        print("ERROR:", e)
        await update.message.reply_text("❌ Gagal convert")

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

            else:
                ydl_opts = {
                    'format': 'bestvideo+bestaudio/best',
                    'outtmpl': 'video.%(ext)s',
                    'quiet': True
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

                file = [f for f in os.listdir() if f.startswith("video")][0]

                with open(file, "rb") as f:
                    await update.message.reply_video(video=f, caption=f"🎬 {title}")

                os.remove(file)

            await msg.edit_text("✅ Selesai!")

        except Exception as e:
            print("ERROR:", e)
            await msg.edit_text("❌ Gagal, coba link lain")

# ===== RUN =====
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, handle_message))

app.run_polling()
