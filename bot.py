import os
import yt_dlp
import google.generativeai as genai

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ===== CONFIG =====
TOKEN = os.getenv("TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

print("API:", GEMINI_API_KEY)

# setup Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-pro")

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

    # ===== MODE =====
    mode = context.user_data.get("mode")

    # ===== LINK =====
    if text.startswith("http"):
        if not mode:
            await update.message.reply_text("⚠️ Pilih menu dulu")
            return

        await update.message.reply_text("⏳ Processing...")
        return

    # ===== CHAT AI =====
    if mode == "ai":
        await update.message.reply_text("🤖 Sedang berpikir...")

        try:
            response = model.generate_content(text)
            await update.message.reply_text(response.text)

        except Exception as e:
            print("AI ERROR:", e)
            await update.message.reply_text("❌ AI error")

# ================= RUN =================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

app.run_polling(drop_pending_updates=True)
