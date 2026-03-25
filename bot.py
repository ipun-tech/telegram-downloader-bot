import os
import yt_dlp
import asyncio
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

# ===== START COMMAND =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✨ *Ipun Bot PRO*\n\n"
        "📥 Kirim link untuk download\n"
        "🤖 Atau tanya apa saja (Aktifkan Mode AI dulu)\n\n"
        "Pilih menu di bawah 👇",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

# ===== MAIN HANDLER =====
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    mode = context.user_data.get("mode")

    # --- 1. LOGIKA MENU TOMBOL ---
    if "Video" in text:
        context.user_data["mode"] = "video"
        await update.message.reply_text("🎬 **Mode Video Aktif.**\nKirim link video (IG/TikTok/YT).", parse_mode="Markdown")
        return

    elif "MP3" in text:
        context.user_data["mode"] = "audio"
        await update.message.reply_text("🎧 **Mode MP3 Aktif.**\nKirim link untuk diconvert ke audio.", parse_mode="Markdown")
        return

    elif "Chat AI" in text:
        context.user_data["mode"] = "ai"
        await update.message.reply_text("🤖 **Mode Chat AI Aktif.**\nSilakan kirim pertanyaanmu!", parse_mode="Markdown")
        return

    elif "Reset" in text:
        context.user_data.clear()
        await update.message.reply_text("♻️ Sesi direset. Mode kembali ke default.")
        return

    # --- 2. LOGIKA DOWNLOAD ---
    if text.startswith("http"):
        url = clean_url(text)
        msg = await update.message.reply_text("⏳ Sedang memproses media...")

        try:
            ydl_opts = {
                'format': 'best',
                'outtmpl': 'downloaded_media.%(ext)s',
                'quiet': True,
                'no_warnings': True
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get("title", "Media")
                filename = ydl.prepare_filename(info)

            if mode == "audio":
                audio_file = "audio_output.mp3"
                await msg.edit_text("🎵 Mengonversi ke MP3...")
                os.system(f'ffmpeg -i "{filename}" -vn -ab 192k -ar 44100 -y "{audio_file}"')
                
                with open(audio_file, "rb") as f:
                    await update.message.reply_audio(f, title=title)
                
                if os.path.exists(audio_file): os.remove(audio_file)
                if os.path.exists(filename): os.remove(filename)

            else:
                with open(filename, "rb") as f:
                    await update.message.reply_video(f, caption=f"🎬 {title}")
                
                if os.path.exists(filename): os.remove(filename)

            await msg.delete()

        except Exception as e:
            print("ERROR DOWNLOAD:", e)
            await msg.edit_text(f"❌ Gagal memproses link.\nError: {str(e)[:50]}")
        return

    # --- 3. LOGIKA AI ---
    elif mode == "ai":
        try:
            processing_msg = await update.message.reply_text("🤖 Mengetik...")
            
            # Kembali menggunakan gemini-2.0-flash yang didukung SDK baru
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=text
            )

            if response.text:
                await processing_msg.edit_text(response.text)
            else:
                await processing_msg.edit_text("⚠️ AI tidak memberikan respon.")
        
        except Exception as e:
            error_msg = str(e)
            print("AI ERROR:", error_msg)
            # Menangkap error limit dari Google
            if "429" in error_msg or "quota" in error_msg.lower():
                await processing_msg.edit_text("❌ Limit API Google kamu sedang penuh/terlalu cepat. Tunggu 1 menit dan coba lagi.")
            else:
                await processing_msg.edit_text("❌ Waduh, otak AI saya lagi error. Coba lagi nanti.")
    
    # --- 4. JIKA TIDAK ADA MODE ---
    else:
        await update.message.reply_text("💡 Pilih menu dulu atau kirim link video ya!")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).read_timeout(30).write_timeout(30).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    print("Bot Berhasil Dijalankan...")
    app.run_polling(drop_pending_updates=True)
