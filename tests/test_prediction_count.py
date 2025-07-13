import unittest
from fastapi.testclient import TestClient
from app import app, init_db, DB_PATH
import sqlite3
from datetime import datetime, timedelta
import os

class TestPredictionCount(unittest.TestCase):

    def setUp(self):
        # Clean the DB
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        init_db()

        self.client = TestClient(app)
        self.now = datetime.utcnow()

    def insert_prediction(self, uid, days_ago):
        timestamp = (self.now - timedelta(days=days_ago)).isoformat()
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                INSERT INTO prediction_sessions (uid, timestamp, original_image, predicted_image)
                VALUES (?, ?, ?, ?)
            """, (uid, timestamp, f"{uid}_original.jpg", f"{uid}_predicted.jpg"))

    def test_prediction_count_format(self):
        """Check response format and status with empty DB"""
        response = self.client.get("/predictions/count")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("count", data)
        self.assertIsInstance(data["count"], int)
        self.assertEqual(data["count"], 0)

    def test_prediction_count_last_7_days(self):
        """Ensure only recent predictions are counted"""
        self.insert_prediction("recent-1", 2)
        self.insert_prediction("old-1", 10)
        response = self.client.get("/predictions/count")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

    def test_prediction_count_multiple_recent(self):
        """Ensure multiple recent predictions are counted"""
        self.insert_prediction("recent-1", 1)
        self.insert_prediction("recent-2", 3)
        self.insert_prediction("recent-3", 6)
        response = self.client.get("/predictions/count")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 3)

    def test_prediction_count_all_old(self):
        """Ensure old predictions are not counted"""
        self.insert_prediction("old-1", 8)
        self.insert_prediction("old-2", 15)
        response = self.client.get("/predictions/count")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 0)

    def test_prediction_exactly_7_days_old(self):
        """Prediction exactly 7 days ago should be included"""
        self.insert_prediction("exact-7", 7)
        response = self.client.get("/predictions/count")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
