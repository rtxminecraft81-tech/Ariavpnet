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
# یه اکانت فیک بساز و اینجا بذار
INSTA_USERNAME = "hegzo_vpn"  # <-- عوض کن
INSTA_PASSWORD = "Erfankhazaee1387138798"  # <-- عوض کن

bot = telebot.TeleBot(TOKEN)
USER_DB = 'users.json'

# ========== راه‌اندازی کلاینت اینستاگرام ==========
def get_instagram_client():
    """ساخت کلاینت اینستاگرام با لاگین"""
    cl = Client()
    try:
        cl.login(INSTA_USERNAME, INSTA_PASSWORD)
        print("✅ لاگین به اینستاگرام موفقیت‌آمیز بود!")
        return cl
    except Exception as e:
        print(f"❌ خطا در لاگین: {e}")
        return None

# لاگین اولیه
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

# ========== تابع دانلود با instagrapi ==========
def download_instagram(link):
    """دانلود با استفاده از instagrapi (مثل اپ موبایل)"""
    global instagram_client
    
    try:
        # اگر کلاینت مشکل داشت، دوباره لاگین کن
        if instagram_client is None:
            instagram_client = get_instagram_client()
            if instagram_client is None:
                return None, "❌ مشکل در اتصال به اینستاگرام! لطفاً دوباره تلاش کن."
        
        # استخراج shortcode از لینک
        shortcode = None
        media_type = "post"
        
        if '/p/' in link:
            shortcode = link.split('/p/')[1].split('/')[0]
        elif '/reel/' in link:
            shortcode = link.split('/reel/')[1].split('/')[0]
            media_type = "reel"
        elif '/tv/' in link:
            shortcode = link.split('/tv/')[1].split('/')[0]
        elif '/stories/' in link:
            return download_story(link)
        else:
            return None, "❌ لینک معتبر نیست!"
        
        if not shortcode:
            return None, "❌ لینک معتبر نیست!"
        
        # دریافت اطلاعات پست
        try:
            media_id = instagram_client.media_id(shortcode)
            info = instagram_client.media_info(media_id)
            
            if not os.path.exists('downloads'):
                os.makedirs('downloads')
            
            # دانلود فایل
            if info.media_type == 1:  # عکس
                filename = f"downloads/instagram_{shortcode}.jpg"
                instagram_client.photo_download(media_id, filename)
                return filename, "✅ عکس دانلود شد!"
                
            elif info.media_type == 2:  # ویدیو / ریلز
                filename = f"downloads/instagram_{shortcode}.mp4"
                instagram_client.video_download(media_id, filename)
                return filename, "✅ ویدیو دانلود شد!"
                
            elif info.media_type == 8:  # چند عکس (Carousel)
                # دانلود اولین عکس
                filename = f"downloads/instagram_{shortcode}_1.jpg"
                instagram_client.photo_download(media_id, filename)
                return filename, "✅ عکس دانلود شد!"
                
            else:
                return None, "❌ نوع محتوا پشتیبانی نمی‌شود!"
                
        except Exception as e:
            error_msg = str(e)
            if "login" in error_msg.lower() or "not found" in error_msg.lower():
                # دوباره لاگین کن
                instagram_client = get_instagram_client()
                if instagram_client:
                    # یکبار دیگه تلاش کن
                    return download_instagram(link)
            return None, f"❌ خطا: {error_msg[:100]}"
            
    except Exception as e:
        return None, f"❌ خطا: {str(e)[:100]}"

# ========== دانلود استوری ==========
def download_story(link):
    """دانلود استوری با instagrapi"""
    global instagram_client
    
    try:
        if instagram_client is None:
            instagram_client = get_instagram_client()
            if instagram_client is None:
                return None, "❌ مشکل در اتصال به اینستاگرام!"
        
        # استخراج یوزرنیم از لینک استوری
        username = link.split('/stories/')[1].split('/')[0]
        
        if not username:
            return None, "❌ لینک استوری معتبر نیست!"
        
        # دریافت user_id
        user_id = instagram_client.user_id_from_username(username)
        
        # دریافت استوری‌ها
        stories = instagram_client.user_stories(user_id)
        
        if not stories:
            return None, "❌ استوری برای این کاربر پیدا نشد!"
        
        # دانلود اولین استوری
        for story in stories:
            if not os.path.exists('downloads'):
                os.makedirs('downloads')
            
            if story.media_type == 1:  # عکس
                filename = f"downloads/story_{username}_{story.id}.jpg"
                instagram_client.story_download(story.id, filename)
                return filename, "✅ استوری دانلود شد!"
            elif story.media_type == 2:  # ویدیو
                filename = f"downloads/story_{username}_{story.id}.mp4"
                instagram_client.story_download(story.id, filename)
                return filename, "✅ استوری دانلود شد!"
        
        return None, "❌ استوری پیدا نشد!"
        
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
🔹 **بدون محدودیت**

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
        bot.reply_to(message, "⏳ در حال دانلود... لطفاً صبر کن")
        
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
                
            except Exception as e:
                bot.reply_to(message, f"❌ خطا در ارسال: {str(e)[:100]}")
                if os.path.exists(filename):
                    os.remove(filename)
        else:
            bot.reply_to(message, result)
    else:
        bot.reply_to(message,
            "❌ لطفاً یک لینک معتبر اینستاگرام بفرست.\n\nمثال:\n`https://www.instagram.com/p/ABC123/`\n`https://www.instagram.com/reel/XYZ/`",
            parse_mode='Markdown'
        )

# ========== اجرا ==========
if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 10000))
    print(f"🤖 ربات دانلودر اینستاگرام روی پورت {PORT} روشن شد!")
    
    if not os.path.exists('downloads'):
        os.makedirs('downloads')
    
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
