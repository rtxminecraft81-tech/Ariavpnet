"""Configuration module for the Telegram automation system."""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration class containing all environment variables."""
    
    # Telegram API credentials
    API_ID = int(os.getenv('API_ID', 0))
    API_HASH = os.getenv('API_HASH', '')
    
    # Bot token
    BOT_TOKEN = os.getenv('BOT_TOKEN', '')
    
    # Storage channel ID
    STORAGE_CHANNEL_ID = int(os.getenv('STORAGE_CHANNEL_ID', 0))
    
    # Session configuration
    SESSION_NAME = os.getenv('SESSION_NAME', 'userbot_session')
    
    # Database configuration
    DATABASE_PATH = os.getenv('DATABASE_PATH', './db/videos.db')
    
    # Logging configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # Admin configuration
    ADMIN_IDS = [
        int(admin_id.strip()) 
        for admin_id in os.getenv('ADMIN_ID', '0').split(',') 
        if admin_id.strip().isdigit()
    ]
    
    # Force subscribe channel
    FORCE_SUB_CHANNEL = os.getenv('FORCE_SUB_CHANNEL', '')
    
    # Download settings
    MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', 500))
    DAILY_LIMIT = int(os.getenv('DAILY_LIMIT', 5))
    
    @classmethod
    def validate(cls) -> bool:
        """Validate that all required configuration values are set."""
        required_fields = [
            ('API_ID', cls.API_ID),
            ('API_HASH', cls.API_HASH),
            ('BOT_TOKEN', cls.BOT_TOKEN),
            ('STORAGE_CHANNEL_ID', cls.STORAGE_CHANNEL_ID),
        ]
        
        missing_fields = []
        for field_name, field_value in required_fields:
            if not field_value or (isinstance(field_value, int) and field_value == 0):
                missing_fields.append(field_name)
        
        if missing_fields:
            print(f"❌ Missing required configuration fields: {', '.join(missing_fields)}")
            return False
        
        print("✅ All configurations loaded successfully!")
        print(f"✅ Storage Channel ID: {cls.STORAGE_CHANNEL_ID}")
        print(f"✅ Admin IDs: {cls.ADMIN_IDS}")
        print(f"✅ Force Subscribe Channel: {cls.FORCE_SUB_CHANNEL}")
        return True
