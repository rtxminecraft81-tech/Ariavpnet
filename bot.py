import telebot
import os
import re
import requests
from flask import Flask
import threading
import time
import json

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Instagram Downloader Bot is running!", 200

TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    raise ValueError("❌ توکن یافت نشد!")

bot = telebot.TeleBot(TOKEN)

# ========== تابع دانلود با API ==========
def download_instagram(link):
    try:
        # استخراج shortcode
        shortcode = None
        if '/reel/' in link:
            shortcode = link.split('/reel/')[1].split('/')[0]
        elif '/p/' in link:
            shortcode = link.split('/p/')[1].split('/')[0]
        else:
            return None, "❌ لینک معتبر نیست!"
        
        if not shortcode:
            return None, "❌ لینک معتبر نیست!"
        
        # استفاده از API رایگان
        api_url = f"https://api.instagram.com/oembed?url=https://www.instagram.com/p/{shortcode}/"
        response = requests.get(api_url, timeout=10)
        
        if response.status_code != 200:
            # روش دوم: استفاده از سایت third-party
            return download_from_third_party(shortcode)
        
        # روش سوم: استفاده از یه API دیگه
        return download_from_alternative_api(shortcode)
        
    except Exception as e:
        return None, f"❌ خطا: {str(e)[:80]}"

def download_from_third_party(shortcode):
    """دانلود از طریق سایت third-party"""
    try:
        # استفاده از yt-dlp با تنظیمات ساده
        import yt_dlp
        
        ydl_opts = {
            'outtmpl': f'downloads/{shortcode}.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
        }
        
        url = f"https://www.instagram.com/p/{shortcode}/"
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info:
                # پیدا کردن فایل
                for ext in ['.mp4', '.jpg', '.png']:
                    filename = f"downloads/{shortcode}{ext}"
                    if os.path.exists(filename):
                        return filename, "✅ دانلود انجام شد!"
        
        return None, "❌ دانلود ناموفق! لطفاً لینک رو بررسی کن."
        
    except Exception as e:
        return None, f"❌ خطا: {str(e)[:80]}"

def download_from_alternative_api(shortcode):
    """دانلود با استفاده از API جایگزین (نیاز به کوکی نداره)"""
    try:
        # استفاده از سایت snaptik یا جایگزین
        urls = [
            f"https://www.instagram.com/p/{shortcode}/?__a=1",
            f"https://i.instagram.com/api/v1/media/{shortcode}/info/",
        ]
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
        }
        
        for url in urls:
            try:
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    # استخراج لینک ویدیو یا عکس
                    if 'graphql' in data:
                        media = data['graphql']['shortcode_media']
                        if media.get('is_video', False):
                            video_url = media.get('video_url')
                            if video_url:
                                r = requests.get(video_url, stream=True)
                                if r.status_code == 200:
                                    filename = f"downloads/{shortcode}.mp4"
                                    with open(filename, 'wb') as f:
                                        for chunk in r.iter_content(chunk_size=8192):
                                            f.write(chunk)
                                    return filename, "✅ ویدیو دانلود شد!"
                        else:
                            image_url = media.get('display_url')
                            if image_url:
                                r = requests.get(image_url)
                                if r.status_code == 200:
                                    filename = f"downloads/{shortcode}.jpg"
                                    with open(filename, 'wb') as f:
                                        f.write(r.content)
                                    return filename, "✅ عکس دانلود شد!"
            except:
                continue
        
        return None, "❌ دانلود ناموفق! لطفاً لینک رو بررسی کن."
        
    except Exception as e:
        return None, f"❌ خطا: {str(e)[:80]}"

# ========== دستور استارت ==========
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, 
        "🤖 **ربات دانلودر اینستاگرام**\n\n"
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
        bot.reply_to(message, "⏳ در حال دانلود... لطفاً صبر کن")
        
        filename, result = download_instagram(link)
        
        if filename and os.path.exists(filename):
            try:
                with open(filename, 'rb') as f:
                    if filename.endswith('.mp4'):
                        bot.send_video(message.chat.id, f, caption=result)
                    else:
                        bot.send_photo(message.chat.id, f, caption=result)
                os.remove(filename)
                bot.reply_to(message, "✅ فایل با موفقیت ارسال شد!")
            except Exception as e:
                bot.reply_to(message, f"❌ خطا در ارسال: {str(e)}")
                if os.path.exists(filename):
                    os.remove(filename)
        else:
            bot.reply_to(message, result)
    else:
        bot.reply_to(message, "❌ لینک معتبر اینستاگرام بفرست!")

# ========== اجرا ==========
if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 10000))
    
    if not os.path.exists('downloads'):
        os.makedirs('downloads')
    
    print("🤖 ربات روشن شد!")
    
    try:
        bot.remove_webhook()
    except:
        pass
    
    time.sleep(1)
    
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)).start()
    
    bot.infinity_polling()
