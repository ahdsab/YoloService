import os
import sqlite3
import unittest
from uuid import uuid4
from datetime import datetime
from fastapi.testclient import TestClient
from app import app, init_db, DB_PATH, UPLOAD_DIR, PREDICTED_DIR

client = TestClient(app)

class TestImageAndStats(unittest.TestCase):

    def setUp(self):
        # Reset DB
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        init_db()

        self.uid = str(uuid4())
        self.original_path = os.path.join(UPLOAD_DIR, self.uid + ".jpg")
        self.predicted_path = os.path.join(PREDICTED_DIR, self.uid + ".jpg")

        os.makedirs(UPLOAD_DIR, exist_ok=True)
        os.makedirs(PREDICTED_DIR, exist_ok=True)

        # Create fake image files
        with open(self.original_path, "w") as f:
            f.write("fake original")
        with open(self.predicted_path, "w") as f:
            f.write("fake predicted")

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                INSERT INTO prediction_sessions (uid, timestamp, original_image, predicted_image)
                VALUES (?, ?, ?, ?)
            """, (self.uid, datetime.utcnow().isoformat(), self.original_path, self.predicted_path))
            conn.execute("""
                INSERT INTO detection_objects (prediction_uid, label, score, box)
                VALUES (?, ?, ?, ?)
            """, (self.uid, "car", 0.9, "[0,0,100,100]"))

    def tearDown(self):
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        if os.path.exists(self.original_path):
            os.remove(self.original_path)
        if os.path.exists(self.predicted_path):
            os.remove(self.predicted_path)

    def test_get_prediction_image_success(self):
        headers = {"accept": "image/jpeg"}
        response = client.get(f"/prediction/{self.uid}/image", headers=headers)
        self.assertEqual(response.status_code, 200)

    def test_get_prediction_image_file_missing(self):
        os.remove(self.original_path)
        headers = {"accept": "image/jpeg"}
        response = client.get(f"/prediction/{self.uid}/image", headers=headers)
        self.assertIn(response.status_code, (200, 404))

    def test_get_prediction_image_invalid_accept(self):
        headers = {"accept": "application/pdf"}
        response = client.get(f"/prediction/{self.uid}/image", headers=headers)
        self.assertEqual(response.status_code, 406)

    def test_stats_empty(self):
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        init_db()

        response = client.get("/stats")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_predictions"], 0)
