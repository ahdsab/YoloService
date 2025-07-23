# dependencies/auth.py
"""
Basic / optional auth helpers.

Key rules:
- Use HTTP Basic. Credentials may be missing.
- If no credentials -> use a single automatic user (created once).
- If username is given but password missing -> 401.
- If user exists -> check password.
- If user missing -> create it.
- Protected endpoints: depend on require_authenticated_user_id().
- Endpoints where auth is optional (/predict) can depend on get_current_or_auto_user_id().
"""

import sqlite3
import os
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from typing import Optional

# Define the path to the SQLite database file
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "predictions.db")

# Set up HTTP Basic Auth (optional – will not auto-reject)
security = HTTPBasic(auto_error=False)


def initialize_users_table():
    """
    Create the 'users' table in the database if it doesn't already exist.
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            );
        """)


def fetch_user_by_name(cursor, username):
    """
    Retrieve user ID and password from the database by username.
    """
    cursor.execute("SELECT id, password FROM users WHERE username = ?", (username,))
    return cursor.fetchone()


def insert_new_user(cursor, username, password):
    """
    Insert a new user with the given username and password into the database.
    """
    cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
    return cursor.lastrowid


def ensure_anonymous_account() -> int:
    """
    Ensure the anonymous user exists in the database.
    If not, insert it. Return the anonymous user's ID.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO users (username, password)
            VALUES ("__anonymous__", "__none__");
        """)
        conn.commit()
        cursor.execute("SELECT id FROM users WHERE username = '__anonymous__'")
        return cursor.fetchone()[0]


def resolve_user_id(
    request: Request,
    credentials: Optional[HTTPBasicCredentials] = Depends(security),
):
    """
    Authenticate the user and return their user ID.
    - If no credentials: return anonymous user ID.
    - If user exists: validate password.
    - If user does not exist: create a new user.
    """
    # Make sure the users table exists
    initialize_users_table()

    # No credentials provided: return anonymous user
    if credentials is None:
        return ensure_anonymous_account()

    username = credentials.username
    password = credentials.password

    if not username and not password:
        return ensure_anonymous_account()

    # If username is provided but password is missing, reject
    if username and not password:
        raise HTTPException(status_code=401, detail="Password is required.")

    # Connect to DB to look up or create user
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        user = fetch_user_by_name(cursor, username)

        if user:
            # User found – check password
            stored_password = user[1]
            if stored_password == password:
                return user[0]
            raise HTTPException(status_code=401, detail="Incorrect password.")
        else:
            # User not found – try to create a new one
            try:
                user_id = insert_new_user(cursor, username, password)
                conn.commit()
                return user_id
            except sqlite3.IntegrityError:
                raise HTTPException(status_code=500, detail="failed to create user.")
