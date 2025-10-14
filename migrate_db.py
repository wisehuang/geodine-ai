"""
Database migration script for multi-bot support
Run this script to migrate your existing database to support multiple bots
"""
import sqlite3
import os
from pathlib import Path

DB_PATH = os.path.join(os.path.dirname(__file__), "geodine.db")


def migrate_database():
    """Migrate database to support multiple bots"""

    if not Path(DB_PATH).exists():
        print(f"Database file not found at {DB_PATH}")
        print("No migration needed - init_db() will create the new schema.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Starting database migration...")

    try:
        # Check if bots table already exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bots'")
        if cursor.fetchone():
            print("✓ Database already migrated (bots table exists)")
            conn.close()
            return

        # Backup the database
        backup_path = DB_PATH + ".backup"
        print(f"Creating backup at {backup_path}...")
        import shutil
        shutil.copy2(DB_PATH, backup_path)
        print("✓ Backup created")

        # Create bots table
        print("Creating bots table...")
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS bots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        print("✓ Bots table created")

        # Insert default bot for existing users
        print("Creating default 'geodine-ai' bot...")
        cursor.execute("INSERT INTO bots (bot_id, name) VALUES (?, ?)", ("geodine-ai", "GeoDine-AI"))
        default_bot_id = cursor.lastrowid
        print(f"✓ Default bot created with ID: {default_bot_id}")

        # Check if users table needs migration
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'bot_id' not in columns:
            print("Migrating users table...")

            # Create new users table
            cursor.execute('''
            CREATE TABLE users_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_id INTEGER NOT NULL,
                line_user_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (bot_id) REFERENCES bots(id),
                UNIQUE(bot_id, line_user_id)
            )
            ''')

            # Copy existing users to new table with default bot_id
            cursor.execute(f'''
            INSERT INTO users_new (id, bot_id, line_user_id, created_at)
            SELECT id, {default_bot_id}, line_user_id, created_at FROM users
            ''')

            # Drop old table and rename new one
            cursor.execute('DROP TABLE users')
            cursor.execute('ALTER TABLE users_new RENAME TO users')
            print("✓ Users table migrated")
        else:
            print("✓ Users table already has bot_id column")

        # Commit changes
        conn.commit()
        print("\n✅ Migration completed successfully!")
        print(f"Backup saved at: {backup_path}")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    print("=" * 50)
    print("Database Migration for Multi-Bot Support")
    print("=" * 50)
    print()

    migrate_database()

    print()
    print("Next steps:")
    print("1. Review your bot configurations in the 'bots' directory")
    print("2. Update your .env file with new bot credentials if needed")
    print("3. Restart your server to load the new configuration")
    print()
