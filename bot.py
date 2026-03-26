import os, yt_dlp, requests, asyncio, io, subprocess
from colorthief import ColorThief
from static_ffmpeg import add_paths
add_paths() 

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# ===== CONFIG =====
TOKEN = os.getenv("TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# MEMORY: Simpan history obrolan (max 10 pesan) per user
user_chat_history = {}

# ===== UI: MENU UTAMA =====
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
    user_id = update.effective_user.id
    user_chat_history[user_id] = [] # Reset history saat start/reset
    
    pesan = "✨ **Ipun Bot PRO v5.3 (Memory Edition)**\n\nAsisten digitalmu sudah siap. Silakan pilih mode di bawah ini: 👇"
    if update.message:
        await update.message.reply_text(pesan, parse_mode="Markdown", reply_markup=get_main_menu())

# ===== HANDLER KLIK TOMBOL =====
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() 
    data = query.data
    user_id = query.from_user.id
    
    modes = {
        "mode_video": ("video", "🎬 **Mode Video Aktif.**\nKirim link video (IG/TikTok/YT)."),
        "mode_audio": ("audio", "🎧 **Mode MP3 Aktif.**\nKirim link media."),
        "mode_ai": ("ai", "🤖 **Mode Chat AI Aktif.**\nSilakan bertanya!"),
        "mode_gambar": ("gambar", "🎨 **Mode Gambar Aktif.**\nKirim deskripsi visual (English)."),
        "mode_warna": ("warna", "🌈 **Mode Palet Warna Aktif.**\nKirim Foto/Video!"),
        "mode_reset": (None, "♻️ **Sesi direset.** Pilih mode baru:")
    }
    
    mode, msg = modes.get(data, (None, ""))
    if mode: 
        context.user_data["mode"] = mode
        if mode == "ai": user_chat_history[user_id] = [] # Reset history saat masuk mode AI
    else: 
        context.user_data.clear()
        user_chat_history[user_id] = [] # Reset history saat reset
    
    await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=get_main_menu())

# --- 1. LOGIKA MEDIA (WARNA) ---
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("mode") != "warna":
        await update.message.reply_text("💡 Aktifkan **Mode Palet Warna** dulu ya!", reply_markup=get_main_menu())
        return
    msg = await update.message.reply_text("🕵️ Menganalisis palet warna... ⏳")
    try:
        file_id = update.message.photo[-1].file_id if update.message.photo else update.message.video.file_id
        file = await context.bot.get_file(file_id)
        path_in = "temp_in"
        await file.download_to_drive(path_in)
        path_out = "frame.jpg"
        if update.message.video:
            subprocess.run(['ffmpeg', '-y', '-i', path_in, '-ss', '00:00:01', '-vframes', '1', path_out], check=True)
        else: path_out = path_in
        palette = ColorThief(path_out).get_palette(color_count=5, quality=1)
        res = "🎨 **Cinematic Color Palette Found!**\n\n"
        for i, rgb in enumerate(palette):
            res += f"{i+1}. `{'#%02x%02x%02x' % rgb}` 🟦\n"
        await msg.edit_text(res + "\n*Tips:* Gunakan HEX ini di CapCut/Photoshop! 🚀", parse_mode="Markdown")
        for f in [path_in, "frame.jpg"]:
            if os.path.exists(f): os.remove(f)
    except: await msg.edit_text("❌ Gagal mengekstrak warna.")

# --- 2. LOGIKA TEKS (CHAT, GAMBAR, DOWNLOAD) ---
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    mode = context.user_data.get("mode")
    user_id = update.effective_user.id
    
    if not mode: return await update.message.reply_text("💡 Pilih mode dulu di /start!", reply_markup=get_main_menu())

    # A. LOGIKA DOWNLOAD
    if text.startswith("http"):
        if mode not in ["video", "audio"]: return await update.message.reply_text("⚠️ Aktifkan Mode Video/MP3 dulu.")
        msg = await update.message.reply_text("⏳ Memproses link...")
        try:
            if mode == "audio":
                with yt_dlp.YoutubeDL({'format':'bestaudio','outtmpl':'out.mp3','postprocessors':[{'key':'FFmpegExtractAudio','preferredcodec':'mp3'}]}) as ydl:
                    ydl.download([text])
                await update.message.reply_audio(open("out.mp3", "rb"))
                os.remove("out.mp3")
            elif mode == "video":
                with yt_dlp.YoutubeDL({'format':'best','outtmpl':'out.mp4'}) as ydl:
                    ydl.download([text])
                await update.message.reply_video(open("out.mp4", "rb"))
                os.remove("out.mp4")
            await msg.delete()
        except: await msg.edit_text("❌ Gagal download.")
        return
    
    # B. LOGIKA BUAT GAMBAR
    elif mode == "gambar":
        msg = await update.message.reply_text("🎨 Pabrik sedang melukis... ⏳")
        try:
            r = requests.get(f"https://ipun-pelukis.tipungsinoman.workers.dev/?prompt={text}")
            await update.message.reply_photo(io.BytesIO(r.content), caption=f"✨Super Bot PRO | Image Generation\nPrompt: {text}")
            await msg.delete()
        except: await msg.edit_text("❌ Pabrik gambar macet.")

    # C. LOGIKA CHAT AI (GROQ DENGAN MEMORY) 🧠
    elif mode == "ai":
        msg = await update.message.reply_text("🤖 Berpikir...")
        try:
            # 1. Ambil History Obrolan User
            history = user_chat_history.get(user_id, [])
            
            # 2. Tambahkan Pesan Baru ke History
            history.append({"role": "user", "content": text})
            
            # 3. Batasi History (Max 10 pesan terakhir) biar server nggak berat
            if len(history) > 10: history = history[-10:]
            
            # 4. Kirim History Lengkap ke Groq AI
            h = {"Authorization": f"Bearer {GROQ_API_KEY}"}
            p = {"model": "llama-3.3-70b-versatile", "messages": history}
            r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=h, json=p).json()
            
            # 5. Ambil Jawaban AI
            jawaban = r['choices'][0]['message']['content']
            
            # 6. Tambahkan Jawaban AI ke History
            history.append({"role": "assistant", "content": jawaban})
            user_chat_history[user_id] = history
            
            # 7. Kirim Jawaban ke Telegram
            await msg.edit_text(jawaban[:4000])
        except: await msg.edit_text("❌ Otak AI sedang error.")

# ===== RUNNING BOT =====
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_click))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_media))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    print("🚀 Ipun Bot PRO v5.3 (Memory Edition) Online!")
    app.run_polling(drop_pending_updates=True)
