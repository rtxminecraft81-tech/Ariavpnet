import telebot
from telebot import types
import os
import re
import yt_dlp
import time
from flask import Flask, send_file
import threading
from datetime import datetime, timedelta
import json

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Multi Downloader Bot is running!", 200

@app.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join('downloads', filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return "File not found!", 404

TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    raise ValueError("❌ توکن یافت نشد!")

bot = telebot.TeleBot(TOKEN)

# ========== تنظیمات ==========
ADMIN_ID = int(os.environ.get('ADMIN_ID', '6795169616'))
BASE_URL = os.environ.get('BASE_URL', 'https://ariavpnet.onrender.com')
USER_DB = 'users.json'
DAILY_LIMIT = 5
MAX_FILE_SIZE_MB = 50
PREMIUM_MAX_SIZE_MB = 500

# ========== دیتابیس ساده ==========
def load_users():
    if os.path.exists(USER_DB):
        with open(USER_DB, 'r') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USER_DB, 'w') as f:
        json.dump(users, f, indent=4)

def init_user(user_id, username=""):
    users = load_users()
    if str(user_id) not in users:
        users[str(user_id)] = {
            'username': username,
            'joined_at': str(datetime.now()),
            'is_premium': False,
            'premium_expiry': None,
            'daily_downloads': 0,
            'last_download_date': str(datetime.now().date()),
            'total_downloads': 0
        }
        save_users(users)
    return users

def is_premium(user_id):
    users = load_users()
    user = users.get(str(user_id), {})
    if not user.get('is_premium', False):
        return False
    expiry = user.get('premium_expiry')
    if expiry:
        expiry_date = datetime.fromisoformat(expiry)
        if datetime.now() > expiry_date:
            users[str(user_id)]['is_premium'] = False
            save_users(users)
            return False
    return True

def can_download(user_id):
    users = load_users()
    user = users.get(str(user_id), {})
    if is_premium(user_id):
        return True, "✅ اشتراک ویژه"
    
    today = str(datetime.now().date())
    if user.get('last_download_date') != today:
        users[str(user_id)]['daily_downloads'] = 0
        users[str(user_id)]['last_download_date'] = today
        save_users(users)
    
    if user.get('daily_downloads', 0) >= DAILY_LIMIT:
        return False, f"❌ محدودیت روزانه ({DAILY_LIMIT}) تمام شد!"
    
    return True, f"✅ {DAILY_LIMIT - user.get('daily_downloads', 0)} دانلود مونده"

def increment_download(user_id):
    users = load_users()
    if not is_premium(user_id):
        users[str(user_id)]['daily_downloads'] = users[str(user_id)].get('daily_downloads', 0) + 1
        users[str(user_id)]['total_downloads'] = users[str(user_id)].get('total_downloads', 0) + 1
        save_users(users)

# ========== کیبورد اصلی ==========
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("📥 دانلود", "🎵 دانلود صدا")
    markup.add("👤 حساب من", "⭐ ارتقا به ویژه")
    markup.add("🛒 خرید فیلترشکن پرسرعت", "📜 راهنما")
    return markup

# ========== تابع دانلود ==========
def download_media(link, is_audio=False):
    try:
        if not os.path.exists('downloads'):
            os.makedirs('downloads')
        
        ydl_opts = {
            'outtmpl': 'downloads/%(title)s_%(id)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'no_check_certificate': True,
            'format': 'bestvideo[height<=720]+bestaudio/best[height<=720]' if not is_audio else 'bestaudio/best',
            'merge_output_format': 'mp4',
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }] if not is_audio else [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            },
            'nocheckcertificate': True,
            'geo_bypass': True,
            'cookiefile': None,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=True)
            if info:
                filename = ydl.prepare_filename(info)
                if not os.path.exists(filename):
                    for f in os.listdir('downloads'):
                        if info.get('id') and info['id'] in f:
                            return os.path.join('downloads', f)
                return filename
        
        return None
        
    except Exception as e:
        print(f"Download error: {e}")
        return None

# ========== ارسال فایل ==========
def send_file(message, filename, user_id):
    if not filename or not os.path.exists(filename):
        # ========== پیام خطای دانلود ناموفق ==========
        bot.reply_to(message, 
            "❌ **دانلود ناموفق!**\n\n"
            "📌 برای دانلود از ربات‌های زیر استفاده کنید:\n"
            "🔹 @aria_bot_channle\n\n"
            "🛒 همچنین می‌توانید از بخش «خرید فیلترشکن پرسرعت» استفاده کنید.",
            parse_mode='Markdown'
        )
        return
    
    try:
        file_size = os.path.getsize(filename) / (1024 * 1024)
        max_size = PREMIUM_MAX_SIZE_MB if is_premium(user_id) else MAX_FILE_SIZE_MB
        
        if file_size > max_size:
            bot.reply_to(message, 
                f"⚠️ حجم فایل {file_size:.1f}MB از حد مجاز ({max_size}MB) بیشتره!\n\n"
                f"📌 برای دانلود فایل‌های بزرگتر از ربات‌های زیر استفاده کنید:\n"
                f"🔹 @aria_bot_channle\n\n"
                f"🛒 یا از بخش «خرید فیلترشکن پرسرعت» استفاده کنید."
            )
            if os.path.exists(filename):
                os.remove(filename)
            return
        
        if file_size > 20:
            file_name = os.path.basename(filename)
            download_link = f"{BASE_URL}/download/{file_name}"
            bot.reply_to(message, 
                f"📥 **فایل آماده دانلود است!**\n\n"
                f"📁 حجم: {file_size:.1f} MB\n"
                f"🔗 [لینک دانلود]({download_link})",
                parse_mode='Markdown'
            )
            threading.Thread(target=lambda: (time.sleep(3600), os.remove(filename) if os.path.exists(filename) else None)).start()
        else:
            with open(filename, 'rb') as f:
                if filename.endswith('.mp4'):
                    bot.send_video(message.chat.id, f, caption="✅ دانلود شد!", supports_streaming=True)
                elif filename.endswith('.mp3'):
                    bot.send_audio(message.chat.id, f, caption="✅ دانلود شد!")
                else:
                    bot.send_document(message.chat.id, f, caption="✅ دانلود شد!")
            os.remove(filename)
        
        increment_download(user_id)
        
    except Exception as e:
        bot.reply_to(message, 
            f"❌ **خطا در ارسال!**\n\n"
            f"📌 برای دانلود از ربات‌های زیر استفاده کنید:\n"
            f"🔹 @aria_bot_channle\n\n"
            f"🛒 یا از بخش «خرید فیلترشکن پرسرعت» استفاده کنید."
        )
        if os.path.exists(filename):
            os.remove(filename)

# ========== دستورات ==========
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    init_user(user_id, message.from_user.username or "")
    
    bot.reply_to(message, 
        f"🎬 **به ربات دانلودر خوش آمدی!**\n\n"
        f"📥 لینک یوتیوب، اینستاگرام یا تیک‌تاک رو بفرست.\n"
        f"⭐ وضعیت: {'✅ ویژه' if is_premium(user_id) else '❌ رایگان'}\n\n"
        f"🛒 برای خرید فیلترشکن پرسرعت از دکمه زیر استفاده کن.\n"
        f"📞 پشتیبانی: @hegzosupport",
        reply_markup=main_keyboard()
    )

@bot.message_handler(func=lambda m: m.text == "📥 دانلود")
def video_cmd(message):
    bot.reply_to(message, "📹 **لینک رو بفرست.**")
    bot.register_next_step_handler(message, lambda m: process_link(m, False))

@bot.message_handler(func=lambda m: m.text == "🎵 دانلود صدا")
def audio_cmd(message):
    bot.reply_to(message, "🎵 **لینک یوتیوب رو بفرست.**")
    bot.register_next_step_handler(message, lambda m: process_link(m, True))

@bot.message_handler(func=lambda m: m.text == "👤 حساب من")
def profile(message):
    user_id = message.from_user.id
    users = load_users()
    user = users.get(str(user_id), {})
    
    text = f"""👤 **حساب من**

🆔 ID: `{user_id}`
⭐ وضعیت: {'✅ ویژه' if is_premium(user_id) else '❌ رایگان'}
📊 دانلود امروز: {user.get('daily_downloads', 0)}/{DAILY_LIMIT}
📈 مجموع: {user.get('total_downloads', 0)}
"""
    bot.reply_to(message, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "⭐ ارتقا به ویژه")
def upgrade(message):
    user_id = message.from_user.id
    if is_premium(user_id):
        bot.reply_to(message, "✅ شما هم‌اکنون ویژه هستید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📅 ۱ ماهه - ۱۵۰,۰۰۰ تومان", callback_data="buy_1month"),
        types.InlineKeyboardButton("📅 ۳ ماهه - ۳۵۰,۰۰۰ تومان", callback_data="buy_3month"),
        types.InlineKeyboardButton("📅 ۶ ماهه - ۶۰۰,۰۰۰ تومان", callback_data="buy_6month")
    )
    bot.reply_to(message, 
        "⭐ **خرید اشتراک ویژه**\n\n"
        "مزایا:\n"
        "✅ دانلود نامحدود\n"
        "✅ فایل تا ۵۰۰MB\n"
        "✅ اولویت پشتیبانی",
        reply_markup=markup
    )

# ========== دکمه خرید فیلترشکن پرسرعت ==========
@bot.message_handler(func=lambda m: m.text == "🛒 خرید فیلترشکن پرسرعت")
def buy_vpn(message):
    bot.reply_to(message,
        "🔹 **برای خرید فیلترشکن پرسرعت از ربات زیر استفاده کنید:**\n\n"
        "🤖 @hegzo_vpn_bot\n\n"
        "📌 این ربات بهترین سرویس‌های VPN رو با کیفیت بالا ارائه میده.\n"
        "💳 پرداخت آسان و پشتیبانی ۲۴ ساعته.\n\n"
        "📞 پشتیبانی: @hegzosupport"
    )

@bot.message_handler(func=lambda m: m.text == "📜 راهنما")
def help_cmd(message):
    bot.reply_to(message,
        "📜 **راهنما**\n\n"
        "🔹 لینک یوتیوب/اینستاگرام/تیک‌تاک رو بفرست.\n"
        "🔹 دانلود خودکار انجام میشه.\n\n"
        "📌 برای دانلود بیشتر از ربات‌های زیر استفاده کنید:\n"
        "🔹 @aria_bot_channle\n\n"
        "🛒 خرید فیلترشکن پرسرعت: @hegzo_vpn_bot\n"
        "📞 پشتیبانی: @hegzosupport"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def buy_callback(call):
    bot.answer_callback_query(call.id, 
        "💰 لطفاً مبلغ رو به کارت زیر واریز کن:\n\n"
        "5022291525516892\n"
        "احمد خزایی\n\n"
        "و رسید رو بفرست.",
        show_alert=True
    )

# ========== پردازش لینک ==========
def process_link(message, is_audio):
    user_id = message.from_user.id
    text = message.text
    
    can, msg = can_download(user_id)
    if not can:
        bot.reply_to(message, 
            f"{msg}\n\n"
            f"📌 برای دانلود بیشتر از ربات‌های زیر استفاده کنید:\n"
            f"🔹 @aria_bot_channle\n\n"
            f"🛒 یا از بخش «خرید فیلترشکن پرسرعت» استفاده کنید."
        )
        return
    
    pattern = r'(https?://(?:www\.)?(?:youtube\.com|youtu\.be|instagram\.com|tiktok\.com)/[\w\-/?=&]+)'
    match = re.search(pattern, text)
    
    if not match:
        bot.reply_to(message, 
            "❌ **لینک معتبر نیست!**\n\n"
            "📌 لینک یوتیوب، اینستاگرام یا تیک‌تاک بفرست.\n\n"
            f"📌 برای دانلود بیشتر از ربات‌های زیر استفاده کنید:\n"
            f"🔹 @aria_bot_channle"
        )
        return
    
    link = match.group(1)
    bot.reply_to(message, "⏳ در حال دانلود...")
    
    filename = download_media(link, is_audio)
    send_file(message, filename, user_id)

# ========== پیام‌های عادی ==========
@bot.message_handler(func=lambda m: True)
def handle_all(message):
    text = message.text
    pattern = r'(https?://(?:www\.)?(?:youtube\.com|youtu\.be|instagram\.com|tiktok\.com)/[\w\-/?=&]+)'
    if re.search(pattern, text):
        process_link(message, False)
    else:
        bot.reply_to(message, 
            "❌ **لینک معتبر نیست!**\n\n"
            "📌 لینک یوتیوب، اینستاگرام یا تیک‌تاک بفرست.\n\n"
            "📌 برای دانلود بیشتر از ربات‌های زیر استفاده کنید:\n"
            "🔹 @aria_bot_channle\n\n"
            "🛒 خرید فیلترشکن پرسرعت: @hegzo_vpn_bot",
            reply_markup=main_keyboard()
        )

# ========== اجرا ==========
if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 10000))
    
    if not os.path.exists('downloads'):
        os.makedirs('downloads')
    
    print("🤖 ربات چندمنظوره روشن شد!")
    
    try:
        bot.remove_webhook()
    except:
        pass
    
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)).start()
    
    bot.infinity_polling()
