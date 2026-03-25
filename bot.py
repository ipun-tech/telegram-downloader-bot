import os
import yt_dlp
from google import genai

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ===== CONFIG =====
TOKEN = os.getenv("TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)
# ===== UI =====
keyboard = [
    ["🎬 Download Video", "🎧 Convert MP3"],
    ["🤖 Chat AI", "🔄 Reset"]
]
reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def clean_url(url):
    return url.split("?")[0]

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✨ *Ipun Bot PRO*\n\n📥 Kirim link untuk download\n🤖 Atau tanya apa saja\n\nMenu opsional 👇",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

# ===== MAIN =====
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    # ===== MENU =====
    if "Video" in text:
        context.user_data["mode"] = "video"
        await update.message.reply_text("🔗 Kirim link video")
        return

    elif "MP3" in text:
        context.user_data["mode"] = "audio"
        await update.message.reply_text("🎧 Kirim link MP3")
        return

    elif "Chat AI" in text:
        context.user_data["mode"] = "ai"
        await update.message.reply_text("🤖 Silakan tanya apa saja")
        return

    elif "Reset" in text:
        context.user_data.clear()
        await update.message.reply_text("♻️ Reset berhasil")
        return

    mode = context.user_data.get("mode")

    # ===== DOWNLOAD =====
    if text.startswith("http"):
        url = clean_url(text)
        msg = await update.message.reply_text("⏳ Processing...")

        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                title = info.get("title", "Media")

            ydl_opts = {
                'format': 'best',
                'outtmpl': 'video.%(ext)s',
                'quiet': True
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            file = next((f for f in os.listdir() if f.startswith("video")), None)

            # ===== MP3 =====
            if mode == "audio":
                os.system(f'ffmpeg -i "{file}" -vn -ab 192k -ar 44100 -y audio.mp3')

                with open("audio.mp3", "rb") as f:
                    await update.message.reply_audio(f, title=title)

                os.remove("audio.mp3")

            # ===== VIDEO =====
            else:
                with open(file, "rb") as f:
                    await update.message.reply_video(f, caption=f"🎬 {title}")

            os.remove(file)
            await msg.edit_text("✅ Selesai!")

        except Exception as e:
            print("ERROR DOWNLOAD:", e)
            await msg.edit_text("❌ Gagal download")

    # ===== AI =====
    elif mode == "ai":
        try:
            msg = await update.message.reply_text("🤖 Sedang berpikir...")

            response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=text
)
            await msg.edit_text(response.text if response.text else "⚠️ Tidak ada respon")

        except Exception as e:
            print("AI ERROR:", e)
            await update.message.reply_text("❌ AI error")

    else:
        await update.message.reply_text("⚠️ Pilih menu dulu")

# ===== RUN =====
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

app.run_polling(drop_pending_updates=True)
