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

# ========== تابع دانلود با API خارجی ==========
def download_instagram(link):
    """دانلود با استفاده از API ساده (بدون لاگین)"""
    try:
        # استفاده از API رایگان
        api_url = f"https://api.instagram.com/oembed?url={link}"
        
        # روش جایگزین: استفاده از سایت third-party
        # این API رو تست کن - کار می‌کنه
        response = requests.get(
            f"https://www.instagram.com/p/{link.split('/p/')[1].split('/')[0]}/?__a=1",
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            # استخراج لینک ویدیو یا عکس
            if 'graphql' in data:
                media = data['graphql']['shortcode_media']
                if media['is_video']:
                    video_url = media['video_url']
                    # دانلود ویدیو
                    video_response = requests.get(video_url, stream=True)
                    if video_response.status_code == 200:
                        filename = f"instagram_{media['id']}.mp4"
                        with open(filename, 'wb') as f:
                            for chunk in video_response.iter_content(chunk_size=8192):
                                f.write(chunk)
                        return filename, "✅ ویدیو دانلود شد!"
                else:
                    # عکس
                    image_url = media['display_url']
                    image_response = requests.get(image_url)
                    if image_response.status_code == 200:
                        filename = f"instagram_{media['id']}.jpg"
                        with open(filename, 'wb') as f:
                            f.write(image_response.content)
                        return filename, "✅ عکس دانلود شد!"
        
        # اگر روش اول جواب نداد، از روش دوم استفاده کن
        return download_with_alternative(link)
        
    except Exception as e:
        return None, f"❌ خطا: {str(e)[:100]}"

# ========== روش جایگزین برای دانلود ==========
def download_with_alternative(link):
    """روش دوم دانلود با استفاده از کتابخانه مختلف"""
    try:
        # استفاده از yt-dlp با تنظیمات خاص
        import yt_dlp
        
        ydl_opts = {
            'outtmpl': 'downloads/instagram_%(id)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'ignoreerrors': True,
            'no_check_certificate': True,
            'cookiefile': None,
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Sec-Fetch-Mode': 'navigate',
            }
        }
        
        if not os.path.exists('downloads'):
            os.makedirs('downloads')
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=True)
            filename = ydl.prepare_filename(info)
            if os.path.exists(filename):
                return filename, "✅ دانلود انجام شد!"
        
        return None, "❌ دانلود ناموفق! لطفاً لینک رو بررسی کن."
        
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
        "📥 **لینک اینستاگرام رو برام بفرست**\n\nمثال:\n`https://www.instagram.com/p/ABC123/`\n`https://www.instagram.com/reel/XYZ/`",
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

⚠️ **محدودیت‌ها:**
- حجم فایل تا ۵۰ مگابایت
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

# ========== دکمه صفحه اصلی ==========
@bot.message_handler(func=lambda m: m.text == "🏠 صفحه اصلی")
def back_home(message):
    bot.reply_to(message, "🏠 **صفحه اصلی**", reply_markup=main_keyboard())

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
        bot.reply_to(message, "⏳ در حال دانلود... لطفاً صبر کن")
        
        filename, msg = download_instagram(link)
        
        if filename and os.path.exists(filename):
            try:
                file_size = os.path.getsize(filename) / (1024 * 1024)
                if file_size > 50:
                    bot.reply_to(message, f"⚠️ حجم فایل {file_size:.1f} مگابایت هست که از محدودیت ۵۰ مگابایت تلگرام بیشتره!")
                    os.remove(filename)
                    return
                
                with open(filename, 'rb') as f:
                    if filename.endswith('.mp4'):
                        bot.send_video(message.chat.id, f, caption=msg, supports_streaming=True)
                    elif filename.endswith('.jpg') or filename.endswith('.jpeg'):
                        bot.send_photo(message.chat.id, f, caption=msg)
                    else:
                        bot.send_document(message.chat.id, f, caption=msg)
                
                os.remove(filename)
                bot.reply_to(message, "✅ فایل با موفقیت ارسال شد!")
                
            except Exception as e:
                bot.reply_to(message, f"❌ خطا در ارسال: {str(e)[:100]}")
                if os.path.exists(filename):
                    os.remove(filename)
        else:
            bot.reply_to(message, msg)
    else:
        bot.reply_to(message,
            "❌ لطفاً یک لینک معتبر اینستاگرام بفرست.\n\nمثال:\n`https://www.instagram.com/p/ABC123/`",
            parse_mode='Markdown'
        )

# ========== اجرا ==========
if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 10000))
    print(f"🤖 ربات دانلودر اینستاگرام روی پورت {PORT} روشن شد!")
    
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
