import telebot
import os
import re
import requests
from flask import Flask
import threading
import time

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Instagram Downloader Bot is running!", 200

TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    raise ValueError("❌ توکن یافت نشد!")

bot = telebot.TeleBot(TOKEN)

# ========== تابع دانلود نهایی ==========
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
        
        #  استفاده از API جایگزین (نیاز به کوکی نداره!)
        url = f"https://api.instagram.com/oembed?url=https://www.instagram.com/p/{shortcode}/"
        
        # این یه راه دیگه هست که با هدرهای درست کار می‌کنه
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        # استفاده از سایت third-party برای دانلود (رایگان و بدون کوکی)
        api_url = f"https://www.instagram.com/p/{shortcode}/?__a=1&__d=1"
        response = requests.get(api_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            media = data['graphql']['shortcode_media']
            
            if media.get('is_video', False):
                video_url = media.get('video_url')
                if video_url:
                    r = requests.get(video_url, stream=True)
                    if r.status_code == 200:
                        filename = f"{shortcode}.mp4"
                        with open(filename, 'wb') as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                f.write(chunk)
                        return filename, "✅ ویدیو دانلود شد!"
            else:
                image_url = media.get('display_url')
                if image_url:
                    r = requests.get(image_url)
                    if r.status_code == 200:
                        filename = f"{shortcode}.jpg"
                        with open(filename, 'wb') as f:
                            f.write(r.content)
                        return filename, "✅ عکس دانلود شد!"
        
        # اگر روش بالا جواب نداد، از yt-dlp استفاده کن
        return download_with_ytdlp(link)
        
    except Exception as e:
        return None, f"❌ خطا: {str(e)[:80]}"

def download_with_ytdlp(link):
    try:
        import yt_dlp
        
        ydl_opts = {
            'outtmpl': '%(id)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=True)
            if info:
                filename = ydl.prepare_filename(info)
                if os.path.exists(filename):
                    return filename, "✅ دانلود انجام شد!"
        return None, "❌ دانلود ناموفق!"
    except Exception as e:
        return None, f"❌ خطا: {str(e)[:80]}"

# ========== دستور استارت ==========
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, 
        "🤖 **ربات دانلودر اینستاگرام**\n\n"
        "📥 لینک رو بفرست تا دانلود کنم.\n\n"
        "مثال:\n"
        "`https://www.instagram.com/reel/ABC123/`\n"
        "`https://www.instagram.com/p/XYZ/`"
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
                bot.reply_to(message, f"❌ خطا: {str(e)}")
        else:
            bot.reply_to(message, result)
    else:
        bot.reply_to(message, "❌ لینک معتبر اینستاگرام بفرست!")

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
