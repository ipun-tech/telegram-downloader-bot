import os
import yt_dlp
import google.generativeai as genai
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ================= CONFIG =================
TOKEN = os.getenv("TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# ================= UI =================
keyboard = [
    ["🎬 Download Video", "🎧 Convert MP3"],
    ["🤖 Chat AI", "🔄 Reset"]
]

reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ================= HELPER =================
def clean_url(url):
    return url.split("?")[0]

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✨ *Ipun Bot PRO*\n\n"
        "📥 Kirim link langsung untuk download\n"
        "🤖 Atau tanya apa saja\n\n"
        "Menu hanya opsional 👇",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

# ================= MAIN =================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    # ===== RESET =====
    if "Reset" in text:
        context.user_data.clear()
        await update.message.reply_text("♻️ Reset berhasil")
        return

    # ===== HANDLE LINK (AUTO DOWNLOAD) =====
    if text.startswith("http"):
        url = clean_url(text)
        msg = await update.message.reply_text("⏳ Processing...")

        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                title = info.get("title", "Media")

            # default: download video
            ydl_opts = {
                'format': 'best',
                'outtmpl': 'video.%(ext)s',
                'quiet': True
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            video_file = next((f for f in os.listdir() if f.startswith("video")), None)

            # ===== JIKA USER MAU MP3 =====
            if "mp3" in text.lower() or "audio" in text.lower():
                mp3_file = "audio.mp3"
                os.system(f'ffmpeg -i "{video_file}" -vn -ab 192k -ar 44100 -y "{mp3_file}"')

                with open(mp3_file, "rb") as f:
                    await update.message.reply_audio(audio=f, title=title)

                os.remove(mp3_file)

            else:
                with open(video_file, "rb") as f:
                    await update.message.reply_video(f, caption=f"🎬 {title}")

            os.remove(video_file)

            await msg.edit_text("✅ Selesai!")

        except Exception as e:
            print("DOWNLOAD ERROR:", e)
            await msg.edit_text("❌ Gagal download")

        return

    # ===== AI CHAT =====
    try:
        msg = await update.message.reply_text("🤖 Sedang berpikir...")

        response = model.generate_content(text)

        await msg.edit_text(response.text)

    except Exception as e:
        print("AI ERROR:", e)
        await update.message.reply_text("❌ AI error")

# ================= RUN =================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

print("BOT RUNNING...")
app.run_polling()
