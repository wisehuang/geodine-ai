#!/usr/bin/env python3
"""
Initialize the GeoDine-AI database.
Run this script once to set up the SQLite database.
"""

from src.database import init_db

if __name__ == "__main__":
    print("Initializing GeoDine-AI database...")
    init_db()
    print("Database initialized successfully.")
    print("Database location: geodine.db in the project root directory") 