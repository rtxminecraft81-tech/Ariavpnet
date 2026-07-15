import telebot
from telebot import types
import json
import os
import time
from datetime import datetime
from flask import Flask
import threading
import re
import requests

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Instagram Downloader Bot is running!", 200

TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    raise ValueError("❌ توکن یافت نشد! لطفاً BOT_TOKEN را در Render تنظیم کنید.")

ADMIN_ID = '6795169616'
CHANNEL_USERNAME = '@hegzo_vpn_channle'

bot = telebot.TeleBot(TOKEN)
USER_DB = 'users.json'

# ========== بخش کاربران ==========
def load_users():
    if os.path.exists(USER_DB):
        with open(USER_DB, 'r') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USER_DB, 'w') as f:
        json.dump(users, f, indent=4)

def init_user(user_id, username=""):
    if str(user_id) not in users:
        users[str(user_id)] = {
            'username': username,
            'joined_at': str(datetime.now())
        }
        save_users(users)

users = load_users()

# ========== بررسی عضویت در کانال ==========
def is_member(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

# ========== کیبورد اصلی ==========
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("📥 دانلود از اینستاگرام")
    markup.add("📜 راهنما", "👤 حساب من")
    markup.add("🆘 پشتیبانی")
    return markup

# ========== تابع دانلود با API ==========
def download_instagram(link):
    """دانلود با استفاده از API رایگان"""
    try:
        # استخراج shortcode از لینک
        shortcode = None
        if '/p/' in link:
            shortcode = link.split('/p/')[1].split('/')[0]
        elif '/reel/' in link:
            shortcode = link.split('/reel/')[1].split('/')[0]
        elif '/tv/' in link:
            shortcode = link.split('/tv/')[1].split('/')[0]
        elif '/stories/' in link:
            # برای استوری باید روش دیگه استفاده بشه
            return download_story(link)
        
        if not shortcode:
            return None, "❌ لینک معتبر نیست!"
        
        # استفاده از API اینستاگرام (با هدرهای جدید)
        url = f"https://www.instagram.com/p/{shortcode}/?__a=1&__d=1"
        
        headers = {
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
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'graphql' in data and 'shortcode_media' in data['graphql']:
                media = data['graphql']['shortcode_media']
                
                # چک کردن محتوا
                if media.get('is_video', False):
                    video_url = media.get('video_url')
                    if video_url:
                        # دانلود ویدیو
                        video_response = requests.get(video_url, stream=True, timeout=30)
                        if video_response.status_code == 200:
                            if not os.path.exists('downloads'):
                                os.makedirs('downloads')
                            filename = f"downloads/instagram_{shortcode}.mp4"
                            with open(filename, 'wb') as f:
                                for chunk in video_response.iter_content(chunk_size=8192):
                                    if chunk:
                                        f.write(chunk)
                            return filename, "✅ ویدیو دانلود شد!"
                else:
                    # عکس (میتونه چندتا عکس باشه)
                    if 'edge_sidecar_to_children' in media:
                        # چندتا عکس
                        edges = media['edge_sidecar_to_children']['edges']
                        image_urls = [edge['node']['display_url'] for edge in edges]
                        # فقط اولین عکس رو دانلود کن
                        image_url = image_urls[0]
                    else:
                        image_url = media.get('display_url')
                    
                    if image_url:
                        image_response = requests.get(image_url, timeout=30)
                        if image_response.status_code == 200:
                            if not os.path.exists('downloads'):
                                os.makedirs('downloads')
                            filename = f"downloads/instagram_{shortcode}.jpg"
                            with open(filename, 'wb') as f:
                                f.write(image_response.content)
                            return filename, "✅ عکس دانلود شد!"
        
        # اگه روش بالا جواب نداد، از روش دوم استفاده کن
        return download_with_alternate(link)
        
    except Exception as e:
        return None, f"❌ خطا: {str(e)[:100]}"

# ========== روش جایگزین برای دانلود ==========
def download_with_alternate(link):
    """روش دوم دانلود با استفاده از سایت third-party"""
    try:
        # استفاده از API جایگزین (سرویس رایگان)
        api_url = "https://api.instagram.com/oembed"
        params = {'url': link}
        response = requests.get(api_url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            # این API فقط اطلاعات رو میده، پس از yt-dlp استفاده کن
            return download_with_ytdlp(link)
        else:
            return download_with_ytdlp(link)
            
    except Exception as e:
        return download_with_ytdlp(link)

# ========== دانلود با yt-dlp ==========
def download_with_ytdlp(link):
    """روش سوم با yt-dlp"""
    try:
        import yt_dlp
        
        if not os.path.exists('downloads'):
            os.makedirs('downloads')
        
        ydl_opts = {
            'outtmpl': 'downloads/instagram_%(id)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'ignoreerrors': True,
            'no_check_certificate': True,
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
            },
            'cookiefile': None,  # بدون کوکی
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=True)
            if info:
                filename = ydl.prepare_filename(info)
                if os.path.exists(filename):
                    return filename, "✅ دانلود انجام شد!"
        
        return None, "❌ دانلود ناموفق! لطفاً لینک رو بررسی کن."
        
    except Exception as e:
        return None, f"❌ خطا: {str(e)[:100]}"

# ========== دانلود استوری ==========
def download_story(link):
    """دانلود استوری (با استفاده از yt-dlp)"""
    try:
        import yt_dlp
        
        if not os.path.exists('downloads'):
            os.makedirs('downloads')
        
        ydl_opts = {
            'outtmpl': 'downloads/story_%(id)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'no_check_certificate': True,
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            },
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=True)
            if info:
                filename = ydl.prepare_filename(info)
                if os.path.exists(filename):
                    return filename, "✅ استوری دانلود شد!"
        
        return None, "❌ دانلود استوری ناموفق!"
        
    except Exception as e:
        return None, f"❌ خطا: {str(e)[:100]}"

# ========== دستور استارت ==========
@bot.message_handler(commands=['start', 'help'])
def start(message):
    user_id = message.from_user.id
    name = message.from_user.first_name
    init_user(user_id, message.from_user.username or "")
    
    if not is_member(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔗 عضویت در کانال", url="https://t.me/hegzo_vpn_channle"))
        markup.add(types.InlineKeyboardButton("✅ تایید عضویت", callback_data="check_membership"))
        bot.reply_to(message, 
            f"🤖 {name} عزیز!\n\nبرای استفاده از ربات دانلودر اینستاگرام، ابتدا در کانال ما عضو شوید، سپس دکمه «تایید عضویت» را بزنید.",
            reply_markup=markup
        )
        return
    
    bot.reply_to(message,
        f"""🤖 **به ربات دانلودر اینستاگرام خوش آمدی {name}!**

📥 لینک پست، ریلز یا استوری اینستاگرام رو برام بفرست تا دانلودش کنم.

🔹 **پشتیبانی:** ریلز، پست، استوری
🔹 **سرعت بالا و رایگان**
🔹 **بدون نیاز به لاگین**

📌 فقط کافیه لینک رو برام بفرستی!
""",
        reply_markup=main_keyboard()
    )

# ========== تایید عضویت ==========
@bot.callback_query_handler(func=lambda call: call.data == "check_membership")
def check_membership(call):
    user_id = call.from_user.id
    if is_member(user_id):
        bot.edit_message_text(
            "✅ عضویت شما تأیید شد! حالا می‌تونی از ربات استفاده کنی.",
            call.message.chat.id,
            call.message.message_id
        )
        bot.send_message(user_id,
            "🤖 **ربات دانلودر اینستاگرام فعال شد!**\n\nلینک مورد نظر رو برام بفرست تا دانلودش کنم.",
            reply_markup=main_keyboard()
        )
    else:
        bot.answer_callback_query(call.id, "❌ شما هنوز در کانال عضو نشده‌اید! لطفاً ابتدا عضو شوید.", show_alert=True)

# ========== دکمه دانلود ==========
@bot.message_handler(func=lambda m: m.text == "📥 دانلود از اینستاگرام")
def download_btn(message):
    bot.reply_to(message,
        "📥 **لینک اینستاگرام رو برام بفرست**\n\nمثال:\n`https://www.instagram.com/p/ABC123/`\n`https://www.instagram.com/reel/XYZ/`\n`https://www.instagram.com/stories/username/`",
        parse_mode='Markdown'
    )

# ========== دکمه راهنما ==========
@bot.message_handler(func=lambda m: m.text == "📜 راهنما")
def help_btn(message):
    bot.reply_to(message,
        """📜 **راهنمای ربات دانلودر اینستاگرام**

1️⃣ لینک پست/ریلز/استوری رو کپی کن
2️⃣ توی ربات برام بفرست
3️⃣ منتظر بمون تا دانلود بشه
4️⃣ فایل برات ارسال میشه

🔹 **پشتیبانی از:**
- پست‌های عادی (عکس/ویدیو)
- ریلز
- استوری

⚠️ **محدودیت‌ها:**
- حجم فایل تا ۵۰ مگابایت (محدودیت تلگرام)
- فقط لینک‌های عمومی

🆔 پشتیبانی: @hegzo_support
"""
    )

# ========== دکمه حساب من ==========
@bot.message_handler(func=lambda m: m.text == "👤 حساب من")
def profile_btn(message):
    user_id = message.from_user.id
    data = users.get(str(user_id), {})
    text = f"""👤 **حساب من**

🆔 شناسه: `{user_id}`
👤 نام: {message.from_user.first_name}
📅 تاریخ عضویت: {data.get('joined_at', 'نامشخص')}

🤖 ربات دانلودر اینستاگرام
"""
    bot.reply_to(message, text, parse_mode='Markdown')

# ========== دکمه پشتیبانی ==========
@bot.message_handler(func=lambda m: m.text == "🆘 پشتیبانی")
def support_btn(message):
    bot.reply_to(message,
        "🆘 **پشتیبانی ربات دانلودر**\n\n@hegzo_support\n\nسوالات و مشکلات خود را به ما بگویید.",
        parse_mode='Markdown'
    )

# ========== دریافت لینک از کاربر ==========
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    user_id = message.from_user.id
    
    if not is_member(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔗 عضویت در کانال", url="https://t.me/hegzo_vpn_channle"))
        markup.add(types.InlineKeyboardButton("✅ تایید عضویت", callback_data="check_membership"))
        bot.reply_to(message,
            "❌ شما هنوز در کانال عضو نشده‌اید!\nلطفاً عضو شوید و تایید کنید.",
            reply_markup=markup
        )
        return
    
    text = message.text
    pattern = r'(https?://(?:www\.)?instagram\.com/[\w\-/]+)'
    match = re.search(pattern, text)
    
    if match:
        link = match.group(1)
        msg = bot.reply_to(message, "⏳ در حال دانلود... لطفاً صبر کن (حداکثر ۳۰ ثانیه)")
        
        # دانلود
        filename, result = download_instagram(link)
        
        if filename and os.path.exists(filename):
            try:
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
                bot.send_message(message.chat.id, "✅ فایل با موفقیت ارسال شد! برای دانلود مجدد، لینک جدید بفرست.")
                
            except Exception as e:
                bot.reply_to(message, f"❌ خطا در ارسال: {str(e)[:100]}")
                if os.path.exists(filename):
                    os.remove(filename)
        else:
            bot.reply_to(message, f"{result}\n\n💡 نکات:\n• مطمئن شو لینک درست کپی شده\n• پست باید عمومی باشه\n• برای استوری، حتماً از لینک استوری استفاده کن")
    else:
        bot.reply_to(message,
            "❌ لطفاً یک لینک معتبر اینستاگرام بفرست.\n\nمثال:\n`https://www.instagram.com/p/ABC123/`\n`https://www.instagram.com/reel/XYZ/`\n`https://www.instagram.com/stories/username/`",
            parse_mode='Markdown'
        )

# ========== اجرا ==========
if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 10000))
    print(f"🤖 ربات دانلودر اینستاگرام روی پورت {PORT} روشن شد!")
    
    # ایجاد پوشه downloads
    if not os.path.exists('downloads'):
        os.makedirs('downloads')
        print("✅ پوشه downloads ساخته شد!")
    
    try:
        bot.delete_webhook()
        print("✅ Webhook پاک شد!")
    except:
        pass
    
    time.sleep(2)
    
    try:
        bot.get_updates(offset=-1, limit=1)
        print("✅ آپدیت‌ها پاک شدند!")
    except:
        pass
    
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)).start()
    
    bot.infinity_polling()
