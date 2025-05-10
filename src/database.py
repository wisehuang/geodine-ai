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
    
    # Create locations table - updated with unique constraint on user_id
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        address TEXT,
        location_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
    """Save or update user location in database (keep only one record per user)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get or create user
    user_id = get_or_create_user(line_user_id)
    
    try:
        # Try to update existing record first
        cursor.execute(
            """
            UPDATE user_locations 
            SET latitude = ?, longitude = ?, address = ?, location_name = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """, 
            (latitude, longitude, address, location_name, user_id)
        )
        
        # If no record was updated, insert a new one
        if cursor.rowcount == 0:
            cursor.execute(
                """
                INSERT INTO user_locations 
                (user_id, latitude, longitude, address, location_name) 
                VALUES (?, ?, ?, ?, ?)
                """, 
                (user_id, latitude, longitude, address, location_name)
            )
        
        location_id = cursor.lastrowid or cursor.execute("SELECT id FROM user_locations WHERE user_id = ?", (user_id,)).fetchone()[0]
        
        conn.commit()
    except Exception as e:
        print(f"Error saving user location: {str(e)}")
        conn.rollback()
        location_id = None
    finally:
        conn.close()
    
    return location_id

def get_user_location(line_user_id: str) -> Optional[Dict[str, Any]]:
    """Get user's current location (single record)"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Join users and user_locations tables to get location by line_user_id
    cursor.execute(
        """
        SELECT ul.id, ul.latitude, ul.longitude, ul.address, ul.location_name, ul.updated_at
        FROM user_locations ul
        JOIN users u ON ul.user_id = u.id
        WHERE u.line_user_id = ?
        """,
        (line_user_id,)
    )
    
    location = cursor.fetchone()
    conn.close()
    
    return dict(location) if location else None

def get_user_location_for_search(line_user_id: str) -> Optional[Dict[str, float]]:
    """
    Get user's location in the format needed by Google Maps API
    Returns {'lat': latitude, 'lng': longitude} or None if not found
    """
    location = get_user_location(line_user_id)
    
    if location and 'latitude' in location and 'longitude' in location:
        return {
            'lat': location['latitude'],
            'lng': location['longitude']
        }
    
    return None

def get_user_locations(line_user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Get user's location record (kept for compatibility)
    Now only returns the single location record as a list with one item
    """
    location = get_user_location(line_user_id)
    return [location] if location else []

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