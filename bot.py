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

def clean_url(url):
    return url.split("?")[0]

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✨ Ipun Downloader Pro\n\nPilih menu lalu kirim link",
        reply_markup=reply_markup
    )

# ===== MAIN =====
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    # ===== MODE =====
    if "Video" in text:
        context.user_data["mode"] = "video"
        await update.message.reply_text("🔗 Kirim link video")
        return

    elif "MP3" in text:
        context.user_data["mode"] = "audio"
        await update.message.reply_text("🎧 Kirim link untuk MP3")
        return

    elif "Reset" in text:
        context.user_data.clear()
        await update.message.reply_text("♻️ Reset")
        return

    # ===== HANDLE LINK =====
    elif text.startswith("http"):
        mode = context.user_data.get("mode")

        if not mode:
            await update.message.reply_text("⚠️ Pilih menu dulu")
            return

        url = clean_url(text)
        msg = await update.message.reply_text("⏳ Processing...")

        try:
            # ambil judul
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                title = info.get("title", "Media")

            # ===== AUDIO =====
            if mode == "audio":
                ydl_opts = {
                    'format': 'best',
                    'outtmpl': 'video.%(ext)s',
                    'quiet': True
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

                video_file = next((f for f in os.listdir() if f.startswith("video")), None)

                if not video_file:
                    await msg.edit_text("❌ Video tidak ditemukan")
                    return

                # convert ke mp3 (butuh ffmpeg)
                os.system(f'ffmpeg -i "{video_file}" -vn -ab 192k -ar 44100 -y audio.mp3')

                if not os.path.exists("audio.mp3"):
                    await msg.edit_text("❌ Gagal convert MP3")
                    return

                with open("audio.mp3", "rb") as f:
                    await update.message.reply_audio(f, title=title)

                os.remove(video_file)
                os.remove("audio.mp3")

            # ===== VIDEO =====
            else:
                ydl_opts = {
                    'format': 'best',
                    'outtmpl': 'video.%(ext)s',
                    'quiet': True
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

                video_file = next((f for f in os.listdir() if f.startswith("video")), None)

                if not video_file:
                    await msg.edit_text("❌ Video tidak ditemukan")
                    return

                with open(video_file, "rb") as f:
                    await update.message.reply_video(f, caption=f"🎬 {title}")

                os.remove(video_file)

            await msg.edit_text("✅ Selesai!")

        except Exception as e:
            print("ERROR:", e)
            await msg.edit_text("❌ Gagal, coba link lain")

# ===== RUN =====
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

app.run_polling()
