import telebot
from telebot import types
import json
import os
import time
from datetime import datetime
from flask import Flask
import threading
import instaloader
import re
import requests

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Instagram Downloader Bot is running!", 200

TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    raise ValueError("❌ توکن یافت نشد! لطفاً BOT_TOKEN را در Render تنظیم کنید.")

ADMIN_ID = '6795169616'  # آیدی ادمین رو همینجا بذار
CHANNEL_USERNAME = '@hegzo_vpn_channle'  # کانال جدید

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

# ========== دستور استارت ==========
@bot.message_handler(commands=['start', 'help'])
def start(message):
    user_id = message.from_user.id
    name = message.from_user.first_name
    init_user(user_id, message.from_user.username or "")
    
    # بررسی عضویت
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

🔹 **پشتیبانی:** ریلز، پست، استوری هایلایت
🔹 **سرعت بالا و رایگان**
🔹 **بدون محدودیت حجم**

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

🔹 **پشتیبانی از:**
- پست‌های عادی (عکس/ویدیو)
- ریلز
- استوری هایلایت

⚠️ **محدودیت‌ها:**
- حجم فایل تا ۵۰ مگابایت (محدودیت تلگرام)
- لینک باید عمومی باشه

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

# ========== تابع دانلود از اینستاگرام ==========
def download_instagram(link):
    """دانلود محتوای اینستاگرام با instaloader"""
    try:
        loader = instaloader.Instaloader()
        
        # تشخیص نوع لینک
        if '/p/' in link:
            shortcode = link.split('/p/')[1].split('/')[0]
            post = instaloader.Post.from_shortcode(loader.context, shortcode)
            return download_post(post)
        elif '/reel/' in link:
            shortcode = link.split('/reel/')[1].split('/')[0]
            post = instaloader.Post.from_shortcode(loader.context, shortcode)
            return download_post(post)
        elif '/stories/' in link:
            # استوری
            username = link.split('/stories/')[1].split('/')[0]
            profile = instaloader.Profile.from_username(loader.context, username)
            return download_story(loader, profile)
        else:
            return None, "❌ لینک معتبر نیست!"
            
    except Exception as e:
        return None, f"❌ خطا در دانلود: {str(e)}"

def download_post(post):
    """دانلود پست یا ریلز"""
    try:
        if post.is_video:
            # دانلود ویدیو
            video_url = post.video_url
            response = requests.get(video_url)
            if response.status_code == 200:
                filename = f"instagram_{post.shortcode}.mp4"
                with open(filename, 'wb') as f:
                    f.write(response.content)
                return filename, "✅ ویدیو دانلود شد!"
        else:
            # دانلود عکس
            image_url = post.url
            response = requests.get(image_url)
            if response.status_code == 200:
                filename = f"instagram_{post.shortcode}.jpg"
                with open(filename, 'wb') as f:
                    f.write(response.content)
                return filename, "✅ عکس دانلود شد!"
        return None, "❌ دانلود ناموفق!"
    except Exception as e:
        return None, f"❌ خطا: {str(e)}"

def download_story(loader, profile):
    """دانلود استوری"""
    try:
        stories = loader.get_stories([profile.userid])
        for story in stories:
            for item in story.get_items():
                if item.is_video:
                    filename = f"story_{profile.username}_{item.mediaid}.mp4"
                    loader.download_storyitem(item, target=filename)
                    return filename, "✅ استوری دانلود شد!"
                else:
                    filename = f"story_{profile.username}_{item.mediaid}.jpg"
                    loader.download_storyitem(item, target=filename)
                    return filename, "✅ استوری دانلود شد!"
        return None, "❌ استوری پیدا نشد!"
    except Exception as e:
        return None, f"❌ خطا: {str(e)}"

# ========== دریافت لینک از کاربر ==========
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    user_id = message.from_user.id
    
    # بررسی عضویت
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
    
    # تشخیص لینک اینستاگرام
    pattern = r'(https?://(?:www\.)?instagram\.com/[\w\-/]+)'
    match = re.search(pattern, text)
    
    if match:
        link = match.group(1)
        bot.reply_to(message, "⏳ در حال دانلود... لطفاً صبر کن")
        
        # دانلود
        filename, msg = download_instagram(link)
        
        if filename and os.path.exists(filename):
            # ارسال فایل
            try:
                with open(filename, 'rb') as f:
                    if filename.endswith('.mp4'):
                        bot.send_video(message.chat.id, f, caption=msg)
                    else:
                        bot.send_photo(message.chat.id, f, caption=msg)
                os.remove(filename)  # پاک کردن فایل بعد از ارسال
            except Exception as e:
                bot.reply_to(message, f"❌ خطا در ارسال: {str(e)}")
        else:
            bot.reply_to(message, msg)
    else:
        # اگر لینک نبود
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
