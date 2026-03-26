import os, yt_dlp, requests, asyncio, io, subprocess
from colorthief import ColorThief
from static_ffmpeg import add_paths
add_paths() 

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

TOKEN = os.getenv("TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pesan = "✨ **Ipun Bot PRO v5.1 (Light Edition)**\n\nAsisten digitalmu siap beraksi! Pilih mode di bawah: 👇"
    if update.message:
        await update.message.reply_text(pesan, parse_mode="Markdown", reply_markup=get_main_menu())

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() 
    data = query.data
    modes = {
        "mode_video": ("video", "🎬 **Mode Video Aktif.**\nKirim link video."),
        "mode_audio": ("audio", "🎧 **Mode MP3 Aktif.**\nKirim link media."),
        "mode_ai": ("ai", "🤖 **Mode Chat AI Aktif.**\nSilakan bertanya!"),
        "mode_gambar": ("gambar", "🎨 **Mode Gambar Aktif.**\nKirim deskripsi (English)."),
        "mode_warna": ("warna", "🌈 **Mode Palet Warna Aktif.**\nKirim Foto/Video iPhone-mu!"),
        "mode_reset": (None, "♻️ **Sesi direset.** Pilih mode baru:")
    }
    mode, msg = modes.get(data, (None, ""))
    if mode: context.user_data["mode"] = mode
    else: context.user_data.clear()
    await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=get_main_menu())

# --- LOGIKA MEDIA (PAKAI FFMPEG, TANPA OPENCV) ---
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("mode") != "warna":
        await update.message.reply_text("💡 Pilih **Mode Palet Warna** dulu ya!", reply_markup=get_main_menu())
        return

    msg = await update.message.reply_text("🕵️ Menganalisis warna sinematik... ⏳")
    try:
        file_id = update.message.photo[-1].file_id if update.message.photo else update.message.video.file_id
        file = await context.bot.get_file(file_id)
        path_input = "in_media"
        await file.download_to_drive(path_input)
        path_extract = "frame.jpg"

        if update.message.video:
            # PAKE JURUS FFMPEG (Lebih sakti & ringan dari OpenCV)
            subprocess.run(['ffmpeg', '-y', '-i', path_input, '-ss', '00:00:01', '-vframes', '1', path_extract], check=True)
        else:
            path_extract = path_input

        palette = ColorThief(path_extract).get_palette(color_count=5, quality=1)
        res = "🎨 **Cinematic Color Palette Found!**\n\n"
        for i, rgb in enumerate(palette):
            res += f"{i+1}. `{'#%02x%02x%02x' % rgb}` 🟦\n"
        
        await msg.edit_text(res + "\n*Tips:* Gunakan HEX ini di CapCut/Photoshop! 🚀", parse_mode="Markdown")
        for f in [path_input, "frame.jpg"]:
            if os.path.exists(f): os.remove(f)
    except Exception as e:
        print(e)
        await msg.edit_text("❌ Gagal ekstrak warna.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    mode = context.user_data.get("mode")
    if not mode: return await update.message.reply_text("💡 Pilih mode dulu!", reply_markup=get_main_menu())

    if text.startswith("http"):
        msg = await update.message.reply_text("⏳ Memproses...")
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
    
    elif mode == "gambar":
        msg = await update.message.reply_text("🎨 Melukis dulu... ⏳")
        try:
            r = requests.get(f"https://ipun-pelukis.tipungsinoman.workers.dev/?prompt={text}")
            await update.message.reply_photo(io.BytesIO(r.content), caption=f"✨ **Ipun AI Engine**\nPrompt: {text}")
            await msg.delete()
        except: await msg.edit_text("❌ Pabrik macet.")

    elif mode == "ai":
        msg = await update.message.reply_text("🤖 Berpikir...")
        try:
            h = {"Authorization": f"Bearer {GROQ_API_KEY}"}
            p = {"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": text}]}
            r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=h, json=p).json()
            await msg.edit_text(r['choices'][0]['message']['content'][:4000])
        except: await msg.edit_text("❌ Groq Error.")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_click))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_media))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    print("🚀 Bot Ipun Light v5.1 Ready!")
    app.run_polling(drop_pending_updates=True)
