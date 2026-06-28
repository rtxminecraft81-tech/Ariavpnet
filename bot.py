import telebot
from telebot import types
import json
import os
import time
from datetime import datetime
from flask import Flask
import threading

app = Flask(__name__)

@app.route('/')
def home():
    return "🏛️ Aria VPN Bot is running!", 200

TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    raise ValueError("🏛️ توکن یافت نشد! لطفاً BOT_TOKEN را در Render تنظیم کنید.")

ADMIN_ID = '6795169616'
CHANNEL_USERNAME = '@AriaVPN_Channel'
CARD_NUMBER = '5022291525516892'
CARD_NAME = 'احمد خزایی'
REFERRAL_AMOUNT = 5000

bot = telebot.TeleBot(TOKEN)
USER_DB = 'users.json'

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

def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🏛️ خرید کانفیگ", "💳 شارژ کیف پول")
    markup.add("📜 کانفیگ‌های من", "👤 حساب من")
    markup.add("🤝 دعوت سلطنتی", "🆘 پشتیبانی")
    markup.add("🏠 صفحه اصلی")
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
    markup.add(types.InlineKeyboardButton("🏛️ بسته‌های شاهنشاهی", callback_data="lev_eco"))
    markup.add(types.InlineKeyboardButton("🗿 بسته‌های آریایی (به زودی)", callback_data="lev_aria"))
    markup.add(types.InlineKeyboardButton("🏠 صفحه اصلی", callback_data="back_main"))
    return markup

def eco_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("⚜️ 25 گیگ - 180,000 تومان", callback_data="b_eco25_180000"))
    markup.add(types.InlineKeyboardButton("⚜️ 50 گیگ - 250,000 تومان", callback_data="b_eco50_250000"))
    markup.add(types.InlineKeyboardButton("⚜️ 100 گیگ - 450,000 تومان", callback_data="b_eco100_450000"))
    markup.add(types.InlineKeyboardButton("⚜️ 200 گیگ - 800,000 تومان", callback_data="b_eco200_800000"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_buy"))
    return markup

@bot.message_handler(commands=['start', 'help'])
def start(message):
    user_id = message.from_user.id
    if is_banned(user_id):
        bot.reply_to(message, "⛔ شما توسط ادمین مسدود شده اید!\n🆔 @Ariavpnetsupport")
        return
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
                bot.send_message(ref, "🎉 یک شاهزاده جدید با لینک شما عضو شد!")
        except:
            pass
    if not is_member(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔗 عضویت در کانال", url="https://t.me/AriaVPN_Channel"))
        markup.add(types.InlineKeyboardButton("✅ تایید عضویت", callback_data="check_membership"))
        bot.reply_to(message, f"🏛️ {name} عزیز!\n\nبرای ورود به پادشاهی اینترنت، ابتدا در کانال رسمی آریا وی‌پی‌ان عضو شوید، سپس دکمه‌ی «تایید عضویت» را بزنید.", reply_markup=markup)
        return
    bot.reply_to(message, f"""🏛️ به پادشاهی اینترنت خوش آمدی {name}!

👑 آریا وی‌پی‌ان، سرویس اختصاصی کانفیگ و VPN با سرعت بالا، امنیت کامل و بدون محدودیت.

✅ اینترنت آزاد و بدون فیلتر
✅ سرعت بالا و پایدار
✅ پشتیبانی ۲۴ ساعته
✅ قیمت مناسب و رقابتی

🇮🇷 به سبک آریایی‌ها وصل شو.

🆔 پشتیبانی: @Ariavpnetsupport""", reply_markup=main_keyboard())

@bot.callback_query_handler(func=lambda call: call.data == "check_membership")
def check_membership(call):
    user_id = call.from_user.id
    if is_member(user_id):
        bot.edit_message_text("✅ عضویت شما تأیید شد! به پادشاهی اینترنت خوش آمدید.", call.message.chat.id, call.message.message_id)
        bot.send_message(user_id, f"""🏛️ به پادشاهی اینترنت خوش آمدی!

👑 آریا وی‌پی‌ان، سرویس اختصاصی کانفیگ و VPN با سرعت بالا، امنیت کامل و بدون محدودیت.

✅ اینترنت آزاد و بدون فیلتر
✅ سرعت بالا و پایدار
✅ پشتیبانی ۲۴ ساعته
✅ قیمت مناسب و رقابتی

🇮🇷 به سبک آریایی‌ها وصل شو.

🆔 پشتیبانی: @Ariavpnetsupport""", reply_markup=main_keyboard())
    else:
        bot.answer_callback_query(call.id, "❌ شما هنوز در کانال عضو نشده‌اید! لطفاً ابتدا عضو شوید.", show_alert=True)

@bot.message_handler(func=lambda m: m.text == "🏠 صفحه اصلی")
def back_home(m):
    bot.reply_to(m, "🏛️ صفحه اصلی آریا وی‌پی‌ان:", reply_markup=main_keyboard())

@bot.message_handler(commands=['buy'])
@bot.message_handler(func=lambda m: m.text == "🏛️ خرید کانفیگ")
def show_buy(m):
    bot.reply_to(m, "🏛️ انتخاب بسته شاهنشاهی:", reply_markup=buy_menu())

@bot.message_handler(commands=['profile'])
@bot.message_handler(func=lambda m: m.text == "👤 حساب من")
def profile(m):
    user_id = m.from_user.id
    data = users.get(str(user_id), {})
    active_count = len(data.get('active_configs', []))
    text = f"👑 **حساب سلطنتی من**\n\n━━━━━━━━━━━━━━━━━━━━━\n🆔 شناسه: `{user_id}`\n👤 نام: {m.from_user.first_name}\n📊 کانفیگ فعال: {active_count}\n👥 زیرمجموعه: {data.get('referrals', 0)}\n💰 اعتبار کیف پول: {data.get('credit', 0):,} تومان\n━━━━━━━━━━━━━━━━━━━━━\n🇮🇷 به سبک آریایی‌ها وصل شو."
    bot.reply_to(m, text, parse_mode='Markdown')

@bot.message_handler(commands=['referral'])
@bot.message_handler(func=lambda m: m.text == "🤝 دعوت سلطنتی")
def invite(m):
    user_id = m.from_user.id
    link = f"https://t.me/{bot.get_me().username}?start={user_id}"
    data = users.get(str(user_id), {})
    text = f"👑 **لینک دعوت سلطنتی شما**\n\n`{link}`\n\n👥 دعوت‌ها: {data.get('referrals', 0)}\n\n💰 هر دعوت = {REFERRAL_AMOUNT:,} تومان اعتبار"
    bot.reply_to(m, text, parse_mode='Markdown')

@bot.message_handler(commands=['support'])
@bot.message_handler(func=lambda m: m.text == "🆘 پشتیبانی")
def support(m):
    bot.reply_to(m, "🏛️ **پشتیبانی سلطنتی آریا وی‌پی‌ان**\n\n@Ariavpnetsupport\n\n۲۴ ساعته پاسخگوی شما هستیم.", parse_mode='Markdown')

@bot.message_handler(commands=['charge'])
@bot.message_handler(func=lambda m: m.text == "💳 شارژ کیف پول")
def charge(m):
    text = f"""👑 **شارژ کیف پول سلطنتی**

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

🆔 پشتیبانی: @Ariavpnetsupport
━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 لطفا مبلغ مورد نظر را وارد کنید (به تومان):"""
    bot.reply_to(m, text, parse_mode='Markdown')
    bot.register_next_step_handler(m, get_amount)

def get_amount(m):
    user_id = m.from_user.id
    try:
        amount = int(m.text)
        if amount < 200000:
            bot.reply_to(m, "❌ حداقل شارژ 200,000 تومان است!")
            return
        users[str(user_id)]['pending_charge'] = amount
        save_users(users)
        bot.reply_to(m, f"✅ درخواست شارژ {amount:,} تومانی ثبت شد!\n\n📸 لطفا رسید واریز را بفرستید.")
    except:
        bot.reply_to(m, "❌ لطفا یک عدد معتبر وارد کنید!")

@bot.message_handler(content_types=['photo'])
def receipt(m):
    user_id = m.from_user.id
    username = m.from_user.username or "بدون نام"
    file_id = m.photo[-1].file_id
    pending = users.get(str(user_id), {}).get('pending_charge', 0)
    if pending > 0:
        admin_text = f"👑 **درخواست شارژ کیف پول**\n👤 @{username}\n🆔 {user_id}\n💸 مبلغ: {pending:,} تومان"
        bot.send_photo(ADMIN_ID, file_id, caption=admin_text, reply_markup=admin_charge_buttons(user_id, pending), parse_mode='Markdown')
        bot.reply_to(m, f"✅ رسید شما دریافت شد!\n🕐 در حال بررسی توسط ادمین...")
        users[str(user_id)]['pending_charge'] = 0
        save_users(users)
    else:
        bot.reply_to(m, "❌ ابتدا از منوی اصلی روی 💳 شارژ کیف پول کلیک کن و مبلغ را وارد کن.")

@bot.message_handler(func=lambda m: m.text == "📜 کانفیگ‌های من")
def my_configs_list(m):
    user_id = m.from_user.id
    cfg_list = users.get(str(user_id), {}).get('active_configs', [])
    if not cfg_list:
        bot.reply_to(m, "📜 **کانفیگ فعالی ندارید!**\n\nبرای خرید کانفیگ از بخش 🏛️ خرید کانفیگ اقدام کنید.", parse_mode='Markdown')
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for i, cfg in enumerate(cfg_list):
        package = cfg.get('package', 'نامشخص')
        date = cfg.get('date', 'نامشخص')[:10]
        markup.add(types.InlineKeyboardButton(f"{i+1}. {package} ({date})", callback_data=f"showcfg_{i}"))
    markup.add(types.InlineKeyboardButton("🏠 صفحه اصلی", callback_data="back_main"))
    
    bot.reply_to(m, "📜 **لیست کانفیگ‌های فعال شما**\n\nلطفا یکی از گزینه‌های زیر را انتخاب کنید:", reply_markup=markup, parse_mode='Markdown')

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
    
    file_name = f"config_{user_id}_{package}.txt"
    with open(file_name, 'w') as f:
        f.write(config)
    
    with open(file_name, 'rb') as f:
        bot.send_document(user_id, f, caption=f"📜 **کانفیگ {package}**\n\n💰 مبلغ: {price:,} تومان\n📅 تاریخ: {date}\n\n🆔 پشتیبانی: @Ariavpnetsupport")
    
    os.remove(file_name)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_configs")
def back_to_configs(call):
    user_id = call.from_user.id
    cfg_list = users.get(str(user_id), {}).get('active_configs', [])
    
    if not cfg_list:
        try:
            bot.edit_message_text("📜 کانفیگ فعالی ندارید!", call.message.chat.id, call.message.message_id, parse_mode='Markdown')
        except:
            bot.send_message(call.message.chat.id, "📜 کانفیگ فعالی ندارید!", parse_mode='Markdown')
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for i, cfg in enumerate(cfg_list):
        package = cfg.get('package', 'نامشخص')
        date = cfg.get('date', 'نامشخص')[:10]
        markup.add(types.InlineKeyboardButton(f"{i+1}. {package} ({date})", callback_data=f"showcfg_{i}"))
    markup.add(types.InlineKeyboardButton("🏠 صفحه اصلی", callback_data="back_main"))
    
    try:
        bot.edit_message_text("📜 **لیست کانفیگ‌های فعال شما**\n\nلطفا یکی از گزینه‌های زیر را انتخاب کنید:", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
    except:
        bot.send_message(call.message.chat.id, "📜 **لیست کانفیگ‌های فعال شما**\n\nلطفا یکی از گزینه‌های زیر را انتخاب کنید:", reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "lev_eco")
def lev_eco(call):
    try:
        bot.edit_message_text("🏛️ **بسته‌های شاهنشاهی آریا وی‌پی‌ان**\n\nلطفا یکی از بسته‌های سلطنتی زیر را انتخاب کنید:", call.message.chat.id, call.message.message_id, reply_markup=eco_menu(), parse_mode='Markdown')
    except:
        bot.send_message(call.message.chat.id, "🏛️ **بسته‌های شاهنشاهی آریا وی‌پی‌ان**\n\nلطفا یکی از بسته‌های سلطنتی زیر را انتخاب کنید:", reply_markup=eco_menu(), parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "lev_aria")
def lev_aria(call):
    bot.answer_callback_query(call.id, "🗿 بسته‌های آریایی به زودی فعال خواهد شد!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "back_buy")
def back_buy(call):
    try:
        bot.edit_message_text("🏛️ انتخاب بسته شاهنشاهی:", call.message.chat.id, call.message.message_id, reply_markup=buy_menu())
    except:
        bot.send_message(call.message.chat.id, "🏛️ انتخاب بسته شاهنشاهی:", reply_markup=buy_menu())

@bot.callback_query_handler(func=lambda call: call.data == "back_main")
def back_main(call):
    try:
        bot.edit_message_text("🏛️ صفحه اصلی آریا وی‌پی‌ان:", call.message.chat.id, call.message.message_id, reply_markup=main_keyboard())
    except:
        bot.send_message(call.message.chat.id, "🏛️ صفحه اصلی آریا وی‌پی‌ان:", reply_markup=main_keyboard())

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
        admin_text = f"👑 **درخواست کانفیگ جدید**\n\n👤 کاربر: @{username}\n🆔 آیدی: {user_id}\n📦 بسته: {package}\n💰 مبلغ: {price:,} تومان"
        bot.send_message(ADMIN_ID, admin_text, reply_markup=admin_buttons(user_id, package, price), parse_mode='Markdown')
        bot.send_message(user_id, f"✅ درخواست شما ثبت شد! منتظر تایید ادمین باشید.")
        bot.answer_callback_query(call.id, "✅ ثبت شد")
        try:
            bot.edit_message_text("✅ درخواست ثبت شد. منتظر تایید ادمین.", call.message.chat.id, call.message.message_id)
        except:
            pass
    else:
        need = price - credit
        bot.send_message(user_id, f"❌ **اعتبار کافی نیست!**\n💰 اعتبار شما: {credit:,} تومان\n💸 نیاز به {need:,} تومان دیگر\n\nبرای افزایش اعتبار از منوی اصلی روی 💳 شارژ کیف پول کلیک کن.", parse_mode='Markdown')
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
    
    bot.send_message(user_id, f"✅ **کانفیگ {package} تایید شد!**\n\n🆔 پشتیبانی: @Ariavpnetsupport", parse_mode='Markdown')
    bot.answer_callback_query(call.id, "✅ تایید شد")
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
    
    bot.send_message(user_id, "❌ **درخواست شما رد شد!**\n\n📱 با پشتیبانی تماس بگیرید: @Ariavpnetsupport", parse_mode='Markdown')
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
    
    file_name = f"config_{user_id}_{package}.txt"
    with open(file_name, 'w') as f:
        f.write(config)
    
    with open(file_name, 'rb') as f:
        bot.send_document(user_id, f, caption=f"🎁 **کانفیگ اختصاصی شما ({package})**\n\n🆔 پشتیبانی: @Ariavpnetsupport")
    
    os.remove(file_name)
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
        bot.send_message(user_id, f"✅ **شارژ {amount:,} تومانی تایید شد!**\n💰 اعتبار جدید: {users[str(user_id)]['credit']:,} تومان", parse_mode='Markdown')
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
        bot.send_message(user_id, "❌ **درخواست شارژ رد شد!**\n\n📱 با پشتیبانی تماس بگیرید: @Ariavpnetsupport", parse_mode='Markdown')
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
    
    count = len(users)
    text = f"👑 **تعداد کاربران آریا وی‌پی‌ان:** {count} نفر\n\n"
    text += "👤 **لیست کاربران:**\n"
    for uid, data in users.items():
        username = data.get('username', '')
        if username:
            username = f"@{username}"
        else:
            username = 'بدون یوزرنیم'
        text += f"• `{uid}` | {username}\n"
    
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
            bot.send_message(int(uid), f"👑 **پیام از دربار آریا وی‌پی‌ان**\n\n{msg}", parse_mode='Markdown')
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
            bot.send_message(user_id, "⛔ شما توسط ادمین مسدود شده اید!\n🆔 @Ariavpnetsupport")
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
    bot.reply_to(m, "❌ لطفا از دکمه‌های منوی اصلی استفاده کنید.", reply_markup=main_keyboard())

if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 10000))
    print(f"🏛️ آریا وی‌پی‌ان روی پورت {PORT} روشن شد!")
    print("✅ بسته‌های شاهنشاهی: 25-50-100-200 گیگ")
    
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
