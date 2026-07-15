import telebot
from telebot import types
import os
import time
import re
from flask import Flask
import threading
from instagrapi import Client

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Instagram Downloader Bot is running!", 200

TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    raise ValueError("❌ توکن یافت نشد!")

bot = telebot.TeleBot(TOKEN)

# ========== اطلاعات اکانت اینستاگرام ==========
INSTA_USERNAME = "Deer.5656308"
INSTA_PASSWORD = "depp12345678910109876543211213141516171819110"

# ========== راه‌اندازی کلاینت اینستاگرام ==========
def get_client():
    cl = Client()
    cl.set_user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    try:
        cl.login(INSTA_USERNAME, INSTA_PASSWORD)
        print(f"✅ لاگین موفق! کاربر: {INSTA_USERNAME}")
        return cl
    except Exception as e:
        print(f"❌ خطا در لاگین: {e}")
        return None

instagram = get_client()

# ========== تابع دانلود ==========
def download_instagram(link):
    global instagram
    
    try:
        if instagram is None:
            instagram = get_client()
            if instagram is None:
                return None, "❌ اتصال به اینستاگرام برقرار نشد!"
        
        # گرفتن shortcode
        shortcode = None
        if '/reel/' in link:
            shortcode = link.split('/reel/')[1].split('/')[0]
        elif '/p/' in link:
            shortcode = link.split('/p/')[1].split('/')[0]
        else:
            return None, "❌ لینک معتبر نیست!"
        
        if not shortcode:
            return None, "❌ لینک معتبر نیست!"
        
        # دریافت اطلاعات
        media_id = instagram.media_id(shortcode)
        info = instagram.media_info(media_id)
        
        # دانلود
        if info.media_type == 1:  # عکس
            filename = f"{shortcode}.jpg"
            instagram.photo_download(media_id, filename)
            return filename, "✅ عکس دانلود شد!"
        elif info.media_type == 2:  # ویدیو
            filename = f"{shortcode}.mp4"
            instagram.video_download(media_id, filename)
            return filename, "✅ ویدیو دانلود شد!"
        else:
            return None, "❌ نوع محتوا پشتیبانی نمی‌شود!"
            
    except Exception as e:
        return None, f"❌ خطا: {str(e)[:80]}"

# ========== دستور استارت ==========
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, 
        "🤖 **به ربات دانلودر اینستاگرام خوش آمدی!**\n\n"
        "📥 لینک پست یا ریلز اینستاگرام رو برام بفرست تا دانلودش کنم.\n\n"
        "مثال:\n"
        "`https://www.instagram.com/reel/ABC123/`\n"
        "`https://www.instagram.com/p/XYZ/`",
        parse_mode='Markdown'
    )

# ========== دریافت لینک ==========
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    text = message.text
    
    pattern = r'(https?://(?:www\.)?instagram\.com/[\w\-/]+)'
    match = re.search(pattern, text)
    
    if match:
        link = match.group(1)
        bot.reply_to(message, "⏳ در حال دانلود...")
        
        filename, result = download_instagram(link)
        
        if filename and os.path.exists(filename):
            try:
                with open(filename, 'rb') as f:
                    if filename.endswith('.mp4'):
                        bot.send_video(message.chat.id, f, caption=result)
                    else:
                        bot.send_photo(message.chat.id, f, caption=result)
                os.remove(filename)
            except Exception as e:
                bot.reply_to(message, f"❌ خطا در ارسال: {str(e)}")
        else:
            bot.reply_to(message, result)
    else:
        bot.reply_to(message, 
            "❌ لطفاً یک لینک معتبر اینستاگرام بفرست.\n\n"
            "مثال:\n"
            "`https://www.instagram.com/reel/ABC123/`",
            parse_mode='Markdown'
        )

# ========== اجرا ==========
if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 10000))
    
    try:
        bot.remove_webhook()
    except:
        pass
    
    time.sleep(1)
    
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)).start()
    
    bot.infinity_polling()
