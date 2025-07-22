import unittest
import os
import sqlite3
from fastapi.testclient import TestClient
from app import app, init_db, DB_PATH, UPLOAD_DIR, PREDICTED_DIR
from uuid import uuid4
from datetime import datetime

class TestDeletePredictionEndpoint(unittest.TestCase):

    def setUp(self):
        # Reset database
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        init_db()
        self.client = TestClient(app)

        # Create fake prediction paths
        self.uid = str(uuid4())
        self.original_path = os.path.join(UPLOAD_DIR, self.uid + ".jpg")
        self.predicted_path = os.path.join(PREDICTED_DIR, self.uid + ".jpg")

        # Create dummy image files
        with open(self.original_path, "w") as f:
            f.write("fake original image")
        with open(self.predicted_path, "w") as f:
            f.write("fake predicted image")

        # Insert dummy user and prediction
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (username, password)
                VALUES (?, ?)
            """, ("testuser", "testpass"))
            user_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO prediction_sessions (uid, timestamp, original_image, predicted_image, user_id)
                VALUES (?, ?, ?, ?, ?)
            """, (self.uid, datetime.utcnow().isoformat(), self.original_path, self.predicted_path, user_id))

            cursor.execute("""
                INSERT INTO detection_objects (prediction_uid, label, score, box)
                VALUES (?, ?, ?, ?)
            """, (self.uid, "car", 0.9, "[0,0,100,100]"))
            conn.commit()

        # Base64 for testuser:testpass
        self.auth_headers = {"Authorization": "Basic dGVzdHVzZXI6dGVzdHBhc3M="}

    def tearDown(self):
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        if os.path.exists(self.original_path):
            os.remove(self.original_path)
        if os.path.exists(self.predicted_path):
            os.remove(self.predicted_path)

    def test_delete_prediction_success(self):
        # Confirm prediction exists
        response = self.client.get(f"/prediction/{self.uid}", headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)

        # Perform delete
        response = self.client.delete(f"/prediction/{self.uid}", headers=self.auth_headers)
        self.assertEqual(response.status_code, 204)

        # Confirm DB entry removed
        with sqlite3.connect(DB_PATH) as conn:
            prediction = conn.execute("SELECT * FROM prediction_sessions WHERE uid = ?", (self.uid,)).fetchone()
            objects = conn.execute("SELECT * FROM detection_objects WHERE prediction_uid = ?", (self.uid,)).fetchall()
            self.assertIsNone(prediction)
            self.assertEqual(len(objects), 0)

        # Confirm files deleted
        self.assertFalse(os.path.exists(self.original_path))
        self.assertFalse(os.path.exists(self.predicted_path))

    def test_delete_prediction_not_found(self):
        fake_uid = str(uuid4())
        response = self.client.delete(f"/prediction/{fake_uid}", headers=self.auth_headers)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Prediction not found")
