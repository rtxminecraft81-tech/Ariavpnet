import telebot
from telebot import types
import json
import os
import time
from datetime import datetime
from flask import Flask
import threading
import random

app = Flask(__name__)

@app.route('/')
def home():
    return "Hegzo VPN Bot is running!", 200

TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    raise ValueError("❌ توکن پیدا نشد! BOT_TOKEN رو توی Render تنظیم کن.")

ADMIN_ID = '6795169616'
CHANNEL_USERNAME = '@hegzo_vpn_channle'
CARD_NUMBER = '5022291525516892'
CARD_NAME = 'احمد خزایی'
REFERRAL_AMOUNT = 5000

bot = telebot.TeleBot(TOKEN)
USER_DB = 'users.json'

# استیکرهای خفن
STICKERS = {
    'welcome': 'CAACAgQAAxkBAAE...',  # استیکر خوش‌آمدگویی
    'success': 'CAACAgQAAxkBAAE...',   # استیکر موفقیت
    'error': 'CAACAgQAAxkBAAE...',     # استیکر خطا
    'money': 'CAACAgQAAxkBAAE...',     # استیکر پول
    'fire': 'CAACAgQAAxkBAAE...',      # استیکر آتیش
    'cool': 'CAACAgQAAxkBAAE...',      # استیکر عینکی
}

# لیست ایموجی‌های متحرک
EMOJIS = {
    'loading': ['⏳', '🔄', '⚡', '💫'],
    'success': ['✅', '🎉', '🎊', '✨', '💎'],
    'error': ['❌', '⛔', '🚫', '💢'],
    'money': ['💰', '💸', '🤑', '💵'],
    'fire': ['🔥', '❤️‍🔥', '⚡', '🌟'],
}

def get_random_emoji(category):
    return random.choice(EMOJIS.get(category, ['✨']))

def loading_animation(message, text, duration=2):
    """ارسال انیمیشن بارگذاری"""
    msg = bot.reply_to(message, f"{get_random_emoji('loading')} {text}")
    time.sleep(duration)
    return msg

def delete_with_animation(message, delay=0.5):
    """حذف پیام با انیمیشن"""
    try:
        time.sleep(delay)
        bot.delete_message(message.chat.id, message.message_id)
    except:
        pass

def send_sticker(user_id, sticker_key):
    """ارسال استیکر"""
    try:
        if sticker_key in STICKERS:
            bot.send_sticker(user_id, STICKERS[sticker_key])
    except:
        pass

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
            'credit': 0,
            'active_configs': [],
            'pending_charge': 0,
            'invited_by': None,
            'referrals': 0,
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

def animated_keyboard(text, keyboard_type='main'):
    """کیبورد با انیمیشن و افکت"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    if keyboard_type == 'main':
        markup.add("💳 شارژ کیف پول", "🛒 خرید کانفیگ")
        markup.add("📁 کانفیگ‌های من", "👤 حساب کاربری")
        markup.add("👥 دعوت از دوستان", "🆘 پشتیبانی")
        markup.add("🏠 منوی اصلی")
    elif keyboard_type == 'payment':
        markup.add("💰 شارژ با کارت", "🔄 شارژ با رمز")
        markup.add("🔙 بازگشت")
    elif keyboard_type == 'config':
        markup.add("📦 خرید بسته جدید", "📁 کانفیگ‌های فعال")
        markup.add("🔙 بازگشت")
    
    return markup

def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("💳 شارژ کیف پول", "🛒 خرید کانفیگ")
    markup.add("📁 کانفیگ‌های من", "👤 حساب کاربری")
    markup.add("👥 دعوت از دوستان", "🆘 پشتیبانی")
    markup.add("🏠 منوی اصلی")
    return markup

def admin_buttons(user_id, package, price):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ تایید", callback_data=f"ok_{user_id}_{package}_{price}"),
        types.InlineKeyboardButton("❌ رد", callback_data=f"no_{user_id}"),
        types.InlineKeyboardButton("✏️ ارسال دستی", callback_data=f"send_{user_id}_{package}_{price}")
    )
    return markup

def admin_charge_buttons(user_id, amount):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ تایید شارژ", callback_data=f"ch_ok_{user_id}_{amount}"),
        types.InlineKeyboardButton("❌ رد شارژ", callback_data=f"ch_no_{user_id}")
    )
    return markup

def buy_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("💰 اقتصادی", callback_data="lev_eco"))
    markup.add(types.InlineKeyboardButton("🎮 گیمینگ", callback_data="lev_gaming"))
    markup.add(types.InlineKeyboardButton("👨‍👩‍👧‍👦 خانواده", callback_data="lev_family"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_main"))
    return markup

def eco_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("25 گیگ - 180,000 تومان (سرعت 4 مگابیت)", callback_data="b_eco25_180000"))
    markup.add(types.InlineKeyboardButton("50 گیگ - 250,000 تومان (سرعت 4 مگابیت)", callback_data="b_eco50_250000"))
    markup.add(types.InlineKeyboardButton("100 گیگ - 450,000 تومان (سرعت 4 مگابیت)", callback_data="b_eco100_450000"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_buy"))
    return markup

def gaming_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("20 گیگ - 200,000 تومان", callback_data="b_gaming20_200000"))
    markup.add(types.InlineKeyboardButton("30 گیگ - 250,000 تومان", callback_data="b_gaming30_250000"))
    markup.add(types.InlineKeyboardButton("50 گیگ - 400,000 تومان", callback_data="b_gaming50_400000"))
    markup.add(types.InlineKeyboardButton("100 گیگ - 700,000 تومان", callback_data="b_gaming100_700000"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_buy"))
    return markup

def family_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("100 گیگ تک کاربره - 1 ماهه 199,000 تومان", callback_data="b_family1_199000"))
    markup.add(types.InlineKeyboardButton("100 گیگ 2 کاربر - 1 ماهه 249,000 تومان", callback_data="b_family2_249000"))
    markup.add(types.InlineKeyboardButton("100 گیگ 3 کاربر - 1 ماهه 299,000 تومان", callback_data="b_family3_299000"))
    markup.add(types.InlineKeyboardButton("100 گیگ 4 کاربر - 1 ماهه 349,000 تومان", callback_data="b_family4_349000"))
    markup.add(types.InlineKeyboardButton("10 روزه تک کاربر نامحدود - 99,000 تومان", callback_data="b_familyunlimited_99000"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_buy"))
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if is_banned(user_id):
        bot.reply_to(message, "⛔ شما توسط ادمین مسدود شده اید!\n🆔 @bintc")
        return
    
    # انیمیشن خوش‌آمدگویی
    loading_msg = loading_animation(message, "🔥 در حال آماده‌سازی...", 1.5)
    delete_with_animation(loading_msg, 0.3)
    
    name = message.from_user.first_name
    init_user(user_id, message.from_user.username or "")
    
    if len(message.text.split()) > 1:
        try:
            ref = int(message.text.split()[1])
            if ref != user_id and str(ref) in users and not users[str(user_id)].get('invited_by'):
                users[str(ref)]['referrals'] += 1
                users[str(user_id)]['invited_by'] = ref
                users[str(ref)]['credit'] += REFERRAL_AMOUNT
                save_users(users)
                bot.send_message(ref, f"🎉 کاربر جدید با لینک شما عضو شد!\n💰 {REFERRAL_AMOUNT:,} تومان به حسابت اضافه شد!")
                send_sticker(ref, 'money')
        except:
            pass
    
    if not is_member(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔗 عضویت در کانال", url="https://t.me/hegzo_vpn_channle"))
        bot.reply_to(message, f"❌ سلام {name} عزیز!\n\nلطفا در کانال عضو شوید.", reply_markup=markup)
        return
    
    send_sticker(user_id, 'welcome')
    bot.reply_to(message, 
        f"""🔥 **به 𝑯𝑬𝑮𝒁𝑶 𝑽𝑷𝑵 خوش اومدی** {name}! 🎉

⚡ **اینترنت آزاد و بدون محدودیت**
🛡️ **امنیت کامل و سرعت بالا**
💎 **کیفیت عالی با قیمت مناسب**

✨ از منوی زیر یکی رو انتخاب کن:
""", 
        reply_markup=main_keyboard(), 
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda m: m.text == "🏠 منوی اصلی")
def back_home(m):
    # انیمیشن بازگشت
    loading_msg = loading_animation(m, "🔄 در حال بازگشت به منوی اصلی...", 1)
    delete_with_animation(loading_msg, 0.3)
    
    bot.reply_to(m, 
        f"🔥 **منوی اصلی 𝑯𝑬𝑮𝒁𝑶 𝑽𝑷𝑵**\n\n{get_random_emoji('fire')} آماده خدمت‌رسانی هستم!",
        reply_markup=main_keyboard()
    )

@bot.message_handler(func=lambda m: m.text == "🛒 خرید کانفیگ")
def show_buy(m):
    loading_msg = loading_animation(m, "📦 در حال بارگذاری سرویس‌ها...", 1)
    delete_with_animation(loading_msg, 0.3)
    
    bot.reply_to(m, 
        f"📊 **انتخاب نوع سرویس**\n\n{get_random_emoji('fire')} بهترین سرویس رو انتخاب کن:",
        reply_markup=buy_menu(),
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda m: m.text == "👤 حساب کاربری")
def profile(m):
    user_id = m.from_user.id
    data = users.get(str(user_id), {})
    active_count = len(data.get('active_configs', []))
    
    loading_msg = loading_animation(m, "📊 در حال دریافت اطلاعات...", 1)
    delete_with_animation(loading_msg, 0.3)
    
    text = f"""👤 **حساب کاربری 𝑯𝑬𝑮𝒁𝑶 𝑽𝑷𝑵**

━━━━━━━━━━━━━━━━━━━━━
🆔 شناسه: `{user_id}`
👤 نام: {m.from_user.first_name}
📊 کانفیگ فعال: {active_count}
👥 زیرمجموعه: {data.get('referrals', 0)}
💰 اعتبار کیف پول: {data.get('credit', 0):,} تومان
━━━━━━━━━━━━━━━━━━━━━

{get_random_emoji('success')} کاربر عزیز، همیشه در کنارتیم!"""
    
    send_sticker(user_id, 'cool')
    bot.reply_to(m, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "👥 دعوت از دوستان")
def invite(m):
    user_id = m.from_user.id
    link = f"https://t.me/{bot.get_me().username}?start={user_id}"
    data = users.get(str(user_id), {})
    
    text = f"""🔥 **لینک دعوت اختصاصی شما**

`{link}`

👥 دعوت‌ها: {data.get('referrals', 0)}
💰 هر دعوت = {REFERRAL_AMOUNT:,} تومان اعتبار

{get_random_emoji('money')} هرچه دوستان بیشتری دعوت کنی، اعتبار بیشتری میگیری!"""
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📤 اشتراک‌گذاری لینک", url=f"https://t.me/share/url?url={link}&text=🔥 به ربات Hegzo VPN بپیوند! اینترنت آزاد و بدون محدودیت!"))
    
    bot.reply_to(m, text, parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🆘 پشتیبانی")
def support(m):
    send_sticker(m.from_user.id, 'fire')
    bot.reply_to(m, 
        f"""🆔 **پشتیبانی 𝑯𝑬𝑮𝒁𝑶 𝑽𝑷𝑵**

{get_random_emoji('success')} ۲۴ ساعته پاسخگوی شما هستیم!

📱 @hegzosupport

⚠️ لطفاً قبل از تماس، سوال خود را دقیق مطرح کنید تا سریع‌تر پاسخ بگیرید.""",
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda m: m.text == "💳 شارژ کیف پول")
def charge(m):
    user_id = m.from_user.id
    
    text = f"""💳 **شارژ کیف پول 𝑯𝑬𝑮𝒁𝑶 𝑽𝑷𝑵**

━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 **حداقل شارژ:** 200,000 تومان
━━━━━━━━━━━━━━━━━━━━━━━━━━━

💳 **شماره کارت:** `{CARD_NUMBER}`
🏦 **به نام:** {CARD_NAME}

📌 **راهنمای واریز:**
1️⃣ مبلغ مورد نظر را به کارت بالا واریز کنید
2️⃣ از رسید واریز اسکرین‌شات بگیرید
3️⃣ همینجا در ربات عکس رسید را بفرستید
4️⃣ ادمین رسید را بررسی کرده و کیف پول شما را شارژ می‌کند

⚠️ **نکات مهم:**
• پس از واریز، حتما رسید را بفرستید
• کد پیگیری رسید را برای پیگیری نگهداری کنید

🆔 پشتیبانی: @bintc
━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 لطفا مبلغ مورد نظر را وارد کنید (به تومان):"""
    
    send_sticker(user_id, 'money')
    bot.reply_to(m, text, parse_mode='Markdown')
    bot.register_next_step_handler(m, get_amount)

def get_amount(m):
    user_id = m.from_user.id
    try:
        amount = int(m.text)
        if amount < 200000:
            bot.reply_to(m, f"❌ **حداقل شارژ 200,000 تومان است!**\n\n{get_random_emoji('error')} لطفاً مبلغ بیشتر یا مساوی ۲۰۰,۰۰۰ تومان وارد کن.", parse_mode='Markdown')
            return
        users[str(user_id)]['pending_charge'] = amount
        save_users(users)
        bot.reply_to(m, f"✅ **درخواست شارژ {amount:,} تومانی ثبت شد!**\n\n📸 لطفا رسید واریز را بفرستید.\n\n{get_random_emoji('loading')} منتظر تایید ادمین باشید.")
    except:
        bot.reply_to(m, 
            f"😎 **اوه! انگار نه انگار!**\n\n{get_random_emoji('error')} لطفاً یه عدد معتبر وارد کن!\n\nمثلاً: 200000",
            parse_mode='Markdown'
        )

@bot.message_handler(content_types=['photo'])
def receipt(m):
    user_id = m.from_user.id
    username = m.from_user.username or "بدون نام"
    file_id = m.photo[-1].file_id
    pending = users.get(str(user_id), {}).get('pending_charge', 0)
    
    if pending > 0:
        admin_text = f"💰 **درخواست شارژ!**\n👤 @{username}\n🆔 {user_id}\n💸 مبلغ: {pending:,} تومان"
        bot.send_photo(ADMIN_ID, file_id, caption=admin_text, reply_markup=admin_charge_buttons(user_id, pending), parse_mode='Markdown')
        
        loading_msg = loading_animation(m, "📤 در حال ارسال رسید...", 1)
        delete_with_animation(loading_msg, 0.3)
        
        bot.reply_to(m, f"✅ **رسید شما دریافت شد!**\n\n{get_random_emoji('loading')} در حال بررسی توسط ادمین...\n\n⏳ لطفاً چند دقیقه صبر کنید.")
        users[str(user_id)]['pending_charge'] = 0
        save_users(users)
        send_sticker(user_id, 'success')
    else:
        bot.reply_to(m, f"❌ **ابتدا از منوی اصلی روی 💳 شارژ کیف پول کلیک کن و مبلغ را وارد کن.**\n\n{get_random_emoji('error')}", parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "📁 کانفیگ‌های من")
def my_configs_list(m):
    user_id = m.from_user.id
    cfg_list = users.get(str(user_id), {}).get('active_configs', [])
    
    loading_msg = loading_animation(m, "📁 در حال دریافت کانفیگ‌ها...", 1)
    delete_with_animation(loading_msg, 0.3)
    
    if not cfg_list:
        bot.reply_to(m, 
            f"📭 **کانفیگ فعالی ندارید!**\n\n{get_random_emoji('error')} برای خرید کانفیگ از بخش 🛒 خرید کانفیگ اقدام کنید.",
            parse_mode='Markdown'
        )
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for i, cfg in enumerate(cfg_list):
        package = cfg.get('package', 'نامشخص')
        date = cfg.get('date', 'نامشخص')[:10]
        markup.add(types.InlineKeyboardButton(f"{i+1}. {package} ({date})", callback_data=f"showcfg_{i}"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_main"))
    
    bot.reply_to(m, 
        f"📦 **لیست کانفیگ‌های فعال شما**\n\n{get_random_emoji('fire')} {len(cfg_list)} کانفیگ فعال داری!\n\nلطفا یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("showcfg_"))
def show_config_detail(call):
    user_id = call.from_user.id
    idx = int(call.data.split("_")[1])
    cfg_list = users.get(str(user_id), {}).get('active_configs', [])
    
    if idx >= len(cfg_list):
        bot.answer_callback_query(call.id, "❌ کانفیگ مورد نظر یافت نشد!", show_alert=True)
        return
    
    cfg = cfg_list[idx]
    package = cfg.get('package', 'نامشخص')
    config = cfg.get('config', 'نامشخص')
    date = cfg.get('date', 'نامشخص')
    price = cfg.get('price', 'نامشخص')
    
    text = f"""📦 **جزئیات کانفیگ {idx+1}**

━━━━━━━━━━━━━━━━━━━━━
📌 **بسته:** {package}
💰 **مبلغ:** {price:,} تومان
📅 **تاریخ دریافت:** {date}
━━━━━━━━━━━━━━━━━━━━━
🔗 **لینک کانفیگ:**
`{config}`
━━━━━━━━━━━━━━━━━━━━━
💡 **نحوه استفاده:**
روی لینک بالا فشار طولانی بدید و Copy رو بزنید، سپس در برنامه V2rayNG یا NPV Tunnel وارد کنید.
━━━━━━━━━━━━━━━━━━━━━
🆔 پشتیبانی: @bintc"""
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 بازگشت به لیست کانفیگ‌ها", callback_data="back_to_configs"))
    markup.add(types.InlineKeyboardButton("🏠 بازگشت به منوی اصلی", callback_data="back_main"))
    
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
    except:
        bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_configs")
def back_to_configs(call):
    user_id = call.from_user.id
    cfg_list = users.get(str(user_id), {}).get('active_configs', [])
    
    if not cfg_list:
        try:
            bot.edit_message_text("📭 کانفیگ فعالی ندارید!", call.message.chat.id, call.message.message_id, parse_mode='Markdown')
        except:
            bot.send_message(call.message.chat.id, "📭 کانفیگ فعالی ندارید!", parse_mode='Markdown')
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for i, cfg in enumerate(cfg_list):
        package = cfg.get('package', 'نامشخص')
        date = cfg.get('date', 'نامشخص')[:10]
        markup.add(types.InlineKeyboardButton(f"{i+1}. {package} ({date})", callback_data=f"showcfg_{i}"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_main"))
    
    try:
        bot.edit_message_text("📦 **لیست کانفیگ‌های فعال شما**\n\nلطفا یکی از گزینه‌های زیر را انتخاب کنید:", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
    except:
        bot.send_message(call.message.chat.id, "📦 **لیست کانفیگ‌های فعال شما**\n\nلطفا یکی از گزینه‌های زیر را انتخاب کنید:", reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "lev_eco")
def lev_eco(call):
    try:
        bot.edit_message_text("💰 **سرور اقتصادی Hegzo VPN**\n\nلطفا یکی از بسته‌های زیر را انتخاب کنید:", call.message.chat.id, call.message.message_id, reply_markup=eco_menu(), parse_mode='Markdown')
    except:
        bot.send_message(call.message.chat.id, "💰 **سرور اقتصادی Hegzo VPN**\n\nلطفا یکی از بسته‌های زیر را انتخاب کنید:", reply_markup=eco_menu(), parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "lev_gaming")
def lev_gaming(call):
    try:
        bot.edit_message_text("🎮 **سرور گیمینگ Hegzo VPN**\n\nلطفا یکی از بسته‌های زیر را انتخاب کنید:", call.message.chat.id, call.message.message_id, reply_markup=gaming_menu(), parse_mode='Markdown')
    except:
        bot.send_message(call.message.chat.id, "🎮 **سرور گیمینگ Hegzo VPN**\n\nلطفا یکی از بسته‌های زیر را انتخاب کنید:", reply_markup=gaming_menu(), parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "lev_family")
def lev_family(call):
    try:
        bot.edit_message_text("👨‍👩‍👧‍👦 **بسته خانواده Hegzo VPN**\n\nلطفا یکی از بسته‌های زیر را انتخاب کنید:", call.message.chat.id, call.message.message_id, reply_markup=family_menu(), parse_mode='Markdown')
    except:
        bot.send_message(call.message.chat.id, "👨‍👩‍👧‍👦 **بسته خانواده Hegzo VPN**\n\nلطفا یکی از بسته‌های زیر را انتخاب کنید:", reply_markup=family_menu(), parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "back_buy")
def back_buy(call):
    try:
        bot.edit_message_text("📊 انتخاب نوع سرویس:", call.message.chat.id, call.message.message_id, reply_markup=buy_menu())
    except:
        bot.send_message(call.message.chat.id, "📊 انتخاب نوع سرویس:", reply_markup=buy_menu())

@bot.callback_query_handler(func=lambda call: call.data == "back_main")
def back_main(call):
    try:
        bot.edit_message_text("🔥 منوی اصلی:", call.message.chat.id, call.message.message_id, reply_markup=main_keyboard())
    except:
        bot.send_message(call.message.chat.id, "🔥 منوی اصلی:", reply_markup=main_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith("b_"))
def buy_cmd(call):
    user_id = call.from_user.id
    if is_banned(user_id):
        bot.answer_callback_query(call.id, "❌ شما مسدود شده اید!", show_alert=True)
        return
    
    parts = call.data.split("_")
    price = int(parts[-1])
    package = "_".join(parts[1:-1])
    
    credit = users.get(str(user_id), {}).get('credit', 0)
    if credit >= price:
        users[str(user_id)]['credit'] -= price
        save_users(users)
        username = call.from_user.username or "بدون نام"
        admin_text = f"📸 **درخواست کانفیگ جدید!**\n\n👤 کاربر: @{username}\n🆔 آیدی: {user_id}\n📦 بسته: {package}\n💰 مبلغ: {price:,} تومان"
        bot.send_message(ADMIN_ID, admin_text, reply_markup=admin_buttons(user_id, package, price), parse_mode='Markdown')
        
        bot.send_message(user_id, f"✅ **درخواست شما ثبت شد!**\n\n{get_random_emoji('loading')} منتظر تایید ادمین باشید.\n\n⏳ معمولاً کمتر از ۵ دقیقه طول می‌کشد.")
        bot.answer_callback_query(call.id, "✅ ثبت شد")
        send_sticker(user_id, 'fire')
        try:
            bot.edit_message_text("✅ درخواست ثبت شد. منتظر تایید ادمین.", call.message.chat.id, call.message.message_id)
        except:
            pass
    else:
        need = price - credit
        bot.send_message(user_id, 
            f"""❌ **اعتبار کافی نیست!**

💰 اعتبار شما: {credit:,} تومان
💸 نیاز به {need:,} تومان دیگر

{get_random_emoji('money')} برای افزایش اعتبار از منوی اصلی روی 💳 شارژ کیف پول کلیک کن.

💡 راهنمایی: می‌تونی با دعوت از دوستانت اعتبار رایگان بگیری!""",
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id, "❌ اعتبار کافی نیست")

@bot.callback_query_handler(func=lambda call: call.data.startswith("ok_"))
def confirm(call):
    if str(call.from_user.id) != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    
    parts = call.data.split("_")
    user_id = int(parts[1])
    package = parts[2]
    price = int(parts[3])
    
    bot.send_message(user_id, f"✅ **کانفیگ {package} تایید شد!**\n\n{get_random_emoji('success')} منتظر دریافت کانفیگ از ادمین باش.\n\n🆔 پشتیبانی: @bintc", parse_mode='Markdown')
    bot.answer_callback_query(call.id, "✅ تایید شد")
    send_sticker(user_id, 'success')
    try:
        bot.edit_message_caption(f"✅ تایید شد - {package}", call.message.chat.id, call.message.message_id)
    except:
        pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("no_"))
def reject(call):
    if str(call.from_user.id) != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    
    user_id = int(call.data.split("_")[1])
    
    bot.send_message(user_id, 
        f"""❌ **درخواست شما رد شد!**

{get_random_emoji('error')} لطفاً با پشتیبانی تماس بگیرید:

📱 @bintc

💡 دلیل احتمالی:
• اطلاعات ناقص
• مشکل در پرداخت
• بسته ناموجود""",
        parse_mode='Markdown'
    )
    bot.answer_callback_query(call.id, "❌ رد شد")
    try:
        bot.edit_message_caption("❌ رد شد", call.message.chat.id, call.message.message_id)
    except:
        pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("send_"))
def manual(call):
    if str(call.from_user.id) != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    
    parts = call.data.split("_")
    user_id = int(parts[1])
    package = parts[2]
    price = int(parts[3])
    
    bot.send_message(call.message.chat.id, f"📝 لطفا کانفیگ مورد نظر برای کاربر {user_id} (بسته: {package}) را بفرستید:")
    bot.register_next_step_handler(call.message, lambda m: send_config(m, user_id, package, price))
    bot.answer_callback_query(call.id)

def send_config(m, user_id, package, price):
    config = m.text
    if str(user_id) in users:
        users[str(user_id)].setdefault('active_configs', []).append({'package': package, 'config': config, 'date': str(datetime.now()), 'price': price})
        save_users(users)
    
    send_sticker(user_id, 'success')
    bot.send_message(user_id, 
        f"""🎁 **کانفیگ اختصاصی شما ({package})**

`{config}`

{get_random_emoji('success')} کانفیگ با موفقیت ثبت شد!

📅 تاریخ فعال‌سازی: {datetime.now().strftime('%Y-%m-%d %H:%M')}

🆔 پشتیبانی: @bintc""",
        parse_mode='Markdown'
    )
    bot.reply_to(m, "✅ کانفیگ با موفقیت ارسال شد")

@bot.callback_query_handler(func=lambda call: call.data.startswith("ch_ok_"))
def ch_ok(call):
    if str(call.from_user.id) != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    
    parts = call.data.split("_")
    user_id = int(parts[2])
    amount = int(parts[3])
    
    if str(user_id) in users:
        users[str(user_id)]['credit'] += amount
        save_users(users)
        
        send_sticker(user_id, 'money')
        bot.send_message(user_id, 
            f"""✅ **شارژ {amount:,} تومانی تایید شد!**

💰 اعتبار جدید: {users[str(user_id)]['credit']:,} تومان

{get_random_emoji('success')} حالا می‌تونی کانفیگ مورد نظرت رو بخری!

🛒 از منوی اصلی روی خرید کانفیگ کلیک کن.""",
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id, "✅ تایید شد")
        try:
            bot.edit_message_caption("✅ تایید شد", call.message.chat.id, call.message.message_id)
        except:
            pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("ch_no_"))
def ch_no(call):
    if str(call.from_user.id) != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    
    user_id = int(call.data.split("_")[2])
    
    if str(user_id) in users:
        bot.send_message(user_id, 
            f"""❌ **درخواست شارژ رد شد!**

{get_random_emoji('error')} لطفاً با پشتیبانی تماس بگیرید:

📱 @bintc

💡 نکته: حتماً رسید را به درستی ارسال کنید.""",
            parse_mode='Markdown'
        )
    bot.answer_callback_query(call.id, "❌ رد شد")
    try:
        bot.edit_message_caption("❌ رد شد", call.message.chat.id, call.message.message_id)
    except:
        pass

@bot.message_handler(commands=['users'])
def list_users(m):
    if str(m.from_user.id) != ADMIN_ID:
        return
    if not users:
        bot.reply_to(m, "📭 هیچ کاربری وجود ندارد.")
        return
    text = "📊 **لیست کاربران Hegzo VPN**\n\n"
    for uid, data in users.items():
        text += f"🆔 `{uid}` | اعتبار: {data.get('credit',0):,} | دعوت: {data.get('referrals',0)}\n"
    bot.reply_to(m, text, parse_mode='Markdown')

@bot.message_handler(commands=['broadcast'])
def broadcast_cmd(m):
    if str(m.from_user.id) != ADMIN_ID:
        return
    bot.reply_to(m, "📢 لطفا پیام خود را بفرستید:")
    bot.register_next_step_handler(m, do_broadcast)

def do_broadcast(m):
    if str(m.from_user.id) != ADMIN_ID:
        return
    msg = m.text
    success = 0
    fail = 0
    for uid in users.keys():
        try:
            bot.send_message(int(uid), f"📢 **پیام از ادمین Hegzo VPN**\n\n{msg}", parse_mode='Markdown')
            success += 1
            time.sleep(0.05)
        except:
            fail += 1
    bot.reply_to(m, f"✅ **ارسال پیام پایان یافت!**\n\n✅ موفق: {success}\n❌ ناموفق: {fail}")

@bot.message_handler(commands=['ban'])
def ban_user(m):
    if str(m.from_user.id) != ADMIN_ID:
        return
    try:
        user_id = int(m.text.split()[1])
        if str(user_id) == ADMIN_ID:
            bot.reply_to(m, "❌ نمی‌توانید ادمین را بن کنید!")
            return
        banned_users.add(str(user_id))
        save_banned_users()
        try:
            bot.send_message(user_id, "⛔ شما توسط ادمین مسدود شده اید!\n🆔 @bintc")
        except:
            pass
        bot.reply_to(m, f"✅ کاربر {user_id} مسدود شد.")
    except:
        bot.reply_to(m, "❌ دستور: /ban [user_id]")

@bot.message_handler(commands=['unban'])
def unban_user(m):
    if str(m.from_user.id) != ADMIN_ID:
        return
    try:
        user_id = int(m.text.split()[1])
        if str(user_id) in banned_users:
            banned_users.discard(str(user_id))
            save_banned_users()
            bot.reply_to(m, f"✅ کاربر {user_id} از حالت مسدودیت خارج شد.")
        else:
            bot.reply_to(m, f"❌ کاربر {user_id} در لیست مسدود شده‌ها نیست.")
    except:
        bot.reply_to(m, "❌ دستور: /unban [user_id]")

@bot.message_handler(commands=['banned'])
def list_banned(m):
    if str(m.from_user.id) != ADMIN_ID:
        return
    if not banned_users:
        bot.reply_to(m, "📭 هیچ کاربر مسدود شده‌ای وجود ندارد.")
        return
    text = "🚫 **لیست کاربران مسدود شده:**\n\n"
    for uid in banned_users:
        text += f"🆔 `{uid}`\n"
    bot.reply_to(m, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: True)
def unknown(m):
    user_id = m.from_user.id
    if is_banned(user_id):
        bot.reply_to(m, "⛔ شما مسدود شده اید!")
        return
    bot.reply_to(m, 
        f"😅 **اوه! این دکمه رو ندارم!**\n\n{get_random_emoji('error')} لطفا از دکمه‌های منوی اصلی استفاده کنید.\n\n{get_random_emoji('fire')} منو در دسترس است:",
        reply_markup=main_keyboard(),
        parse_mode='Markdown'
    )

if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 10000))
    print(f"🤖 Hegzo VPN روی پورت {PORT} روشن شد!")
    print("✅ سرویس اقتصادی: 25-50-100 گیگ با سرعت 4 مگابیت")
    print("✅ سرویس گیمینگ: 20-30-50-100 گیگ")
    print("✅ سرویس خانواده: 1 تا 4 کاربر + نامحدود 10 روزه")
    print("🎬 انیمیشن‌ها و افکت‌های ویژه فعال شدند!")
    
    bot.delete_webhook()
    time.sleep(2)
    
    from threading import Thread
    Thread(target=lambda: app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)).start()
    
    bot.infinity_polling()
