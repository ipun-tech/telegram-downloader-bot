import os, yt_dlp, requests, asyncio, io, subprocess, PyPDF2
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
        "mode_ai": ("ai", "🤖 **Mode Chat AI Aktif.**\nSilakan bertanya atau kirim Dokumen PDF!"),
        "mode_gambar": ("gambar", "🎨 **Mode Gambar Aktif.**\nKirim deskripsi visual (English)."),
        "mode_warna": ("warna", "🌈 **Mode Palet Warna Aktif.**\n\n📸 **Kirim Foto/Video** untuk mengekstrak warna.\n\n👇 Atau pakai **Referensi Palet Pro** ini:\n\n**1. Teal & Orange (Blockbuster)**\nHex: `#011936` | `#465362` | `#82A3A1` | `#E07A5F` | `#F4F1DE`\n\n**2. Cyberpunk (Neon Night)**\nHex: `#711C91` | `#EA00D9` | `#0ABDC6` | `#133E7C` | `#091833`\n\n**3. Moody Vintage (Retro / Kopi)**\nHex: `#2B3A24` | `#5A6650` | `#8C9A84` | `#D4D1C5` | `#8B5A33`\n\n*(💡 Tap Hex untuk copy ke CapCut/Photoshop)*"),
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

# --- 2. LOGIKA BACA PDF ---
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("mode") != "ai":
        await update.message.reply_text("🤖 Aktifkan **Mode Chat AI** dulu sebelum kirim dokumen PDF ya!", reply_markup=get_main_menu())
        return

    msg = await update.message.reply_text("📄 Sedang mengunduh dan membedah isi PDF... ⏳")
    user_id = update.effective_user.id
    
    try:
        # Download file PDF
        file_id = update.message.document.file_id
        file = await context.bot.get_file(file_id)
        path_pdf = f"temp_{user_id}.pdf"
        await file.download_to_drive(path_pdf)
        
        # Ekstrak Teks pakai PyPDF2
        teks_pdf = ""
        with open(path_pdf, "rb") as f:
            pdf = PyPDF2.PdfReader(f)
            # Batasi baca 15 halaman biar gak jebol
            jml_halaman = min(len(pdf.pages), 15) 
            for i in range(jml_halaman):
                teks_pdf += pdf.pages[i].extract_text() + "\n"
                
        if os.path.exists(path_pdf): os.remove(path_pdf)
        
        # --- DETEKTOR KERTAS KOSONG ---
        if not teks_pdf.strip():
            await msg.edit_text("❌ Waduh, aku nggak bisa baca teks di PDF ini. Kemungkinan besar ini PDF hasil scan (berupa gambar) atau teksnya dikunci. Coba kirim PDF teks biasa ya, Bos!")
            return
        
        # Siapkan History & Prompt
        history = user_chat_history.get(user_id, [])
        prompt_pdf = f"Bro, ini ada dokumen PDF nih:\n\n{teks_pdf}\n\nTolong bedah dan rangkum tugas atau materi ini pakai bahasa yang santai banget, luwes, dan gampang dicerna. Posisikan lu kayak temen tongkrongan yang lagi bantuin gue ngerjain tugas kampus. Bikin poin-poin utamanya aja, jangan pakai bahasa kaku atau bahasa robot ya!"
        
        # Masukin ke memori obrolan biar dia ingat lu habis kirim PDF
        history.append({"role": "user", "content": "Tolong rangkum dokumen PDF yang saya kirim ini."})
        if len(history) > 10: history = history[-10:]
        
        system_prompt = {
            "role": "system",
            "content": (
                "Kamu adalah Ipun Assistant, AI jenius dan asisten tech profesional. "
                "Jawablah dengan bahasa yang santai, asyik, dan tajam. "
                "ATURAN MUTLAK: JANGAN PERNAH membuat tabel (Markdown table dengan simbol '|'). "
                "Ganti SEMUA format tabel menjadi List Beruntun (bullet points) atau sub-judul. "
                "Jika melanggar, sistem akan error."
            )
        }
        
        # Gabung semua buat ditembak ke Groq (Sisipkan teks asli PDF khusus di pengiriman ini)
        pesan_ke_groq = [system_prompt] + history[:-1] + [{"role": "user", "content": prompt_pdf}]
        
        h = {"Authorization": f"Bearer {GROQ_API_KEY}"}
        p = {"model": "openai/gpt-oss-120b", "messages": pesan_ke_groq, "max_tokens": 3000}
        
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=h, json=p).json()
        
        if 'error' in r:
            raise Exception(f"Groq API Error: {r['error']['message']}")
            
        jawaban = r['choices'][0]['message']['content']
        
        history.append({"role": "assistant", "content": jawaban})
        user_chat_history[user_id] = history
        
        await msg.edit_text(jawaban[:4000], parse_mode="Markdown")
        
    except Exception as e:
        print(f"Error PDF: {e}")
        await msg.edit_text(f"❌ Gagal membedah PDF.\nPastikan filenya bukan hasil scan gambar/foto.\nDetail Error: {str(e)[:150]}")

# --- 3. LOGIKA TEKS (CHAT, GAMBAR, DOWNLOAD) ---
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
            # 1. TRIGGER BROWSING
            if text.lower().startswith("cari ") or text.lower().startswith("search "):
                query = text.split(" ", 1)[1]
                await msg.edit_text("🌐 Sedang menarik data akurat dari internet...")
                
                hasil_search = ""
                try:
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

            # 2. System Prompt
            system_prompt = {
                "role": "system",
                "content": (
                    "Kamu adalah Ipun Assistant, AI jenius dan asisten tech profesional. "
                    "Jawablah dengan bahasa yang santai, asyik, dan tajam. "
                    "ATURAN MUTLAK: JANGAN PERNAH membuat tabel (Markdown table dengan simbol '|'). "
                    "Ganti SEMUA format tabel menjadi List Beruntun (bullet points) atau sub-judul. "
                    "Jika melanggar, sistem akan error."
                )
            }
            
            # 3. Kelola Memory
            history = user_chat_history.get(user_id, [])
            history.append({"role": "user", "content": text})
            if len(history) > 10: history = history[-10:]
            
            pesan_ke_groq = [system_prompt] + history
            
            # 4. Tembak ke API Groq
            h = {"Authorization": f"Bearer {GROQ_API_KEY}"}
            p = {"model": "openai/gpt-oss-120b", "messages": pesan_ke_groq, "max_tokens": 3000}
            r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=h, json=p).json()
            
            if 'error' in r:
                raise Exception(f"Groq API Error: {r['error']['message']}")
                
            jawaban = r['choices'][0]['message']['content']
            
            # Bersihkan memory (agar text raksasa dari internet nggak tersimpan)
            if text_asli.lower().startswith("cari ") or text_asli.lower().startswith("search "):
                history[-1] = {"role": "user", "content": text_asli}
                
            history.append({"role": "assistant", "content": jawaban})
            user_chat_history[user_id] = history
            
            await msg.edit_text(jawaban[:4000], parse_mode="Markdown")
        except Exception as e: 
            print(f"Error AI: {e}")
            await msg.edit_text(f"❌ Otak AI sedang pusing.\nDetail Error: {str(e)[:150]}")

# ===== RUNNING BOT =====
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_click))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_media))
    app.add_handler(MessageHandler(filters.Document.PDF, handle_document)) # NEW: Sensor PDF
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    print("🚀 Ipun Bot PRO v5.3 (Super Edition) Online!")
    app.run_polling(drop_pending_updates=True)
