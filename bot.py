import telebot
from telebot import types
import json
import os
import time
from datetime import datetime
from flask import Flask
import threading
import re
from instagrapi import Client

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Instagram Downloader Bot is running!", 200

TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    raise ValueError("❌ توکن یافت نشد! لطفاً BOT_TOKEN را در Render تنظیم کنید.")

ADMIN_ID = '6795169616'
CHANNEL_USERNAME = '@hegzo_vpn_channle'

# ========== اطلاعات اکانت اینستاگرام ==========
INSTA_USERNAME = os.environ.get('INSTA_USERNAME')
INSTA_PASSWORD = os.environ.get('INSTA_PASSWORD')

bot = telebot.TeleBot(TOKEN)
USER_DB = 'users.json'

# ========== راه‌اندازی کلاینت اینستاگرام ==========
def get_instagram_client():
    if not INSTA_USERNAME or not INSTA_PASSWORD:
        print("❌ اطلاعات اکانت اینستاگرام موجود نیست!")
        return None
    cl = Client()
    cl.set_user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    try:
        cl.login(INSTA_USERNAME, INSTA_PASSWORD)
        print(f"✅ لاگین به اینستاگرام موفق! (کاربر: {INSTA_USERNAME})")
        return cl
    except Exception as e:
        print(f"❌ خطا در لاگین: {e}")
        return None

instagram_client = get_instagram_client()

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

# ========== تابع دانلود ==========
def download_instagram(link):
    global instagram_client
    
    try:
        if instagram_client is None:
            instagram_client = get_instagram_client()
            if instagram_client is None:
                return None, "❌ مشکل در اتصال به اینستاگرام!"
        
        shortcode = None
        if '/p/' in link:
            shortcode = link.split('/p/')[1].split('/')[0]
        elif '/reel/' in link:
            shortcode = link.split('/reel/')[1].split('/')[0]
        elif '/stories/' in link:
            return download_story(link)
        else:
            return None, "❌ لینک معتبر نیست!"
        
        if not shortcode:
            return None, "❌ لینک معتبر نیست!"
        
        media_id = instagram_client.media_id(shortcode)
        info = instagram_client.media_info(media_id)
        
        if not os.path.exists('downloads'):
            os.makedirs('downloads')
        
        if info.media_type == 1:
            filename = f"downloads/instagram_{shortcode}.jpg"
            instagram_client.photo_download(media_id, filename)
            return filename, "✅ عکس دانلود شد!"
        elif info.media_type == 2:
            filename = f"downloads/instagram_{shortcode}.mp4"
            instagram_client.video_download(media_id, filename)
            return filename, "✅ ویدیو دانلود شد!"
        elif info.media_type == 8:
            filename = f"downloads/instagram_{shortcode}_1.jpg"
            instagram_client.photo_download(media_id, filename)
            return filename, "✅ عکس دانلود شد!"
        else:
            return None, "❌ نوع محتوا پشتیبانی نمی‌شود!"
            
    except Exception as e:
        return None, f"❌ خطا: {str(e)[:100]}"

def download_story(link):
    global instagram_client
    
    try:
        if instagram_client is None:
            instagram_client = get_instagram_client()
            if instagram_client is None:
                return None, "❌ مشکل در اتصال به اینستاگرام!"
        
        username = link.split('/stories/')[1].split('/')[0]
        user_id = instagram_client.user_id_from_username(username)
        stories = instagram_client.user_stories(user_id)
        
        if not stories:
            return None, "❌ استوری پیدا نشد!"
        
        for story in stories:
            if not os.path.exists('downloads'):
                os.makedirs('downloads')
            
            if story.media_type == 1:
                filename = f"downloads/story_{username}_{story.id}.jpg"
                instagram_client.story_download(story.id, filename)
                return filename, "✅ استوری دانلود شد!"
            elif story.media_type == 2:
                filename = f"downloads/story_{username}_{story.id}.mp4"
                instagram_client.story_download(story.id, filename)
                return filename, "✅ استوری دانلود شد!"
        
        return None, "❌ استوری پیدا نشد!"
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
    bot.reply_to(m, "🆘 **پشتیبانی**\n\n@hegzo_support")

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
        bot.reply_to(m, "⏳ در حال دانلود...")
        
        filename, result = download_instagram(link)
        
        if filename and os.path.exists(filename):
            try:
                with open(filename, 'rb') as f:
                    if filename.endswith('.mp4'):
                        bot.send_video(m.chat.id, f, caption=result)
                    else:
                        bot.send_photo(m.chat.id, f, caption=result)
                os.remove(filename)
            except Exception as e:
                bot.reply_to(m, f"❌ خطا: {str(e)[:100]}")
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
        bot.delete_webhook()
    except:
        pass
    
    time.sleep(2)
    
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)).start()
    
    bot.infinity_polling()
