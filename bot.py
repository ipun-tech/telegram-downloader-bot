import os
import yt_dlp
import requests
import asyncio
import io
import cv2
import numpy as np
from colorthief import ColorThief
from static_ffmpeg import add_paths

# Inisialisasi FFmpeg untuk Railway
add_paths() 

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# ===== CONFIG =====
TOKEN = os.getenv("TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ===== UI: MENU UTAMA (Lengkap 5 Mode) =====
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("🎬 Download Video", callback_data="mode_video"),
         InlineKeyboardButton("🎧 Convert MP3", callback_data="mode_audio")],
        [InlineKeyboardButton("🤖 Chat AI", callback_data="mode_ai"),
         InlineKeyboardButton("🎨 Buat Gambar", callback_data="mode_gambar")],
        [InlineKeyboardButton("🌈 Palet Warna", callback_data="mode_warna")],
        [InlineKeyboardButton("🔄 Reset", callback_data="mode_reset")]
    ]
    return InlineKeyboardMarkup(keyboard)

def clean_url(url):
    return url.split("?")[0]

# ===== START COMMAND =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pesan = (
        "✨ **Ipun Bot PRO v5.0**\n\n"
        "Asisten digitalmu sudah siap. Silakan pilih mode kerja di bawah ini untuk memulai! 👇"
    )
    if update.message:
        await update.message.reply_text(pesan, parse_mode="Markdown", reply_markup=get_main_menu())

# ===== HANDLER KLIK TOMBOL =====
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() 
    data = query.data

    if data == "mode_video":
        context.user_data["mode"] = "video"
        msg = "🎬 **Mode Video Aktif.**\nKirim link video (IG/TikTok/YT) yang ingin diunduh."
    elif data == "mode_audio":
        context.user_data["mode"] = "audio"
        msg = "🎧 **Mode MP3 Aktif.**\nKirim link media untuk dikonversi menjadi audio."
    elif data == "mode_ai":
        context.user_data["mode"] = "ai"
        msg = "🤖 **Mode Chat AI Aktif.**\nSilakan kirim pertanyaan atau topik diskusi."
    elif data == "mode_gambar":
        context.user_data["mode"] = "gambar"
        msg = "🎨 **Mode Gambar Aktif.**\nKirim deskripsi visual (English) untuk dilukis AI."
    elif data == "mode_warna":
        context.user_data["mode"] = "warna"
        msg = "🌈 **Mode Palet Warna Aktif.**\nKirim Foto/Video untuk ekstrak kode HEX sinematik."
    elif data == "mode_reset":
        context.user_data.clear()
        msg = "♻️ **Sesi direset.** Silakan pilih mode baru:"
    
    await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=get_main_menu())

# --- 1. LOGIKA MEDIA (WARNA) ---
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get("mode")
    
    if mode != "warna":
        await update.message.reply_text("💡 Aktifkan **Mode Palet Warna** dulu untuk fitur ini!", reply_markup=get_main_menu())
        return

    msg = await update.message.reply_text("🕵️ Menganalisis palet warna sinematik... ⏳")
    
    try:
        # Identifikasi jenis file
        if update.message.photo:
            file_id = update.message.photo[-1].file_id
            ext = ".jpg"
        elif update.message.video:
            file_id = update.message.video.file_id
            ext = ".mp4"
        else: return

        file = await context.bot.get_file(file_id)
        path_file = f"temp_media{ext}"
        await file.download_to_drive(path_file)

        path_extract = path_file
        if update.message.video:
            cap = cv2.VideoCapture(path_file)
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) // 2)
            ret, frame = cap.read()
            if ret:
                path_extract = "temp_frame.jpg"
                cv2.imwrite(path_extract, frame)
            cap.release()

        # Ekstrak 5 warna utama
        color_thief = ColorThief(path_extract)
        palette = color_thief.get_palette(color_count=5, quality=1)
        
        balasan = "🎨 **Cinematic Color Palette Found!**\n\n"
        for i, rgb in enumerate(palette):
            hex_color = '#%02x%02x%02x' % rgb
            balasan += f"{i+1}. `{hex_color.upper()}` 🟦\n"
        
        balasan += "\n*Tips:* Gunakan kode HEX ini di CapCut/Photoshop untuk hasil grading profesional! 🚀"
        await msg.edit_text(balasan, parse_mode="Markdown")

        # Hapus file sampah
        for f in [path_file, "temp_frame.jpg"]:
            if os.path.exists(f): os.remove(f)

    except Exception as e:
        await msg.edit_text("❌ Gagal mengekstrak warna. Coba file lain.")

# --- 2. LOGIKA TEKS (CHAT, GAMBAR, DOWNLOAD) ---
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    mode = context.user_data.get("mode")

    if not mode:
        await update.message.reply_text("💡 Pilih mode dulu melalui /start!", reply_markup=get_main_menu())
        return

    # A. LOGIKA DOWNLOAD (VIDEO/AUDIO)
    if text.startswith("http"):
        if mode not in ["video", "audio"]:
            await update.message.reply_text("⚠️ Aktifkan Mode Video/MP3 dulu.")
            return
        
        msg = await update.message.reply_text("⏳ Memproses permintaan media...")
        try:
            url = clean_url(text)
            if mode == "audio":
                opts = {'format': 'bestaudio/best', 'outtmpl': 'out.%(ext)s', 'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3'}], 'quiet': True}
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    await update.message.reply_audio(open("out.mp3", "rb"), title=info.get("title"))
                if os.path.exists("out.mp3"): os.remove("out.mp3")
            
            elif mode == "video":
                opts = {'format': 'best', 'outtmpl': 'out.%(ext)s', 'quiet': True}
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    fname = ydl.prepare_filename(info)
                    await update.message.reply_video(open(fname, "rb"), caption=f"🎬 {info.get('title')}")
                if os.path.exists(fname): os.remove(fname)
            await msg.delete()
        except:
            await msg.edit_text("❌ Gagal memproses link.")
        return

    # B. LOGIKA BUAT GAMBAR
    if mode == "gambar":
        msg = await update.message.reply_text("🎨 Pabrik Ipun sedang melukis... ⏳")
        try:
            import urllib.parse
            url = f"https://ipun-pelukis.tipungsinoman.workers.dev/?prompt={urllib.parse.quote(text)}"
            res = requests.get(url)
            if res.status_code == 200:
                await update.message.reply_photo(
                    photo=io.BytesIO(res.content), 
                    caption=f"✨ **Ipun Bot PRO | Rendering Complete**\n\nPrompt: _{text}_", 
                    parse_mode="Markdown"
                )
                await msg.delete()
            else: await msg.edit_text("❌ Pabrik gambar sedang sibuk.")
        except: await msg.edit_text("❌ Gagal menghubungi pabrik.")

    # C. LOGIKA CHAT AI (GROQ)
    elif mode == "ai":
        msg = await update.message.reply_text("🤖 AI sedang berpikir...")
        try:
            headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
            payload = {"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": text}]}
            res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload).json()
            jawaban = res['choices'][0]['message']['content']
            
            # Kirim jawaban (potong jika terlalu panjang)
            if len(jawaban) > 4000:
                await msg.edit_text(jawaban[:4000])
                await update.message.reply_text(jawaban[4000:])
            else:
                await msg.edit_text(jawaban)
        except: await msg.edit_text("❌ Otak AI sedang lelah. Coba lagi nanti.")

# ===== RUNNING BOT =====
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_click))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_media))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    
    print("🚀 Ipun Bot PRO v5.0 is Online!")
    app.run_polling(drop_pending_updates=True)
