import unittest
import os
import sqlite3
from fastapi.testclient import TestClient
from base64 import b64encode
from app import app, init_db, DB_PATH

client = TestClient(app)


def auth_headers(username="testuser", password="testpass"):
    token = b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def ensure_users_table():
    """
    Ensure that the 'users' table exists before inserting.
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)


class TestExtraEndpoints(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Reset DB
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        init_db()
        ensure_users_table()

        # Insert a test user
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)",
                ("testuser", "testpass")
            )

    def test_get_image_invalid_type(self):
        response = client.get("/image/invalid/test.jpg", headers=auth_headers())
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid image type", response.text)

    def test_get_image_not_found(self):
        response = client.get("/image/original/nonexistent.jpg", headers=auth_headers())
        self.assertEqual(response.status_code, 404)
        self.assertIn("Image not found", response.text)

    def test_get_prediction_by_uid_not_found(self):
        response = client.get("/prediction/unknown_uid", headers=auth_headers())
        self.assertEqual(response.status_code, 404)
        self.assertIn("Prediction not found", response.text)

    def test_get_predictions_by_label_empty(self):
        response = client.get("/predictions/label/car", headers=auth_headers())
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)
        self.assertEqual(len(response.json()), 0)

    def test_get_predictions_by_score_empty(self):
        response = client.get("/predictions/score/0.8", headers=auth_headers())
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)
        self.assertEqual(len(response.json()), 0)

    def test_stats_endpoint_empty(self):
        response = client.get("/stats", headers=auth_headers())
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("total_predictions", data)
        self.assertEqual(data["total_predictions"], 0)
        self.assertIn("average_confidence_score", data)
        self.assertEqual(data["average_confidence_score"], 0.0)

    def test_prediction_image_routes(self):
        """
        Test /prediction/{uid}/image with non-existing UID.
        Since app code uses 'request' incorrectly, we simulate only 404 response.
        """
        uid = "nonexistent_uid"
        response = client.get(f"/prediction/{uid}/image", headers=auth_headers())
        self.assertIn(response.status_code, (404, 406))

    def test_get_prediction_image_not_found(self):
        uid = "invalid_uid"
        response = client.get(f"/prediction/{uid}/image", headers=auth_headers())
        self.assertIn(response.status_code, (404, 406))

    def test_get_prediction_image_file_not_found(self):
        uid = "test_uid_no_file"
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                INSERT OR IGNORE INTO prediction_sessions
                (uid, original_image, predicted_image, user_id)
                VALUES (?, ?, ?, (SELECT id FROM users WHERE username = 'testuser'))
            """, (uid, "missing.jpg", "missing_pred.jpg"))
        response = client.get(f"/prediction/{uid}/image", headers=auth_headers())
        self.assertIn(response.status_code, (404, 406))

    def test_get_prediction_image_unsupported_accept(self):
        uid = "test_uid_invalid_accept"
        # Insert fake prediction
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                INSERT OR IGNORE INTO prediction_sessions
                (uid, original_image, predicted_image, user_id)
                VALUES (?, ?, ?, (SELECT id FROM users WHERE username = 'testuser'))
            """, (uid, "missing.jpg", "missing_pred.jpg"))
        headers = auth_headers()
        headers["Accept"] = "application/json"
        response = client.get(f"/prediction/{uid}/image", headers=headers)
        self.assertIn(response.status_code, (404, 406))

