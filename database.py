import sqlite3
import json
from datetime import datetime

class Database:
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Initialize database tables."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Users table
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                joined_at TEXT,
                is_premium INTEGER DEFAULT 0,
                premium_expiry TEXT,
                total_downloads INTEGER DEFAULT 0,
                daily_downloads INTEGER DEFAULT 0,
                last_download_date TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_user(self, user_id, username=""):
        """Add new user to database."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute(
            "INSERT OR IGNORE INTO users (user_id, username, joined_at) VALUES (?, ?, ?)",
            (user_id, username, datetime.now().isoformat())
        )
        
        conn.commit()
        conn.close()
    
    def get_user(self, user_id):
        """Get user data."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        
        conn.close()
        
        if row:
            return {
                'user_id': row[0],
                'username': row[1],
                'joined_at': row[2],
                'is_premium': bool(row[3]),
                'premium_expiry': row[4],
                'total_downloads': row[5],
                'daily_downloads': row[6],
                'last_download_date': row[7]
            }
        return None
    
    def increment_downloads(self, user_id):
        """Increment download count for user."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        today = datetime.now().date().isoformat()
        
        c.execute(
            "UPDATE users SET total_downloads = total_downloads + 1, daily_downloads = daily_downloads + 1, last_download_date = ? WHERE user_id = ?",
            (today, user_id)
        )
        
        conn.commit()
        conn.close()
    
    def get_daily_downloads(self, user_id):
        """Get daily download count for user."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("SELECT daily_downloads FROM users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        
        conn.close()
        
        return row[0] if row else 0
    
    def reset_daily_downloads(self, user_id):
        """Reset daily downloads for user."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute(
            "UPDATE users SET daily_downloads = 0 WHERE user_id = ?",
            (user_id,)
        )
        
        conn.commit()
        conn.close()
    
    def get_total_users(self):
        """Get total number of users."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("SELECT COUNT(*) FROM users")
        count = c.fetchone()[0]
        
        conn.close()
        
        return count
    
    def get_total_downloads(self):
        """Get total number of downloads."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("SELECT SUM(total_downloads) FROM users")
        total = c.fetchone()[0] or 0
        
        conn.close()
        
        return total
