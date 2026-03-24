from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import yt_dlp
import os

TOKEN = "8307650303:AAFJGrwoOeb73dOedEeYLDdqddyE1N65Ckg"


# START MENU
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎬 Download Video", callback_data='video')],
        [InlineKeyboardButton("🎵 Download Audio", callback_data='audio')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Pilih menu:", reply_markup=reply_markup)

# HANDLE BUTTON
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["mode"] = query.data

    await query.edit_message_text("Kirim link sekarang...")

# HANDLE LINK
async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    mode = context.user_data.get("mode")

    await update.message.reply_text("⏳ Processing...")

    try:
        if mode == "audio":
            ydl_opts = {
                'format': 'bestaudio',
                'outtmpl': 'audio.%(ext)s',
            }
        else:
            ydl_opts = {
                'format': 'mp4',
                'outtmpl': 'video.%(ext)s',
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        if mode == "audio":
            file = [f for f in os.listdir() if f.startswith("audio")][0]
            with open(file, "rb") as f:
                await update.message.reply_audio(audio=f)
            os.remove(file)
        else:
            with open("video.mp4", "rb") as f:
                await update.message.reply_video(video=f)
            os.remove("video.mp4")

    except Exception as e:
        print(e)
        await update.message.reply_text("❌ Gagal")

# RUN BOT
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))

app.run_polling()

