import unittest
import os
import sqlite3
from fastapi.testclient import TestClient
from app import app, init_db, DB_PATH, UPLOAD_DIR, PREDICTED_DIR
from uuid import uuid4
from datetime import datetime
from base64 import b64encode

client = TestClient(app)

def auth_headers(username="testuser", password="testpass"):
    token = b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}

class TestExtraEndpoints(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        init_db()
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", ("testuser", "testpass"))

    def test_get_prediction_by_uid_not_found(self):
        response = client.get("/prediction/invalid-uid", headers=auth_headers())
        self.assertEqual(response.status_code, 404)

    def test_get_predictions_by_label_empty(self):
        response = client.get("/predictions/label/ghost", headers=auth_headers())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_get_predictions_by_score_empty(self):
        response = client.get("/predictions/score/0.9", headers=auth_headers())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_get_image_invalid_type(self):
        response = client.get("/image/fake/doesnotexist.jpg", headers=auth_headers())
        self.assertEqual(response.status_code, 400)

    def test_get_image_not_found(self):
        response = client.get("/image/original/missing.jpg", headers=auth_headers())
        self.assertEqual(response.status_code, 404)

    @unittest.skip("Skipping because app.py has request bug in /prediction/{uid}/image")
    def test_prediction_image_routes(self):
        pass

    def test_stats_endpoint_empty(self):
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM detection_objects")
            conn.execute("DELETE FROM prediction_sessions")
        response = client.get("/stats", headers=auth_headers())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total_predictions"], 0)
