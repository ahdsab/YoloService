import unittest
import os
import sqlite3
from fastapi.testclient import TestClient
from app import app, init_db, DB_PATH, UPLOAD_DIR, PREDICTED_DIR
from uuid import uuid4
from datetime import datetime

class TestDeletePredictionEndpoint(unittest.TestCase):

    def setUp(self):
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        init_db()
        self.client = TestClient(app)

        self.uid = str(uuid4())
        self.original_path = os.path.join(UPLOAD_DIR, self.uid + ".jpg")
        self.predicted_path = os.path.join(PREDICTED_DIR, self.uid + ".jpg")

        os.makedirs(UPLOAD_DIR, exist_ok=True)
        os.makedirs(PREDICTED_DIR, exist_ok=True)

        with open(self.original_path, "w") as f:
            f.write("fake original image")
        with open(self.predicted_path, "w") as f:
            f.write("fake predicted image")

        # Insert into DB
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                INSERT INTO prediction_sessions (uid, timestamp, original_image, predicted_image)
                VALUES (?, ?, ?, ?)
            """, (self.uid, datetime.utcnow().isoformat(), self.original_path, self.predicted_path))

            conn.execute("""
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
        response = self.client.get(f"/prediction/{self.uid}")
        self.assertEqual(response.status_code, 200)

        # Perform delete
        response = self.client.delete(f"/prediction/{self.uid}")
        self.assertEqual(response.status_code, 204)

        # Try deleting again (should return 404)
        response = self.client.delete(f"/prediction/{self.uid}")
        self.assertEqual(response.status_code, 404)

        # Confirm files removed
        self.assertFalse(os.path.exists(self.original_path))
        self.assertFalse(os.path.exists(self.predicted_path))

    def test_delete_prediction_not_found(self):
        fake_uid = str(uuid4())
        response = self.client.delete(f"/prediction/{fake_uid}", headers=self.auth_headers)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Prediction not found")

    def test_delete_with_missing_files(self):
        # Remove files manually
        os.remove(self.original_path)
        os.remove(self.predicted_path)

        response = self.client.delete(f"/prediction/{self.uid}")
        # Still should return 204 even if files missing
        self.assertEqual(response.status_code, 204)
