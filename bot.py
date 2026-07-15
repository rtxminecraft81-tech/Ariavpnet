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
    raise ValueError("❌ توکن یافت نشد!")

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
banned_users = set()

def load_banned_users():
    global banned_users
    if os.path.exists('banned_users.json'):
        with open('banned_users.json', 'r') as f:
            banned_users = set(json.load(f))

def save_banned_users():
    with open('banned_users.json', 'w') as f:
        json.dump(list(banned_users), f)

def is_banned(user_id):
    return str(user_id) in banned_users

load_banned_users()

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
    markup.add("📜 کانفیگ‌های من", "👤 حساب من")
    markup.add("🤝 دعوت سلطنتی", "🆘 پشتیبانی")
    markup.add("🏠 صفحه اصلی")
    return markup

# ========== تابع دانلود با API ==========
def download_instagram(link):
    """دانلود با استفاده از API رایگان (نیاز به کوکی نداره)"""
    try:
        # استخراج shortcode از لینک
        shortcode = None
        if '/p/' in link:
            shortcode = link.split('/p/')[1].split('/')[0]
        elif '/reel/' in link:
            shortcode = link.split('/reel/')[1].split('/')[0]
        elif '/tv/' in link:
            shortcode = link.split('/tv/')[1].split('/')[0]
        else:
            return None, "❌ لینک معتبر نیست!"
        
        if not shortcode:
            return None, "❌ لینک معتبر نیست!"
        
        # استفاده از API اینستاگرام (بدون لاگین)
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
                
                if not os.path.exists('downloads'):
                    os.makedirs('downloads')
                
                # دانلود ویدیو
                if media.get('is_video', False):
                    video_url = media.get('video_url')
                    if video_url:
                        video_response = requests.get(video_url, stream=True, timeout=30)
                        if video_response.status_code == 200:
                            filename = f"downloads/instagram_{shortcode}.mp4"
                            with open(filename, 'wb') as f:
                                for chunk in video_response.iter_content(chunk_size=8192):
                                    if chunk:
                                        f.write(chunk)
                            return filename, "✅ ویدیو دانلود شد!"
                else:
                    # دانلود عکس
                    image_url = media.get('display_url')
                    if image_url:
                        image_response = requests.get(image_url, timeout=30)
                        if image_response.status_code == 200:
                            filename = f"downloads/instagram_{shortcode}.jpg"
                            with open(filename, 'wb') as f:
                                f.write(image_response.content)
                            return filename, "✅ عکس دانلود شد!"
        
        # اگه روش بالا جواب نداد، از yt-dlp استفاده کن
        return download_with_ytdlp(link)
        
    except Exception as e:
        return None, f"❌ خطا: {str(e)[:100]}"

# ========== روش جایگزین با yt-dlp ==========
def download_with_ytdlp(link):
    """روش دوم با yt-dlp"""
    try:
        import yt_dlp
        
        if not os.path.exists('downloads'):
            os.makedirs('downloads')
        
        ydl_opts = {
            'outtmpl': 'downloads/instagram_%(id)s.%(ext)s',
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
                    return filename, "✅ دانلود انجام شد!"
        
        return None, "❌ دانلود ناموفق! لطفاً لینک رو بررسی کن."
        
    except Exception as e:
        return None, f"❌ خطا: {str(e)[:100]}"

# ========== دستورات ربات ==========
@bot.message_handler(commands=['start', 'help'])
def start(message):
    user_id = message.from_user.id
    if is_banned(user_id):
        bot.reply_to(message, "⛔ شما توسط ادمین مسدود شده اید!")
        return
    name = message.from_user.first_name
    init_user(user_id, message.from_user.username or "")
    
    if not is_member(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔗 عضویت در کانال", url="https://t.me/hegzo_vpn_channle"))
        markup.add(types.InlineKeyboardButton("✅ تایید عضویت", callback_data="check_membership"))
        bot.reply_to(message, f"🤖 {name} عزیز!\n\nبرای استفاده از ربات، ابتدا در کانال عضو شوید.", reply_markup=markup)
        return
    
    bot.reply_to(message, f"""🤖 **به ربات دانلودر اینستاگرام خوش آمدی {name}!**

📥 لینک پست، ریلز یا استوری اینستاگرام رو برام بفرست تا دانلودش کنم.
""", reply_markup=main_keyboard())

@bot.callback_query_handler(func=lambda call: call.data == "check_membership")
def check_membership(call):
    user_id = call.from_user.id
    if is_member(user_id):
        bot.edit_message_text("✅ عضویت تأیید شد!", call.message.chat.id, call.message.message_id)
        bot.send_message(user_id, "🤖 ربات فعال شد!", reply_markup=main_keyboard())
    else:
        bot.answer_callback_query(call.id, "❌ عضو نشده‌اید!", show_alert=True)

@bot.message_handler(func=lambda m: m.text == "🏠 صفحه اصلی")
def back_home(m):
    bot.reply_to(m, "🏠 صفحه اصلی", reply_markup=main_keyboard())

@bot.message_handler(func=lambda m: m.text == "📥 دانلود از اینستاگرام")
def download_btn(m):
    bot.reply_to(m, "📥 **لینک اینستاگرام رو بفرست**")

@bot.message_handler(func=lambda m: m.text == "📜 کانفیگ‌های من")
def my_configs(m):
    bot.reply_to(m, "📜 **کانفیگ‌های فعال شما:**\n\n(این بخش برای ربات دانلودر غیرفعال است)")

@bot.message_handler(func=lambda m: m.text == "👤 حساب من")
def profile(m):
    user_id = m.from_user.id
    data = users.get(str(user_id), {})
    text = f"""👤 **حساب من**

🆔 شناسه: `{user_id}`
👤 نام: {m.from_user.first_name}
📅 تاریخ عضویت: {data.get('joined_at', 'نامشخص')}
"""
    bot.reply_to(m, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "🤝 دعوت سلطنتی")
def invite(m):
    link = f"https://t.me/{bot.get_me().username}?start={m.from_user.id}"
    bot.reply_to(m, f"👑 **لینک دعوت شما**\n\n`{link}`")

@bot.message_handler(func=lambda m: m.text == "🆘 پشتیبانی")
def support(m):
    bot.reply_to(m, "🆘 **پشتیبانی**\n\n@hegzosupport")

@bot.message_handler(func=lambda m: True)
def handle_message(m):
    user_id = m.from_user.id
    
    if is_banned(user_id):
        bot.reply_to(m, "⛔ شما مسدود شده اید!")
        return
    
    if not is_member(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔗 عضویت در کانال", url="https://t.me/hegzo_vpn_channle"))
        markup.add(types.InlineKeyboardButton("✅ تایید عضویت", callback_data="check_membership"))
        bot.reply_to(m, "❌ ابتدا در کانال عضو شوید!", reply_markup=markup)
        return
    
    text = m.text
    pattern = r'(https?://(?:www\.)?instagram\.com/[\w\-/]+)'
    match = re.search(pattern, text)
    
    if match:
        link = match.group(1)
        bot.reply_to(m, "⏳ در حال دانلود... لطفاً صبر کن")
        
        filename, result = download_instagram(link)
        
        if filename and os.path.exists(filename):
            try:
                file_size = os.path.getsize(filename) / (1024 * 1024)
                if file_size > 50:
                    bot.reply_to(m, f"⚠️ حجم فایل {file_size:.1f} مگابایت هست که از محدودیت ۵۰ مگابایت تلگرام بیشتره!")
                    os.remove(filename)
                    return
                
                with open(filename, 'rb') as f:
                    if filename.endswith('.mp4'):
                        bot.send_video(m.chat.id, f, caption=result, supports_streaming=True)
                    elif filename.endswith('.jpg') or filename.endswith('.jpeg') or filename.endswith('.png'):
                        bot.send_photo(m.chat.id, f, caption=result)
                    else:
                        bot.send_document(m.chat.id, f, caption=result)
                
                os.remove(filename)
                bot.send_message(m.chat.id, "✅ فایل با موفقیت ارسال شد!")
                
            except Exception as e:
                bot.reply_to(m, f"❌ خطا در ارسال: {str(e)[:100]}")
                if os.path.exists(filename):
                    os.remove(filename)
        else:
            bot.reply_to(m, result)
    else:
        bot.reply_to(m, "❌ لینک معتبر اینستاگرام بفرست")

# ========== اجرا ==========
if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 10000))
    
    if not os.path.exists('downloads'):
        os.makedirs('downloads')
    
    try:
        bot.remove_webhook()
        print("✅ Webhook پاک شد!")
    except:
        pass
    
    time.sleep(2)
    
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)).start()
    
    bot.infinity_polling()
