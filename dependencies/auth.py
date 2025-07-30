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

import os
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from typing import Optional
from database.connections import Base, engine, get_db
from models.Users_model import Users
from sqlalchemy.orm import Session


# Define the path to the SQLite database file
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "predictions.db")

# Set up HTTP Basic Auth (optional – will not auto-reject)
security = HTTPBasic(auto_error=False)


def initialize_users_table():
    """
    Create the 'users' table in the database if it doesn't already exist.
    """
    Users.__table__.create(bind=engine, checkfirst=True)


def fetch_user_by_name(db: Session, username: str):
    """
    Retrieve user ID and password by username.
    Returns a tuple (id, password) or None.
    """
    result = db.query(Users.id, Users.password).filter(Users.username == username).first()
    return result  # (id, password) or None

def insert_new_user(db: Session, username: str, password: str) -> int:
    """
    Insert a new user with the given username and password.
    Returns the new user's ID.
    """
    new_user = Users(username=username, password=password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)  # loads the generated ID
    return new_user.id


def ensure_anonymous_account(db: Session) -> int:
    """
    Ensure the anonymous user exists in the database.
    If not, insert it. Return the anonymous user's ID.
    """
    anonymous = db.query(Users).filter(Users.username == "__anonymous__").first()
    if anonymous:
        return anonymous.id

    new_user = Users(username="__anonymous__", password="__none__")
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user.id


def resolve_user_id(
    request: Request,
    credentials: Optional[HTTPBasicCredentials] = Depends(security),
    db: Session = Depends(get_db),
):
    """
    Authenticate the user and return their user ID.
    - If no credentials: return anonymous user ID.
    - If user exists: validate password.
    - If user does not exist: create a new user.
    """
    # No credentials provided: return anonymous user
    if credentials is None:
        return ensure_anonymous_account(db)

    username = credentials.username
    password = credentials.password

    if not username and not password:
        return ensure_anonymous_account(db)

    # If username is provided but password is missing, reject
    if username and not password:
        raise HTTPException(status_code=401, detail="Password is required.")

    user = fetch_user_by_name(db, username)

    if user:
        # User found – check password
        if user.password == password:
            return user.id
        raise HTTPException(status_code=401, detail="Incorrect password.")
    else:
        # User not found – try to create a new one
        try:
            return insert_new_user(db, username, password)
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to create user.")