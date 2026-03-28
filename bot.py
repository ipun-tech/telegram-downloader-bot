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
    
    pesan = "✨ **Ipun Bot PRO v5.3**\n\nAsisten digitalmu sudah siap. Silakan pilih mode di bawah ini: 👇"
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

    # A. LOGIKA DOWNLOAD (VIDEO & AUDIO)
    if text.startswith("http"):
        if mode not in ["video", "audio"]: 
            return await update.message.reply_text("⚠️ Aktifkan Mode Video/MP3 dulu.")
        
        msg = await update.message.reply_text("⏳ Memproses link...")
        try:
            # --- MODE AUDIO (METADATA PRO) ---
            if mode == "audio":
                opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': 'out.%(ext)s',
                    'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}],
                    'quiet': True
                }
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(text, download=True)
                    judul = info.get('title', 'Audio Ipun Bot')
                    penyanyi = info.get('uploader', 'Unknown Artist')
                
                await update.message.reply_audio(
                    audio=open("out.mp3", "rb"),
                    title=judul, performer=penyanyi, filename=f"{judul}.mp3"
                )
                if os.path.exists("out.mp3"): os.remove("out.mp3")

            # --- MODE VIDEO (CAPTION PRO) ---
            elif mode == "video":
                opts = {'format': 'best', 'outtmpl': 'out.mp4', 'quiet': True}
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(text, download=True)
                    judul = info.get('title', 'Video Ipun Bot')
                    kreator = info.get('uploader', 'Unknown Creator')
                    link_asli = info.get('webpage_url', text)
                
                caption_teks = f"🎬 **{judul}**\n👤 Creator: `{kreator}`\n\n🔗 [Original Link]({link_asli})"
                
                await update.message.reply_video(
                    video=open("out.mp4", "rb"),
                    caption=caption_teks, parse_mode="Markdown"
                )
                if os.path.exists("out.mp4"): os.remove("out.mp4")
                
            await msg.delete()
        except Exception as e:
            print(f"Download Error: {e}")
            await msg.edit_text("❌ Gagal download.")
        return
    
    # B. LOGIKA BUAT GAMBAR
    elif mode == "gambar":
        msg = await update.message.reply_text("🎨 Pabrik sedang melukis... ⏳")
        try:
            r = requests.get(f"https://ipun-pelukis.tipungsinoman.workers.dev/?prompt={text}")
            await update.message.reply_photo(io.BytesIO(r.content), caption=f"Ipun Bot PRO | Image Generation\nPrompt: {text}")
            await msg.delete()
        except: await msg.edit_text("❌ Pabrik gambar macet.")

    # C. LOGIKA CHAT AI (GROQ DENGAN MEMORY & WEB SEARCH)
    elif mode == "ai":
        msg = await update.message.reply_text("🤖 Berpikir...")
        try:
            text_asli = text
            # 1. TRIGGER BROWSING: Kalau chat dimulai dengan "cari " atau "search "
            if text.lower().startswith("cari ") or text.lower().startswith("search "):
                query = text.split(" ", 1)[1] # Ambil kata kunci
                await msg.edit_text("🌐 Sedang menarik data akurat dari internet...")
                
                # Proses Browsing Tavily
                hasil_search = ""
                try:
                    import os
                    import requests
                    import datetime
                    
                    tavily_key = os.environ.get("TAVILY_API_KEY", "")
                    if tavily_key:
                        payload = {"api_key": tavily_key, "query": query, "search_depth": "basic", "include_answer": False, "max_results": 3}
                        res = requests.post("https://api.tavily.com/search", json=payload).json()
                        for item in res.get('results', []):
                            hasil_search += f"- Sumber: {item.get('url', '')}\n  Isi: {item.get('content', '')}\n\n"
                    else:
                        hasil_search = "Data internet kosong karena API Key Tavily tidak ada."
                        
                    hari_ini = datetime.datetime.now().strftime("%d %B %Y")
                    text = f"Hari ini tanggal {hari_ini}. Tolong jawab pertanyaanku: '{text_asli}'. Ini data dari internet:\n\n{hasil_search}\n\nJawab STRICT berdasarkan data di atas."
                except Exception as e:
                    print(f"Error Tavily: {e}")
                    text = f"Tolong jawab: '{text_asli}'. (Catatan: internet sedang error)."

            # 2. System Prompt (Kepribadian)
            system_prompt = {
                "role": "system",
                "content": "Kamu adalah Ipun Assistant, AI jenius dan asisten tech profesional. Jawablah dengan bahasa yang santai, asyik, dan tajam."
            }
            
            # 3. Kelola Memory
            history = user_chat_history.get(user_id, [])
            history.append({"role": "user", "content": text})
            if len(history) > 10: history = history[-10:] # Batasi memori biar nggak kepenuhan
            
            # Gabung System Prompt + History
            pesan_ke_groq = [system_prompt] + history
            
            # 4. Tembak ke API Groq
            import requests # Pastikan tools ini aktif untuk manggil Groq
            h = {"Authorization": f"Bearer {GROQ_API_KEY}"}
            p = {"model": "llama-3.3-70b-versatile", "messages": pesan_ke_groq}
            r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=h, json=p).json()
            
            # Sinar-X: Cek apakah Groq menolak memproses
            if 'error' in r:
                raise Exception(f"Groq API Error: {r['error']['message']}")
                
            jawaban = r['choices'][0]['message']['content']
            
            # Bersihkan memory (agar text raksasa dari internet nggak tersimpan di riwayat)
            if text_asli.lower().startswith("cari ") or text_asli.lower().startswith("search "):
                history[-1] = {"role": "user", "content": text_asli}
                
            history.append({"role": "assistant", "content": jawaban})
            user_chat_history[user_id] = history
            
            await msg.edit_text(jawaban[:4000])
        except Exception as e: 
            print(f"Error AI: {e}")
            # Bot akan memunculkan detail errornya ke Telegram!
            await msg.edit_text(f"❌ Otak AI sedang pusing.\nDetail Error: {str(e)[:150]}")

# ===== RUNNING BOT =====
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_click))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_media))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    print("🚀 Ipun Bot PRO v5.3 (Memory Edition) Online!")
    app.run_polling(drop_pending_updates=True)
