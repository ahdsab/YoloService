import os
import sqlite3
import unittest
from fastapi.testclient import TestClient
from app import app, DB_PATH, init_db

client = TestClient(app)

class TestPredictionsCount(unittest.TestCase):

    def setUp(self):
        # Remove old DB file and recreate it
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        init_db()

    def tearDown(self):
        # Clean up after each test
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)

    def test_count_when_empty(self):
        """
        Ensure count is 0 when no predictions exist
        """
        response = client.get("/predictions/count")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 0)

    def test_count_with_recent_prediction(self):
        """
        Insert a recent prediction and verify count is 1
        """
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                INSERT INTO prediction_sessions (uid, timestamp, original_image, predicted_image)
                VALUES ('test-uid', datetime('now', '-1 day'), 'original.jpg', 'predicted.jpg')
            """)

        response = client.get("/predictions/count")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)


    def test_count_with_old_prediction(self):
        """
        Insert an old prediction (more than 7 days ago) and verify count is 0
        """
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                INSERT INTO prediction_sessions (uid, timestamp, original_image, predicted_image)
                VALUES ('old-uid', datetime('now', '-10 days'), 'old.jpg', 'old_pred.jpg')
            """)

        response = client.get("/predictions/count")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 0)


