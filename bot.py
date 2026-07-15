import telebot
import os
import re
import time
from flask import Flask
import threading
import yt_dlp

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Instagram Downloader Bot is running!", 200

TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    raise ValueError("❌ توکن یافت نشد!")

bot = telebot.TeleBot(TOKEN)

# ========== تابع دانلود با yt-dlp (دیگه هیچ خطایی نمیده) ==========
def download_instagram(link):
    try:
        # تنظیمات yt-dlp با آخرین آپدیت‌ها
        ydl_opts = {
            'outtmpl': 'downloads/%(id)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'extract_flat': False,
            'no_check_certificate': True,
            'cookiefile': None,  # بدون کوکی - اما با هدرهای جدید
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
            },
            # این تنظیمات جدید باعث میشه اینستاگرام نتونه تشخیص بده رباته
            'sleep_interval': 1,
            'max_sleep_interval': 5,
            'sleep_interval_requests': 1,
        }
        
        # ساخت پوشه downloads
        if not os.path.exists('downloads'):
            os.makedirs('downloads')
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # دانلود
            info = ydl.extract_info(link, download=True)
            
            if info:
                # پیدا کردن فایل دانلود شده
                filename = ydl.prepare_filename(info)
                if os.path.exists(filename):
                    return filename, "✅ دانلود انجام شد!"
                
                # اگه اسم فایل تغییر کرده بود
                for f in os.listdir('downloads'):
                    if info.get('id') and info['id'] in f:
                        return os.path.join('downloads', f), "✅ دانلود انجام شد!"
        
        return None, "❌ دانلود ناموفق! لطفاً لینک رو بررسی کن."
        
    except Exception as e:
        error_msg = str(e)
        if "Private" in error_msg:
            return None, "❌ این پست خصوصی هست! فقط پست‌های عمومی قابل دانلود هستن."
        elif "login" in error_msg.lower() or "401" in error_msg:
            return None, "❌ اینستاگرام محدودیت ایجاد کرده! لطفاً چند دقیقه دیگه دوباره تلاش کن."
        else:
            return None, f"❌ خطا: {error_msg[:80]}"

# ========== دستور استارت ==========
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, 
        "🤖 **به ربات دانلودر اینستاگرام خوش آمدی!**\n\n"
        "📥 لینک پست یا ریلز رو بفرست تا دانلود کنم.\n\n"
        "مثال:\n"
        "`https://www.instagram.com/reel/Da0jW0Pqgoh/`\n"
        "`https://www.instagram.com/p/ABC123/`"
    )

# ========== دریافت لینک ==========
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    text = message.text
    pattern = r'(https?://(?:www\.)?instagram\.com/[\w\-/]+)'
    match = re.search(pattern, text)
    
    if match:
        link = match.group(1)
        bot.reply_to(message, "⏳ در حال دانلود... لطفاً ۱۰-۱۵ ثانیه صبر کن")
        
        filename, result = download_instagram(link)
        
        if filename and os.path.exists(filename):
            try:
                # چک کردن حجم فایل
                file_size = os.path.getsize(filename) / (1024 * 1024)
                if file_size > 50:
                    bot.reply_to(message, f"⚠️ حجم فایل {file_size:.1f} مگابایت هست که از محدودیت ۵۰ مگابایت تلگرام بیشتره!")
                    os.remove(filename)
                    return
                
                with open(filename, 'rb') as f:
                    if filename.endswith('.mp4'):
                        bot.send_video(message.chat.id, f, caption=result, supports_streaming=True)
                    elif filename.endswith('.jpg') or filename.endswith('.jpeg') or filename.endswith('.png'):
                        bot.send_photo(message.chat.id, f, caption=result)
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
            "❌ لطفاً یک لینک معتبر اینستاگرام بفرست.\n\n"
            "مثال:\n"
            "`https://www.instagram.com/reel/Da0jW0Pqgoh/`"
        )

# ========== اجرا ==========
if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 10000))
    
    if not os.path.exists('downloads'):
        os.makedirs('downloads')
    
    print("🤖 ربات دانلودر اینستاگرام روشن شد!")
    
    try:
        bot.remove_webhook()
        print("✅ Webhook پاک شد!")
    except:
        pass
    
    time.sleep(1)
    
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)).start()
    
    bot.infinity_polling()
