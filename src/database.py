import os
import sqlite3
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

# Database path
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "geodine.db")

def init_db():
    """Initialize the database and create tables if they don't exist"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        line_user_id TEXT UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create locations table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        address TEXT,
        location_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    ''')
    
    # Create user preferences table for future use
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_preferences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        preference_key TEXT NOT NULL,
        preference_value TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        UNIQUE(user_id, preference_key)
    )
    ''')
    
    conn.commit()
    conn.close()

def get_or_create_user(line_user_id: str) -> int:
    """Get user ID from database or create if not exists"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if user exists
    cursor.execute("SELECT id FROM users WHERE line_user_id = ?", (line_user_id,))
    user = cursor.fetchone()
    
    if user:
        user_id = user[0]
    else:
        # Create new user
        cursor.execute("INSERT INTO users (line_user_id) VALUES (?)", (line_user_id,))
        user_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    return user_id

def save_user_location(
    line_user_id: str, 
    latitude: float, 
    longitude: float, 
    address: Optional[str] = None,
    location_name: Optional[str] = None
) -> int:
    """Save user location to database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get or create user
    user_id = get_or_create_user(line_user_id)
    
    # Insert location
    cursor.execute(
        """
        INSERT INTO user_locations 
        (user_id, latitude, longitude, address, location_name) 
        VALUES (?, ?, ?, ?, ?)
        """, 
        (user_id, latitude, longitude, address, location_name)
    )
    
    location_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    return location_id

def get_user_locations(line_user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Get user's recent locations"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # This enables column access by name
    cursor = conn.cursor()
    
    # Get user ID
    cursor.execute("SELECT id FROM users WHERE line_user_id = ?", (line_user_id,))
    user = cursor.fetchone()
    
    if not user:
        return []
    
    user_id = user['id']
    
    # Get recent locations
    cursor.execute(
        """
        SELECT id, latitude, longitude, address, location_name, created_at
        FROM user_locations
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (user_id, limit)
    )
    
    locations = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return locations

def save_user_preference(line_user_id: str, key: str, value: str) -> bool:
    """Save user preference to database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Get or create user
        user_id = get_or_create_user(line_user_id)
        
        # Insert or update preference
        cursor.execute(
            """
            INSERT INTO user_preferences (user_id, preference_key, preference_value)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, preference_key) 
            DO UPDATE SET preference_value = ?
            """, 
            (user_id, key, value, value)
        )
        
        conn.commit()
        result = True
    except Exception as e:
        print(f"Error saving user preference: {str(e)}")
        conn.rollback()
        result = False
    finally:
        conn.close()
    
    return result

def get_user_preference(line_user_id: str, key: str) -> Optional[str]:
    """Get user preference from database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get user ID
    cursor.execute("SELECT id FROM users WHERE line_user_id = ?", (line_user_id,))
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        return None
    
    user_id = user[0]
    
    # Get preference
    cursor.execute(
        """
        SELECT preference_value
        FROM user_preferences
        WHERE user_id = ? AND preference_key = ?
        """,
        (user_id, key)
    )
    
    preference = cursor.fetchone()
    
    conn.close()
    
    return preference[0] if preference else None 