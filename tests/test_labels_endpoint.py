import unittest
import sqlite3
import os
from fastapi.testclient import TestClient
from app import app, init_db, DB_PATH
from datetime import datetime, timedelta

class TestLabelsEndpoint(unittest.TestCase):

    def setUp(self):
        # Reset DB
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

            # Insert one recent prediction session
            cursor.execute("""
                INSERT INTO prediction_sessions (uid, timestamp, original_image, predicted_image, user_id)
                VALUES (?, ?, ?, ?, ?)
            """, (
                "test-uid",
                self.now.isoformat(),
                "original.jpg",
                "predicted.jpg",
                self.user_id
            ))

            # Insert multiple objects with labels
            labels = ["person", "car", "person", "truck"]
            for label in labels:
                cursor.execute("""
                    INSERT INTO detection_objects (prediction_uid, label, score, box)
                    VALUES (?, ?, ?, ?)
                """, ("test-uid", label, 0.9, "[0,0,100,100]"))

            # Insert an old prediction with label that should NOT appear
            old_uid = "old-uid"
            cursor.execute("""
                INSERT INTO prediction_sessions (uid, timestamp, original_image, predicted_image, user_id)
                VALUES (?, ?, ?, ?, ?)
            """, (
                old_uid,
                (self.now - timedelta(days=10)).isoformat(),
                "old.jpg",
                "old_pred.jpg",
                self.user_id
            ))

            cursor.execute("""
                INSERT INTO detection_objects (prediction_uid, label, score, box)
                VALUES (?, ?, ?, ?)
            """, (old_uid, "outdated_label", 0.95, "[10,10,20,20]"))

        # Auth headers for testuser:testpass
        self.auth_headers = {"Authorization": "Basic dGVzdHVzZXI6dGVzdHBhc3M="}

    def tearDown(self):
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)

    def test_labels_endpoint(self):
        response = self.client.get("/labels", headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("labels", data)
        self.assertIsInstance(data["labels"], list)

        # Check expected labels
        expected = set(["person", "car", "truck"])
        actual = set(data["labels"])
        self.assertEqual(expected, actual)

        # Make sure outdated label is not included
        self.assertNotIn("outdated_label", actual)
