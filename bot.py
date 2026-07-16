import telebot
import os
import re
import yt_dlp
from flask import Flask
import threading
import time

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 YouTube Downloader Bot is running!", 200

TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    raise ValueError("❌ توکن یافت نشد!")

bot = telebot.TeleBot(TOKEN)

# ========== تابع دانلود از یوتیوب ==========
def download_youtube(link, quality="high"):
    """
    دانلود ویدیو از یوتیوب
    quality: "high" برای کیفیت بالا, "low" برای کیفیت پایین
    """
    try:
        if not os.path.exists('downloads'):
            os.makedirs('downloads')
        
        # تنظیمات yt-dlp برای یوتیوب
        ydl_opts = {
            'outtmpl': 'downloads/%(title)s_%(id)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'no_check_certificate': True,
            'format': 'bestvideo[height<=720]+bestaudio/best[height<=720]' if quality == "high" else 'best[height<=480]',
            'merge_output_format': 'mp4',
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # دریافت اطلاعات
            info = ydl.extract_info(link, download=True)
            
            if info:
                # پیدا کردن فایل دانلود شده
                filename = ydl.prepare_filename(info)
                
                # اگه فایل با فرمت mp4 نباشه
                if not os.path.exists(filename):
                    for f in os.listdir('downloads'):
                        if info.get('id') and info['id'] in f:
                            return os.path.join('downloads', f), "✅ ویدیو دانلود شد!"
                
                return filename, "✅ ویدیو دانلود شد!"
        
        return None, "❌ دانلود ناموفق! لینک رو بررسی کن."
        
    except Exception as e:
        error_msg = str(e)
        if "Private" in error_msg:
            return None, "❌ این ویدیو خصوصی هست!"
        elif "unavailable" in error_msg.lower():
            return None, "❌ ویدیو در دسترس نیست!"
        else:
            return None, f"❌ خطا: {error_msg[:80]}"

# ========== تابع دانلود صوتی ==========
def download_audio(link):
    """دانلود فقط صدا از یوتیوب"""
    try:
        if not os.path.exists('downloads'):
            os.makedirs('downloads')
        
        ydl_opts = {
            'outtmpl': 'downloads/%(title)s_%(id)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=True)
            if info:
                filename = ydl.prepare_filename(info)
                # تبدیل به mp3
                mp3_filename = filename.rsplit('.', 1)[0] + '.mp3'
                if os.path.exists(mp3_filename):
                    return mp3_filename, "✅ آهنگ دانلود شد!"
                elif os.path.exists(filename):
                    return filename, "✅ آهنگ دانلود شد!"
        
        return None, "❌ دانلود ناموفق!"
        
    except Exception as e:
        return None, f"❌ خطا: {str(e)[:80]}"

# ========== کیبورد ==========
def main_keyboard():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("📹 دانلود ویدیو", "🎵 دانلود صدا")
    markup.add("⚙️ کیفیت بالا", "⚙️ کیفیت پایین")
    markup.add("📜 راهنما")
    return markup

# ========== دستور استارت ==========
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, 
        "🎬 **به ربات دانلودر یوتیوب خوش آمدی!**\n\n"
        "📥 لینک یوتیوب رو برام بفرست تا دانلود کنم.\n\n"
        "🔹 **قابلیت‌ها:**\n"
        "• دانلود ویدیو با کیفیت بالا/پایین\n"
        "• دانلود فقط صدا (MP3)\n"
        "• پشتیبانی از لینک‌های کوتاه (youtu.be)\n\n"
        "مثال:\n"
        "`https://www.youtube.com/watch?v=abc123`\n"
        "`https://youtu.be/abc123`",
        reply_markup=main_keyboard()
    )

# ========== دکمه‌ها ==========
@bot.message_handler(func=lambda m: m.text == "📹 دانلود ویدیو")
def video_download_btn(message):
    bot.reply_to(message, "📹 **لینک یوتیوب رو بفرست تا ویدیو رو دانلود کنم.**")

@bot.message_handler(func=lambda m: m.text == "🎵 دانلود صدا")
def audio_download_btn(message):
    bot.reply_to(message, "🎵 **لینک یوتیوب رو بفرست تا آهنگ رو دانلود کنم.**")

@bot.message_handler(func=lambda m: m.text == "⚙️ کیفیت بالا")
def quality_high(message):
    global QUALITY
    QUALITY = "high"
    bot.reply_to(message, "✅ **کیفیت بالا** فعال شد!")

@bot.message_handler(func=lambda m: m.text == "⚙️ کیفیت پایین")
def quality_low(message):
    global QUALITY
    QUALITY = "low"
    bot.reply_to(message, "✅ **کیفیت پایین** فعال شد!")

@bot.message_handler(func=lambda m: m.text == "📜 راهنما")
def help_btn(message):
    bot.reply_to(message,
        "📜 **راهنمای ربات یوتیوب دانلودر**\n\n"
        "1️⃣ لینک یوتیوب رو کپی کن\n"
        "2️⃣ توی ربات برام بفرست\n"
        "3️⃣ منتظر بمون تا دانلود بشه\n"
        "4️⃣ فایل برات ارسال میشه\n\n"
        "🔹 **دکمه‌ها:**\n"
        "• 📹 دانلود ویدیو: دانلود ویدیو با کیفیت انتخابی\n"
        "• 🎵 دانلود صدا: دانلود فقط آهنگ (MP3)\n"
        "• ⚙️ کیفیت بالا/پایین: انتخاب کیفیت ویدیو\n\n"
        "⚠️ **محدودیت‌ها:**\n"
        "• حجم فایل تا ۵۰ مگابایت (محدودیت تلگرام)\n"
        "• فقط لینک‌های عمومی"
    )

# ========== دریافت لینک ==========
QUALITY = "high"  # حالت پیش‌فرض

@bot.message_handler(func=lambda m: True)
def handle_message(message):
    text = message.text
    
    # بررسی لینک یوتیوب
    pattern = r'(https?://(?:www\.)?(?:youtube\.com|youtu\.be)/[\w\-/?=&]+)'
    match = re.search(pattern, text)
    
    if match:
        link = match.group(1)
        
        # تشخیص نوع درخواست
        is_audio = False
        if message.text and "صدا" in message.text or "آهنگ" in message.text:
            is_audio = True
        
        bot.reply_to(message, "⏳ در حال دانلود... لطفاً صبر کن")
        
        if is_audio:
            filename, result = download_audio(link)
        else:
            filename, result = download_youtube(link, QUALITY)
        
        if filename and os.path.exists(filename):
            try:
                # چک کردن حجم
                file_size = os.path.getsize(filename) / (1024 * 1024)
                if file_size > 50:
                    bot.reply_to(message, f"⚠️ حجم فایل {file_size:.1f} مگابایت هست که از محدودیت ۵۰ مگابایت تلگرام بیشتره!")
                    os.remove(filename)
                    return
                
                with open(filename, 'rb') as f:
                    if filename.endswith('.mp4'):
                        bot.send_video(message.chat.id, f, caption=result, supports_streaming=True)
                    elif filename.endswith('.mp3'):
                        bot.send_audio(message.chat.id, f, caption=result)
                    else:
                        bot.send_document(message.chat.id, f, caption=result)
                
                os.remove(filename)
                bot.reply_to(message, "✅ فایل با موفقیت ارسال شد!")
                
            except Exception as e:
                bot.reply_to(message, f"❌ خطا در ارسال: {str(e)[:80]}")
                if os.path.exists(filename):
                    os.remove(filename)
        else:
            bot.reply_to(message, result)
    else:
        bot.reply_to(message, 
            "❌ لطفاً یک لینک معتبر یوتیوب بفرست.\n\n"
            "مثال:\n"
            "`https://www.youtube.com/watch?v=abc123`\n"
            "`https://youtu.be/abc123`",
            parse_mode='Markdown'
        )

# ========== اجرا ==========
if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 10000))
    
    if not os.path.exists('downloads'):
        os.makedirs('downloads')
    
    print("🎬 ربات دانلودر یوتیوب روشن شد!")
    
    try:
        bot.remove_webhook()
    except:
        pass
    
    time.sleep(1)
    
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)).start()
    
    bot.infinity_polling()
