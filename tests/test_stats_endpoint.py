import unittest
import sqlite3
import os
from fastapi.testclient import TestClient
from app import app, init_db, DB_PATH
from datetime import datetime, timedelta

class TestStatsEndpoint(unittest.TestCase):

    def setUp(self):
        # Recreate database
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        init_db()
        self.client = TestClient(app)
        self.now = datetime.utcnow()

        # Insert dummy user
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (username, password)
                VALUES (?, ?)
            """, ("testuser", "testpass"))
            self.user_id = cursor.lastrowid

            # One recent session (linked to test user)
            cursor.execute("""
                INSERT INTO prediction_sessions (uid, timestamp, original_image, predicted_image, user_id)
                VALUES (?, ?, ?, ?, ?)
            """, (
                "recent-uid", self.now.isoformat(), "original.jpg", "predicted.jpg", self.user_id
            ))

            # Add detection objects
            objects = [
                ("recent-uid", "person", 0.9, "[0,0,100,100]"),
                ("recent-uid", "car", 0.8, "[0,0,100,100]"),
                ("recent-uid", "person", 0.85, "[0,0,100,100]"),
                ("recent-uid", "dog", 0.95, "[0,0,100,100]"),
                ("recent-uid", "car", 0.75, "[0,0,100,100]")
            ]
            cursor.executemany("""
                INSERT INTO detection_objects (prediction_uid, label, score, box)
                VALUES (?, ?, ?, ?)
            """, objects)

            # One old session outside 7-day range
            cursor.execute("""
                INSERT INTO prediction_sessions (uid, timestamp, original_image, predicted_image, user_id)
                VALUES (?, ?, ?, ?, ?)
            """, (
                "old-uid", (self.now - timedelta(days=10)).isoformat(), "old.jpg", "old_pred.jpg", self.user_id
            ))
            cursor.execute("""
                INSERT INTO detection_objects (prediction_uid, label, score, box)
                VALUES (?, ?, ?, ?)
            """, ("old-uid", "outdated", 0.99, "[0,0,100,100]"))
            conn.commit()

        # Auth header for testuser:testpass
        self.auth_headers = {"Authorization": "Basic dGVzdHVzZXI6dGVzdHBhc3M="}

    def tearDown(self):
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)

    def test_stats_endpoint(self):
        response = self.client.get("/stats", headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Total predictions should only include recent one
        self.assertEqual(data["total_predictions"], 1)

        # Average confidence score
        expected_avg = round((0.9 + 0.8 + 0.85 + 0.95 + 0.75) / 5, 3)
        self.assertAlmostEqual(data["average_confidence_score"], expected_avg)

        # Most common labels
        expected_labels = {
            "person": 2,
            "car": 2,
            "dog": 1
        }
        self.assertEqual(data["most_common_labels"], expected_labels)
