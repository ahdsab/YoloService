import base64
import sqlite3
import secrets
from typing import Optional
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.security.utils import get_authorization_scheme_param

DB_PATH = "predictions.db"
security = HTTPBasic()

# חובה להזין שם משתמש וסיסמה
def authenticate_user(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    username = credentials.username
    password = credentials.password

    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT password FROM users WHERE username = ?", (username,)).fetchone()

    if row is None or not secrets.compare_digest(row[0], password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    return username

# אופציונלי (ל־POST /predict)
def get_optional_credentials(authorization: Optional[str] = Header(None)) -> Optional[HTTPBasicCredentials]:
    if authorization:
        scheme, credentials = get_authorization_scheme_param(authorization)
        if scheme.lower() == "basic":
            decoded = base64.b64decode(credentials).decode()
            username, password = decoded.split(":", 1)
            return HTTPBasicCredentials(username=username, password=password)
    return None

def get_user_id_or_none(credentials: Optional[HTTPBasicCredentials] = Depends(get_optional_credentials)) -> Optional[int]:
    if not credentials:
        return None
    username, password = credentials.username, credentials.password
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT id, password FROM users WHERE username = ?", (username,)).fetchone()
        if row and secrets.compare_digest(row[1], password):
            return row[0]
    raise HTTPException(status_code=401, detail="Invalid credentials", headers={"WWW-Authenticate": "Basic"})
