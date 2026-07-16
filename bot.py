import telebot
from telebot import types
import os
import re
import yt_dlp
import requests
import json
import time
from datetime import datetime, timedelta
from flask import Flask, send_file
import threading

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Mega Downloader Bot is running!", 200

@app.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join('downloads', filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return "فایل پیدا نشد!", 404

TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    raise ValueError("❌ توکن یافت نشد!")

bot = telebot.TeleBot(TOKEN)

# ========== تنظیمات ==========
ADMIN_ID = '6795169616'
CARD_NUMBER = '5022291525516892'
CARD_NAME = 'احمد خزایی'
BASE_URL = 'https://ariavpnet.onrender.com'

PRICES = {
    '1month': 150000,
    '3month': 350000,
    '6month': 600000,
    '1year': 1000000
}

PLANS = {
    '1month': '📅 ۱ ماهه',
    '3month': '📅 ۳ ماهه',
    '6month': '📅 ۶ ماهه',
    '1year': '📅 ۱ ساله'
}

USER_DB = 'users.json'
DAILY_LIMIT = 5
MAX_FILE_SIZE_MB = 50
PREMIUM_MAX_SIZE_MB = 500

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
            'joined_at': str(datetime.now()),
            'is_premium': False,
            'premium_expiry': None,
            'daily_downloads': 0,
            'last_download_date': str(datetime.now().date()),
            'pending_payment': None,
            'total_downloads': 0
        }
        save_users(users)

def is_premium(user_id):
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
    user = users.get(str(user_id), {})
    if is_premium(user_id):
        return True, "✅ اشتراک ویژه"
    
    today = str(datetime.now().date())
    if user.get('last_download_date') != today:
        users[str(user_id)]['daily_downloads'] = 0
        users[str(user_id)]['last_download_date'] = today
        save_users(users)
    
    if user.get('daily_downloads', 0) >= DAILY_LIMIT:
        return False, f"❌ محدودیت روزانه ({DAILY_LIMIT} دانلود) تمام شد! برای دانلود نامحدود اشتراک تهیه کن."
    
    return True, f"✅ {DAILY_LIMIT - user.get('daily_downloads', 0)} دانلود باقی مونده"

def increment_download(user_id):
    user = users.get(str(user_id), {})
    if not is_premium(user_id):
        users[str(user_id)]['daily_downloads'] = user.get('daily_downloads', 0) + 1
        users[str(user_id)]['total_downloads'] = user.get('total_downloads', 0) + 1
        save_users(users)

users = load_users()

# ========== کیبورد اصلی ==========
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("📥 دانلود ویدیو", "🎵 دانلود صدا")
    markup.add("👤 حساب من", "⭐ ارتقا به ویژه")
    markup.add("📜 راهنما")
    return markup

# ========== تابع دانلود یوتیوب ==========
def download_youtube(link, is_audio=False):
    try:
        if not os.path.exists('downloads'):
            os.makedirs('downloads')
        
        ydl_opts = {
            'outtmpl': 'downloads/%(title)s_%(id)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'no_check_certificate': True,
            'format': 'best[height<=720]' if not is_audio else 'bestaudio/best',
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
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=True)
            if info:
                filename = ydl.prepare_filename(info)
                if not os.path.exists(filename):
                    for f in os.listdir('downloads'):
                        if info.get('id') and info['id'] in f:
                            return os.path.join('downloads', f), "✅ دانلود انجام شد!"
                return filename, "✅ دانلود انجام شد!"
        
        return None, "❌ دانلود ناموفق!"
        
    except Exception as e:
        return None, f"❌ خطا: {str(e)[:80]}"

# ========== تابع دانلود اینستاگرام ==========
def download_instagram(link):
    try:
        import yt_dlp
        
        if not os.path.exists('downloads'):
            os.makedirs('downloads')
        
        shortcode = None
        if '/reel/' in link:
            shortcode = link.split('/reel/')[1].split('/')[0]
        elif '/p/' in link:
            shortcode = link.split('/p/')[1].split('/')[0]
        else:
            return None, "❌ لینک اینستاگرام معتبر نیست!"
        
        ydl_opts = {
            'outtmpl': f'downloads/instagram_{shortcode}.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'no_check_certificate': True,
            'format': 'best',
            'merge_output_format': 'mp4',
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            },
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=True)
            if info:
                filename = ydl.prepare_filename(info)
                if os.path.exists(filename):
                    return filename, "✅ ویدیو دانلود شد!"
        
        return None, "❌ دانلود ناموفق!"
        
    except Exception as e:
        return None, f"❌ خطا: {str(e)[:80]}"

# ========== تابع ارسال فایل ==========
def send_file(message, filename, result, user_id):
    if filename and os.path.exists(filename):
        try:
            file_size = os.path.getsize(filename) / (1024 * 1024)
            max_size = PREMIUM_MAX_SIZE_MB if is_premium(user_id) else MAX_FILE_SIZE_MB
            
            if file_size > max_size:
                if is_premium(user_id):
                    bot.reply_to(message, f"⚠️ حجم فایل {file_size:.1f} مگابایت هست که از حد مجاز اشتراک ویژه ({max_size} مگابایت) بیشتره!")
                else:
                    bot.reply_to(message, f"⚠️ حجم فایل {file_size:.1f} مگابایت هست. برای دانلود فایل‌های بزرگتر، اشتراک ویژه تهیه کن! (حداکثر {max_size} مگابایت)")
                os.remove(filename)
                return
            
            # اگه فایل بزرگتر از ۵۰ مگابایت بود، لینک دانلود بفرست
            if file_size > 50:
                file_name = os.path.basename(filename)
                download_link = f"{BASE_URL}/download/{file_name}"
                
                bot.reply_to(message, 
                    f"📥 **فایل شما آماده دانلود است!**\n\n"
                    f"📁 حجم: {file_size:.1f} مگابایت\n"
                    f"🔗 لینک دانلود:\n`{download_link}`\n\n"
                    f"💡 روی لینک کلیک کن یا کپی کن و توی مرورگر بذار.",
                    parse_mode='Markdown'
                )
                
                def delete_later():
                    time.sleep(3600)
                    if os.path.exists(filename):
                        os.remove(filename)
                threading.Thread(target=delete_later).start()
                
                increment_download(user_id)
                return
            
            # فایل‌های کوچک‌تر از ۵۰ مگابایت مستقیم توی تلگرام
            with open(filename, 'rb') as f:
                if filename.endswith('.mp4'):
                    bot.send_video(message.chat.id, f, caption=result, supports_streaming=True)
                elif filename.endswith('.mp3'):
                    bot.send_audio(message.chat.id, f, caption=result)
                else:
                    bot.send_document(message.chat.id, f, caption=result)
            
            os.remove(filename)
            
            increment_download(user_id)
            
            if not is_premium(user_id):
                remaining = DAILY_LIMIT - users[str(user_id)].get('daily_downloads', 0)
                bot.reply_to(message, f"✅ فایل ارسال شد! {remaining} دانلود امروز باقی مونده.")
            else:
                bot.reply_to(message, "✅ فایل با موفقیت ارسال شد! (اشتراک ویژه)")
            
        except Exception as e:
            bot.reply_to(message, f"❌ خطا در ارسال: {str(e)[:80]}")
            if os.path.exists(filename):
                os.remove(filename)
    else:
        bot.reply_to(message, result)

# ========== پردازش لینک ==========
def process_link(message, is_audio=False):
    user_id = message.from_user.id
    text = message.text
    
    can, msg = can_download(user_id)
    if not can:
        bot.reply_to(message, msg)
        return
    
    youtube_pattern = r'(https?://(?:www\.)?(?:youtube\.com|youtu\.be)/[\w\-/?=&]+)'
    instagram_pattern = r'(https?://(?:www\.)?instagram\.com/[\w\-/]+)'
    
    youtube_match = re.search(youtube_pattern, text)
    instagram_match = re.search(instagram_pattern, text)
    
    if youtube_match:
        link = youtube_match.group(1)
        bot.reply_to(message, "⏳ در حال دانلود... لطفاً صبر کن")
        filename, result = download_youtube(link, is_audio)
        send_file(message, filename, result, user_id)
        
    elif instagram_match:
        link = instagram_match.group(1)
        bot.reply_to(message, "⏳ در حال دانلود از اینستاگرام...")
        filename, result = download_instagram(link)
        send_file(message, filename, result, user_id)
        
    else:
        bot.reply_to(message, 
            "❌ لطفاً یک لینک معتبر بفرست.\n\n"
            "پشتیبانی از:\n"
            "• یوتیوب: youtube.com یا youtu.be\n"
            "• اینستاگرام: instagram.com/reel/ یا /p/"
        )

# ========== دستورات ==========
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    init_user(user_id, message.from_user.username or "")
    
    premium_status = "✅ فعال" if is_premium(user_id) else "❌ غیرفعال"
    
    bot.reply_to(message, 
        f"🎬 **به ربات دانلودر حرفه‌ای خوش آمدی!**\n\n"
        f"👤 وضعیت: {premium_status}\n"
        f"📥 لینک یوتیوب یا اینستاگرام رو بفرست.\n\n"
        f"🔹 **قابلیت‌ها:**\n"
        f"• دانلود ویدیو و صدا از یوتیوب\n"
        f"• دانلود ریلز و پست اینستاگرام\n"
        f"• کیفیت بالا (720p)\n"
        f"• بدون محدودیت با اشتراک ویژه\n\n"
        f"⭐ برای دانلود نامحدود، از دکمه «ارتقا به ویژه» استفاده کن.",
        reply_markup=main_keyboard()
    )

@bot.message_handler(func=lambda m: m.text == "📥 دانلود ویدیو")
def video_download(message):
    bot.reply_to(message, "📹 **لینک یوتیوب یا اینستاگرام رو بفرست.**")
    bot.register_next_step_handler(message, lambda m: process_link(m, is_audio=False))

@bot.message_handler(func=lambda m: m.text == "🎵 دانلود صدا")
def audio_download(message):
    bot.reply_to(message, "🎵 **لینک یوتیوب رو بفرست تا آهنگ دانلود بشه.**")
    bot.register_next_step_handler(message, lambda m: process_link(m, is_audio=True))

@bot.message_handler(func=lambda m: m.text == "👤 حساب من")
def profile(message):
    user_id = message.from_user.id
    user = users.get(str(user_id), {})
    
    premium_status = "✅ فعال" if is_premium(user_id) else "❌ غیرفعال"
    expiry = user.get('premium_expiry', 'ندارد')
    daily = user.get('daily_downloads', 0)
    total = user.get('total_downloads', 0)
    
    if is_premium(user_id):
        expiry_date = datetime.fromisoformat(expiry)
        days_left = (expiry_date - datetime.now()).days
        expiry_text = f"{days_left} روز باقی مونده"
    else:
        expiry_text = "ندارد"
    
    text = f"""👤 **حساب کاربری من**

🆔 شناسه: `{user_id}`
👤 نام: {message.from_user.first_name}

⭐ وضعیت اشتراک: {premium_status}
📅 تاریخ انقضا: {expiry_text}
📊 دانلود امروز: {daily} از {DAILY_LIMIT}
📈 مجموع دانلود: {total}

💳 برای خرید اشتراک، روی دکمه «ارتقا به ویژه» کلیک کن.
"""
    bot.reply_to(message, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "⭐ ارتقا به ویژه")
def upgrade(message):
    user_id = message.from_user.id
    init_user(user_id, message.from_user.username or "")
    
    if is_premium(user_id):
        expiry = users[str(user_id)].get('premium_expiry')
        if expiry:
            expiry_date = datetime.fromisoformat(expiry)
            days_left = (expiry_date - datetime.now()).days
            bot.reply_to(message, f"✅ شما هم‌اکنون اشتراک ویژه دارید!\n📅 {days_left} روز باقی مونده.")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📅 ۱ ماهه - ۱۵۰,۰۰۰ تومان", callback_data="buy_1month"),
        types.InlineKeyboardButton("📅 ۳ ماهه - ۳۵۰,۰۰۰ تومان", callback_data="buy_3month"),
        types.InlineKeyboardButton("📅 ۶ ماهه - ۶۰۰,۰۰۰ تومان", callback_data="buy_6month"),
        types.InlineKeyboardButton("📅 ۱ ساله - ۱,۰۰۰,۰۰۰ تومان", callback_data="buy_1year")
    )
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_main"))
    
    bot.reply_to(message,
        "⭐ **ارتقا به اشتراک ویژه**\n\n"
        "با تهیه اشتراک ویژه، می‌تونی:\n"
        "✅ دانلود نامحدود روزانه\n"
        "✅ دانلود فایل‌های تا ۵۰۰ مگابایت\n"
        "✅ پشتیبانی優先\n\n"
        "لطفاً یکی از پلن‌های زیر رو انتخاب کن:",
        reply_markup=markup
    )

@bot.message_handler(func=lambda m: m.text == "📜 راهنما")
def help_btn(message):
    bot.reply_to(message,
        "📜 **راهنمای ربات**\n\n"
        "🔹 **نحوه استفاده:**\n"
        "1️⃣ لینک یوتیوب یا اینستاگرام رو کپی کن\n"
        "2️⃣ روی دکمه «دانلود ویدیو» بزن و لینک رو بفرست\n"
        "3️⃣ ویدیو با کیفیت بالا برات ارسال میشه\n\n"
        "🔹 **محدودیت‌های رایگان:**\n"
        f"• روزانه {DAILY_LIMIT} دانلود\n"
        f"• حداکثر حجم {MAX_FILE_SIZE_MB} مگابایت\n\n"
        "⭐ **مزایای اشتراک ویژه:**\n"
        "• دانلود نامحدود\n"
        f"• حجم فایل تا {PREMIUM_MAX_SIZE_MB} مگابایت\n"
        "• کیفیت بالا\n\n"
        "📞 پشتیبانی: @hegzosupport"
    )

# ========== دکمه‌های اینلاین ==========
@bot.callback_query_handler(func=lambda call: call.data == "back_main")
def back_main(call):
    bot.edit_message_text(
        "🏠 **صفحه اصلی**",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=None
    )
    bot.send_message(call.message.chat.id, "به صفحه اصلی برگشتی.", reply_markup=main_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def process_buy(call):
    user_id = call.from_user.id
    plan = call.data.split("_")[1]
    price = PRICES.get(plan, 0)
    plan_name = PLANS.get(plan, "نامشخص")
    
    if not price:
        bot.answer_callback_query(call.id, "❌ خطا در پردازش!", show_alert=True)
        return
    
    users[str(user_id)]['pending_payment'] = {
        'plan': plan,
        'price': price,
        'date': str(datetime.now())
    }
    save_users(users)
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ رسید رو ارسال کردم", callback_data="send_receipt"))
    markup.add(types.InlineKeyboardButton("🔙 انصراف", callback_data="back_main"))
    
    bot.edit_message_text(
        f"💳 **ثبت درخواست خرید {plan_name}**\n\n"
        f"💰 مبلغ: {price:,} تومان\n\n"
        f"🏦 **شماره کارت:**\n`{CARD_NUMBER}`\n"
        f"👤 **به نام:** {CARD_NAME}\n\n"
        f"📌 **مراحل:**\n"
        f"1️⃣ مبلغ {price:,} تومان رو به کارت بالا واریز کن\n"
        f"2️⃣ از رسید واریز اسکرین‌شات بگیر\n"
        f"3️⃣ روی دکمه «رسید رو ارسال کردم» بزن و عکس رو بفرست\n\n"
        f"⏳ پس از تایید ادمین، اشتراک شما فعال میشه.",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode='Markdown'
    )
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "send_receipt")
def send_receipt(call):
    user_id = call.from_user.id
    
    if not users[str(user_id)].get('pending_payment'):
        bot.answer_callback_query(call.id, "❌ درخواست خرید پیدا نشد!", show_alert=True)
        return
    
    bot.edit_message_text(
        "📸 **لطفاً عکس رسید واریز رو بفرست.**",
        call.message.chat.id,
        call.message.message_id
    )
    bot.answer_callback_query(call.id)
    bot.register_next_step_handler(call.message, receipt_handler)

def receipt_handler(message):
    user_id = message.from_user.id
    pending = users[str(user_id)].get('pending_payment')
    
    if not pending:
        bot.reply_to(message, "❌ درخواستی برای پرداخت وجود ندارد!")
        return
    
    if not message.photo:
        bot.reply_to(message, "❌ لطفاً یه عکس از رسید بفرست!")
        bot.register_next_step_handler(message, receipt_handler)
        return
    
    file_id = message.photo[-1].file_id
    plan_name = PLANS.get(pending['plan'], 'نامشخص')
    price = pending['price']
    
    admin_text = f"""💳 **درخواست خرید جدید**

👤 کاربر: @{message.from_user.username or 'بدون نام'}
🆔 شناسه: `{user_id}`
📦 پلن: {plan_name}
💰 مبلغ: {price:,} تومان

📅 تاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ تایید", callback_data=f"approve_{user_id}"),
        types.InlineKeyboardButton("❌ رد", callback_data=f"reject_{user_id}")
    )
    
    bot.send_photo(ADMIN_ID, file_id, caption=admin_text, reply_markup=markup, parse_mode='Markdown')
    bot.reply_to(message, "✅ رسید شما به ادمین ارسال شد. پس از تایید، اشتراک شما فعال میشه.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_"))
def approve_payment(call):
    if str(call.from_user.id) != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    
    user_id = int(call.data.split("_")[1])
    pending = users.get(str(user_id), {}).get('pending_payment')
    
    if not pending:
        bot.answer_callback_query(call.id, "❌ درخواست پیدا نشد!", show_alert=True)
        return
    
    plan = pending['plan']
    days = {
        '1month': 30,
        '3month': 90,
        '6month': 180,
        '1year': 365
    }.get(plan, 30)
    
    expiry_date = datetime.now() + timedelta(days=days)
    users[str(user_id)]['is_premium'] = True
    users[str(user_id)]['premium_expiry'] = str(expiry_date)
    users[str(user_id)]['pending_payment'] = None
    save_users(users)
    
    bot.send_message(user_id, 
        f"✅ **اشتراک ویژه شما فعال شد!**\n\n"
        f"📦 پلن: {PLANS.get(plan, 'نامشخص')}\n"
        f"📅 تاریخ انقضا: {expiry_date.strftime('%Y-%m-%d')}\n\n"
        f"🎉 از دانلود نامحدود لذت ببر!"
    )
    
    bot.edit_message_caption(
        f"✅ تایید شد - {PLANS.get(plan, 'نامشخص')}",
        call.message.chat.id,
        call.message.message_id
    )
    bot.answer_callback_query(call.id, "✅ تایید شد!")

@bot.callback_query_handler(func=lambda call: call.data.startswith("reject_"))
def reject_payment(call):
    if str(call.from_user.id) != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    
    user_id = int(call.data.split("_")[1])
    users[str(user_id)]['pending_payment'] = None
    save_users(users)
    
    bot.send_message(user_id, "❌ درخواست خرید شما رد شد. با پشتیبانی تماس بگیرید: @hegzosupport")
    
    bot.edit_message_caption(
        "❌ رد شد",
        call.message.chat.id,
        call.message.message_id
    )
    bot.answer_callback_query(call.id, "❌ رد شد!")

# ========== دریافت لینک مستقیم ==========
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    text = message.text
    
    youtube_pattern = r'(https?://(?:www\.)?(?:youtube\.com|youtu\.be)/[\w\-/?=&]+)'
    instagram_pattern = r'(https?://(?:www\.)?instagram\.com/[\w\-/]+)'
    
    if re.search(youtube_pattern, text) or re.search(instagram_pattern, text):
        process_link(message, is_audio=False)
    else:
        bot.reply_to(message, 
            "❌ دستور یا لینک معتبر نیست.\n\n"
            "لینک یوتیوب یا اینستاگرام بفرست یا از دکمه‌ها استفاده کن.",
            reply_markup=main_keyboard()
        )

# ========== اجرا ==========
if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 10000))
    
    if not os.path.exists('downloads'):
        os.makedirs('downloads')
    
    print("🎬 ربات دانلودر حرفه‌ای روشن شد!")
    
    try:
        bot.remove_webhook()
    except:
        pass
    
    time.sleep(1)
    
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)).start()
    
    bot.infinity_polling()
