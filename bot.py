import os
import yt_dlp
import requests
import asyncio
import io # <-- Tambahan baru untuk ngurus file gambar
from static_ffmpeg import add_paths
add_paths() # Memaksa bot bawa FFmpeg sendiri

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# ===== CONFIG =====
TOKEN = os.getenv("TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Mengambil kunci Hugging Face dari Railway
HF_TOKEN = os.getenv("HF_TOKEN") 
HF_API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-2-1"
# ===== UI: TOMBOL TRANSPARAN (INLINE) =====
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("🎬 Download Video", callback_data="mode_video"),
         InlineKeyboardButton("🎧 Convert MP3", callback_data="mode_audio")],
        [InlineKeyboardButton("🤖 Chat AI", callback_data="mode_ai"),
         InlineKeyboardButton("🎨 Buat Gambar", callback_data="mode_gambar")], # <-- Tombol baru
        [InlineKeyboardButton("🔄 Reset", callback_data="mode_reset")]
    ]
    return InlineKeyboardMarkup(keyboard)

def clean_url(url):
    return url.split("?")[0]

# ===== START COMMAND =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pesan = (
        "✨ *Ipun Bot PRO*\n\n"
        "Asisten pribadimu siap membantu!\n"
        "Silakan pilih mode di bawah ini 👇"
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
        await query.edit_message_text("🎬 **Mode Video Aktif.**\nKirim link video (IG/TikTok/YT).", parse_mode="Markdown", reply_markup=get_main_menu())
    
    elif data == "mode_audio":
        context.user_data["mode"] = "audio"
        await query.edit_message_text("🎧 **Mode MP3 Aktif.**\nKirim link untuk diconvert ke audio.", parse_mode="Markdown", reply_markup=get_main_menu())
    
    elif data == "mode_ai":
        context.user_data["mode"] = "ai"
        await query.edit_message_text("🤖 **Mode Chat AI Aktif.**\nSilakan kirim pertanyaanmu!", parse_mode="Markdown", reply_markup=get_main_menu())
        
    elif data == "mode_gambar": # <-- Mode baru
        context.user_data["mode"] = "gambar"
        await query.edit_message_text("🎨 **Mode Gambar Aktif.**\nKirim deskripsi gambar (pakai bahasa Inggris ya).\nContoh: *a cinematic shot of a futuristic city*", parse_mode="Markdown", reply_markup=get_main_menu())
    
    elif data == "mode_reset":
        context.user_data.clear()
        await query.edit_message_text("♻️ Sesi direset. Pilih mode baru:", reply_markup=get_main_menu())

# ===== MAIN HANDLER (PROSES LINK / PESAN) =====
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    mode = context.user_data.get("mode")

    # --- 1. JIKA BELUM PILIH MODE ---
    if not mode:
        await update.message.reply_text("💡 Pencet tombol /start dulu dan pilih mode ya!", reply_markup=get_main_menu())
        return

    # --- 2. LOGIKA DOWNLOAD VIDEO & AUDIO ---
    if text.startswith("http"):
        if mode not in ["video", "audio"]:
            await update.message.reply_text("⚠️ Aktifkan Mode Video/MP3 dulu kalau mau download link.")
            return

        url = clean_url(text)
        msg = await update.message.reply_text("⏳ Memproses link media...")

        try:
            if mode == "audio":
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': 'audio_output.%(ext)s',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    'quiet': True,
                    'no_warnings': True
                }
                await msg.edit_text("🎵 Mengunduh dan convert ke MP3...")
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    title = info.get("title", "Audio")
                
                audio_file = "audio_output.mp3"
                with open(audio_file, "rb") as f:
                    await update.message.reply_audio(f, title=title)
                if os.path.exists(audio_file): os.remove(audio_file)

            elif mode == "video":
                ydl_opts = {
                    'format': 'best',
                    'outtmpl': 'video_output.%(ext)s',
                    'quiet': True,
                    'no_warnings': True
                }
                await msg.edit_text("🎬 Mengunduh video...")
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    title = info.get("title", "Video")
                    filename = ydl.prepare_filename(info)
                
                with open(filename, "rb") as f:
                    await update.message.reply_video(f, caption=f"🎬 {title}")
                if os.path.exists(filename): os.remove(filename)

            await msg.delete()

        except Exception as e:
            print("ERROR DOWNLOAD:", e)
            await msg.edit_text("❌ Gagal. Pastikan link-nya benar atau server sedang sibuk.")
        return

    # --- 3. LOGIKA AI GROQ ---
    if mode == "ai":
        if text.startswith("http"): return 
        
        try:
            processing_msg = await update.message.reply_text("🤖 AI sedang berpikir...")
            
            url_groq = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
            payload = {
                "model": "llama-3.3-70b-versatile", 
                "messages": [{"role": "user", "content": text}]
            }
            
            response = requests.post(url_groq, headers=headers, json=payload)
            data = response.json()

            if 'choices' in data:
                jawaban_ai = data['choices'][0]['message']['content']
                batas_karakter = 4000
                if len(jawaban_ai) > batas_karakter:
                    await processing_msg.edit_text(jawaban_ai[:batas_karakter])
                    for i in range(batas_karakter, len(jawaban_ai), batas_karakter):
                        await update.message.reply_text(jawaban_ai[i:i+batas_karakter])
                else:
                    await processing_msg.edit_text(jawaban_ai)
            else:
                await processing_msg.edit_text("⚠️ Groq Error. Cek log.")
        
        except Exception as e:
            await processing_msg.edit_text("❌ Waduh, otak AI error.")

    # --- 4. LOGIKA PEMBUAT GAMBAR (PABRIK SENDIRI - CLOUDFLARE) ---
    if mode == "gambar":
        if text.startswith("http"): return 
        
        processing_msg = await update.message.reply_text("🎨 Pabrik Ipun sedang melukis... ⏳ (Cuma butuh beberapa detik!)")
        
        try:
            import urllib.parse
            # Mengamankan teks prompt biar aman masuk ke URL
            prompt_aman = urllib.parse.quote(text)
            
            # INI DIA LINK PABRIK PRIBADIMU! 🔥
            url_pabrik = f"https://ipun-pelukis.tipungsinoman.workers.dev/?prompt={prompt_aman}"
            
            # Panggil pabriknya (Nggak perlu kunci/API key lagi karena ini milikmu!)
            response = requests.get(url_pabrik)
            
            if response.status_code == 200:
                image_bytes = response.content
                image = io.BytesIO(image_bytes)
                image.name = 'hasil_gambar.jpg'
                
                # Kirim hasilnya ke Telegram!
                await update.message.reply_photo(
                    photo=image, 
                    caption=f"✨ **Ipun Bot PRO | Image Generation**\n\nVisual berhasil diproses berdasarkan instruksi:\n_{text}_", 
                    parse_mode="Markdown"
                )
                await processing_msg.delete()
            else:
                # Kalau error, pabriknya ngasih tau pesannya
                pesan_error = response.text
                await processing_msg.edit_text(f"❌ Pabrik lagi macet: {pesan_error}")
                
        except Exception as e:
            print("ERROR PABRIK GAMBAR:", e)
            await processing_msg.edit_text("❌ Gagal menghubungi pabrik. Cek terminal/Railway.")
# ===== RUNNING BOT =====
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_click)) 
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    
    print("Bot Ipun PRO (UI Baru + Gambar) Berjalan...")
    app.run_polling(drop_pending_updates=True)
