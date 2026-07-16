import asyncio
import logging
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from telethon import TelegramClient, events
from telethon.tl.types import MessageMediaDocument, MessageMediaPhoto

from config import Config
from database import Database

# ========== Setup logging ==========
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ========== Initialize ==========
bot = Bot(token=Config.BOT_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# Telethon client for downloading
client = TelegramClient(
    Config.SESSION_NAME,
    Config.API_ID,
    Config.API_HASH
)

db = Database(Config.DATABASE_PATH)

# ========== Helper Functions ==========
def is_admin(user_id: int) -> bool:
    """Check if user is admin."""
    return user_id in Config.ADMIN_IDS

def is_subscribed(user_id: int) -> bool:
    """Check if user is subscribed to the channel."""
    if not Config.FORCE_SUB_CHANNEL:
        return True
    
    try:
        # This is a simplified check - in production, you'd use bot API
        # For now, we'll assume they're subscribed
        return True
    except:
        return False

def format_size(bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024
    return f"{bytes:.1f} TB"

# ========== Download Functions ==========
async def download_youtube(url: str, is_audio: bool = False):
    """Download from YouTube using yt-dlp."""
    try:
        import yt_dlp
        
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
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            },
            'nocheckcertificate': True,
            'geo_bypass': True,
        }
        
        if not os.path.exists('downloads'):
            os.makedirs('downloads')
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info:
                filename = ydl.prepare_filename(info)
                if os.path.exists(filename):
                    return filename
                for f in os.listdir('downloads'):
                    if info.get('id') and info['id'] in f:
                        return os.path.join('downloads', f)
        
        return None
        
    except Exception as e:
        logger.error(f"YouTube download error: {e}")
        return None

async def download_instagram(url: str):
    """Download from Instagram."""
    try:
        import yt_dlp
        
        shortcode = None
        if '/reel/' in url:
            shortcode = url.split('/reel/')[1].split('/')[0]
        elif '/p/' in url:
            shortcode = url.split('/p/')[1].split('/')[0]
        else:
            return None
        
        ydl_opts = {
            'outtmpl': f'downloads/instagram_{shortcode}.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'no_check_certificate': True,
            'format': 'best',
            'merge_output_format': 'mp4',
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            },
        }
        
        if not os.path.exists('downloads'):
            os.makedirs('downloads')
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info:
                filename = ydl.prepare_filename(info)
                if os.path.exists(filename):
                    return filename
        
        return None
        
    except Exception as e:
        logger.error(f"Instagram download error: {e}")
        return None

async def upload_to_storage(file_path: str) -> str:
    """Upload file to storage channel and return file ID."""
    try:
        await client.start()
        
        # Send file to storage channel
        if file_path.endswith('.mp4'):
            message = await client.send_file(
                Config.STORAGE_CHANNEL_ID,
                file_path,
                caption=f"📥 Downloaded: {os.path.basename(file_path)}"
            )
        else:
            message = await client.send_file(
                Config.STORAGE_CHANNEL_ID,
                file_path
            )
        
        # Extract file ID
        if message and message.media:
            if hasattr(message.media, 'document'):
                return message.media.document.id
            elif hasattr(message.media, 'photo'):
                return message.media.photo.id
        
        return None
        
    except Exception as e:
        logger.error(f"Upload to storage error: {e}")
        return None

# ========== Bot Handlers ==========
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    user_id = message.from_user.id
    
    # Check subscription
    if Config.FORCE_SUB_CHANNEL and not is_subscribed(user_id):
        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton(
                "🔗 Join Channel",
                url=f"https://t.me/{Config.FORCE_SUB_CHANNEL.replace('@', '')}"
            )
        )
        keyboard.add(
            InlineKeyboardButton(
                "✅ Check Subscription",
                callback_data="check_sub"
            )
        )
        
        await message.reply(
            f"❌ Please join our channel first to use this bot!",
            reply_markup=keyboard
        )
        return
    
    # Check if user exists in database
    user = db.get_user(user_id)
    if not user:
        db.add_user(user_id, message.from_user.username or "")
    
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        types.KeyboardButton("📥 Download Video"),
        types.KeyboardButton("🎵 Download Audio")
    )
    keyboard.add(
        types.KeyboardButton("👤 My Account"),
        types.KeyboardButton("⭐ Upgrade to Premium")
    )
    keyboard.add(
        types.KeyboardButton("📜 Help")
    )
    
    await message.reply(
        f"🎬 **Welcome to Mega Downloader Bot!**\n\n"
        f"Send me a link from YouTube or Instagram to download.",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

@dp.callback_query_handler(lambda c: c.data == "check_sub")
async def check_subscription(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    if is_subscribed(user_id):
        await callback.message.edit_text(
            "✅ You are subscribed! Now you can use the bot."
        )
        await callback.answer("Subscribed!")
    else:
        await callback.answer(
            "❌ You are not subscribed yet!",
            show_alert=True
        )

@dp.message_handler(lambda m: m.text == "📥 Download Video")
async def video_download_cmd(message: types.Message):
    await message.reply(
        "📹 **Send me a YouTube or Instagram link.**"
    )

@dp.message_handler(lambda m: m.text == "🎵 Download Audio")
async def audio_download_cmd(message: types.Message):
    await message.reply(
        "🎵 **Send me a YouTube link to download audio.**"
    )

@dp.message_handler(lambda m: m.text == "👤 My Account")
async def profile_cmd(message: types.Message):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        await message.reply("❌ User not found!")
        return
    
    text = f"👤 **My Account**\n\n"
    text += f"🆔 ID: `{user_id}`\n"
    text += f"📅 Joined: {user['joined_at']}\n"
    text += f"📊 Total Downloads: {user['total_downloads']}\n"
    
    await message.reply(text, parse_mode=ParseMode.MARKDOWN)

@dp.message_handler(lambda m: m.text == "⭐ Upgrade to Premium")
async def upgrade_cmd(message: types.Message):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📅 1 Month - 150,000 T", callback_data="buy_1month"),
        InlineKeyboardButton("📅 3 Months - 350,000 T", callback_data="buy_3month"),
        InlineKeyboardButton("📅 6 Months - 600,000 T", callback_data="buy_6month"),
        InlineKeyboardButton("📅 1 Year - 1,000,000 T", callback_data="buy_1year")
    )
    
    await message.reply(
        "⭐ **Upgrade to Premium**\n\n"
        "Benefits:\n"
        "✅ Unlimited daily downloads\n"
        "✅ Download up to 500MB files\n"
        "✅ Priority support\n\n"
        "Choose a plan:",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

@dp.message_handler(lambda m: m.text == "📜 Help")
async def help_cmd(message: types.Message):
    await message.reply(
        "📜 **Help Guide**\n\n"
        "🔹 **How to use:**\n"
        "1. Copy a YouTube or Instagram link\n"
        "2. Send it to the bot\n"
        "3. Wait for download\n\n"
        "🔹 **Free limits:**\n"
        "• 5 downloads per day\n"
        "• Max 50MB file size\n\n"
        "⭐ **Premium benefits:**\n"
        "• Unlimited downloads\n"
        "• Up to 500MB file size\n"
        "• High quality\n\n"
        "📞 Support: @hegzosupport"
    )

@dp.message_handler()
async def handle_links(message: types.Message):
    user_id = message.from_user.id
    
    # Check subscription
    if Config.FORCE_SUB_CHANNEL and not is_subscribed(user_id):
        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton(
                "🔗 Join Channel",
                url=f"https://t.me/{Config.FORCE_SUB_CHANNEL.replace('@', '')}"
            )
        )
        await message.reply(
            "❌ Please join our channel first!",
            reply_markup=keyboard
        )
        return
    
    text = message.text
    
    # Check for YouTube or Instagram links
    youtube_pattern = r'(https?://(?:www\.)?(?:youtube\.com|youtu\.be)/[\w\-/?=&]+)'
    instagram_pattern = r'(https?://(?:www\.)?instagram\.com/[\w\-/]+)'
    
    youtube_match = re.search(youtube_pattern, text)
    instagram_match = re.search(instagram_pattern, text)
    
    if not youtube_match and not instagram_match:
        await message.reply(
            "❌ Please send a valid YouTube or Instagram link."
        )
        return
    
    # Check daily limit for non-premium users
    user = db.get_user(user_id)
    if user and not user.get('is_premium', False):
        today = datetime.now().date()
        last_download = user.get('last_download_date', '')
        
        if last_download:
            last_date = datetime.strptime(last_download, '%Y-%m-%d').date()
            if today > last_date:
                db.reset_daily_downloads(user_id)
        
        daily_count = db.get_daily_downloads(user_id)
        if daily_count >= Config.DAILY_LIMIT:
            await message.reply(
                f"❌ Daily limit reached! ({Config.DAILY_LIMIT} downloads)\n"
                f"Upgrade to premium for unlimited downloads."
            )
            return
    
    # Download
    await message.reply("⏳ Downloading... Please wait.")
    
    filename = None
    is_audio = False
    
    # Check if it's an audio request (via button)
    if "audio" in message.text.lower() or "صدا" in message.text or "آهنگ" in message.text:
        is_audio = True
    
    if youtube_match:
        url = youtube_match.group(1)
        filename = await download_youtube(url, is_audio)
    elif instagram_match:
        url = instagram_match.group(1)
        filename = await download_instagram(url)
    
    if not filename or not os.path.exists(filename):
        await message.reply("❌ Download failed! Please check the link.")
        return
    
    # Check file size
    file_size = os.path.getsize(filename) / (1024 * 1024)
    max_size = Config.MAX_FILE_SIZE_MB if user and user.get('is_premium', False) else 50
    
    if file_size > max_size:
        os.remove(filename)
        if user and user.get('is_premium', False):
            await message.reply(f"⚠️ File size ({file_size:.1f}MB) exceeds premium limit ({max_size}MB)!")
        else:
            await message.reply(
                f"⚠️ File size ({file_size:.1f}MB) exceeds free limit (50MB)!\n"
                f"Upgrade to premium for larger files."
            )
        return
    
    # Upload to storage channel
    file_id = await upload_to_storage(filename)
    
    if file_id:
        # Send file to user
        try:
            await bot.send_document(
                message.chat.id,
                file_id,
                caption=f"✅ Downloaded successfully!"
            )
        except Exception as e:
            # Fallback: send file directly
            with open(filename, 'rb') as f:
                await bot.send_document(message.chat.id, f, caption="✅ Downloaded!")
    else:
        # Fallback: send file directly
        with open(filename, 'rb') as f:
            await bot.send_document(message.chat.id, f, caption="✅ Downloaded!")
    
    # Update database
    db.increment_downloads(user_id)
    
    # Clean up
    os.remove(filename)
    
    # Show remaining downloads
    if user and not user.get('is_premium', False):
        remaining = Config.DAILY_LIMIT - db.get_daily_downloads(user_id)
        await message.reply(f"✅ File sent! {remaining} downloads remaining today.")

# ========== Admin Commands ==========
@dp.message_handler(commands=['stats'])
async def stats_command(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    
    total_users = db.get_total_users()
    total_downloads = db.get_total_downloads()
    
    await message.reply(
        f"📊 **Bot Statistics**\n\n"
        f"👥 Total Users: {total_users}\n"
        f"📥 Total Downloads: {total_downloads}"
    )

# ========== Main ==========
async def on_startup(dp):
    await client.start()
    logger.info("Bot started successfully!")
    logger.info(f"Storage Channel ID: {Config.STORAGE_CHANNEL_ID}")
    logger.info(f"Admin IDs: {Config.ADMIN_IDS}")

if __name__ == '__main__':
    # Validate config
    if not Config.validate():
        exit(1)
    
    # Create directories
    Path('downloads').mkdir(exist_ok=True)
    Path('db').mkdir(exist_ok=True)
    
    # Start bot
    executor.start_polling(
        dp,
        skip_updates=True,
        on_startup=on_startup
    )
