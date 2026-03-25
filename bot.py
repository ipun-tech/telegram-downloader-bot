from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp
import os
import google.generativeai as genai

# ===== ENV =====
TOKEN = os.getenv("TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

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
        "✨ Ipun Bot (Downloader + AI Gemini)\n\n"
        "🎬 Download Video\n🎧 Convert MP3\n🤖 Chat AI\n\n"
        "Pilih menu atau langsung tanya",
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

    # ===== LINK PROCESS =====
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

                mp3_file = "audio.mp3"
                os.system(f'ffmpeg -i "{video_file}" -vn -ab 192k -ar 44100 -y "{mp3_file}"')

                if not os.path.exists(mp3_file):
                    await msg.edit_text("❌ Gagal convert MP3")
                    return

                with open(mp3_file, "rb") as f:
                    await update.message.reply_audio(f, title=title)

                os.remove(video_file)
                os.remove(mp3_file)

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
            await msg.edit_text("❌ Gagal download")

    # ===== AI GEMINI =====
    else:
        try:
            msg = await update.message.reply_text("🤖 Sedang berpikir...")

            response = model.generate_content(text)
            reply = response.text

            await msg.edit_text(reply)

        except Exception as e:
            print("AI ERROR:", e)
            await update.message.reply_text("❌ AI error")

# ===== RUN =====
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

app.run_polling()
