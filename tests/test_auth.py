import base64
import sqlite3
from fastapi.testclient import TestClient
import app  # This assumes your main app is in app.py

client = TestClient(app)
DB_PATH = "predictions.db"

def setup_module(module):
    """Ensure test user exists before running any tests."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL
            )
        """)
        conn.execute("""
            INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)
        """, ("admin", "admin"))


def auth_header(username, password):
    """
    Helper to generate the Authorization header for Basic Auth.
    """
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def test_health_open():
    """
    /health endpoint should work without auth
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_predict_unauthenticated():
    """
    /predict should work without auth (username saved as null)
    """
    response = client.post("/predict", files={"file": ("test.jpg", b"fakeimage", "image/jpeg")})
    assert response.status_code == 200
    assert "prediction_uid" in response.json()


def test_predict_authenticated():
    """
    /predict should also work with auth (username stored)
    """
    response = client.post("/predict",
                           files={"file": ("test.jpg", b"fakeimage", "image/jpeg")},
                           headers=auth_header("admin", "admin"))
    assert response.status_code == 200
    assert "prediction_uid" in response.json()


def test_protected_endpoint_no_auth():
    """
    /labels should be protected and return 401 without auth
    """
    response = client.get("/labels")
    assert response.status_code == 401


def test_protected_endpoint_with_auth():
    """
    /labels should work with proper credentials
    """
    response = client.get("/labels", headers=auth_header("admin", "admin"))
    assert response.status_code == 200
    assert "labels" in response.json()
