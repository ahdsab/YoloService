import unittest
import os
import sqlite3
from fastapi.testclient import TestClient
from app import app, init_db, DB_PATH, UPLOAD_DIR, PREDICTED_DIR
from uuid import uuid4
from datetime import datetime
from base64 import b64encode
from PIL import Image

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
        # Insert a dummy user
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                ("testuser", "testpass"),
            )

    def setUp(self):
        # Ensure upload directories exist
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        os.makedirs(PREDICTED_DIR, exist_ok=True)

    def test_get_prediction_by_uid_not_found(self):
        response = client.get("/prediction/invalid-uid", headers=auth_headers())
        self.assertEqual(response.status_code, 404)
        self.assertIn("Prediction not found", response.text)

    def test_get_predictions_by_label_empty(self):
        response = client.get("/predictions/label/nonexistent", headers=auth_headers())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_get_predictions_by_score_empty(self):
        response = client.get("/predictions/score/0.9", headers=auth_headers())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_get_image_invalid_type(self):
        response = client.get("/image/invalid_type/doesnotexist.jpg", headers=auth_headers())
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid image type", response.text)

    def test_get_image_not_found(self):
        response = client.get("/image/original/missing.jpg", headers=auth_headers())
        self.assertEqual(response.status_code, 404)
        self.assertIn("Image not found", response.text)

    def test_get_prediction_image_not_found(self):
        response = client.get("/prediction/invalid/image", headers=auth_headers())
        self.assertEqual(response.status_code, 404)
        self.assertIn("Prediction not found", response.text)

    def test_get_prediction_image_file_not_found(self):
        # Insert a prediction with a non-existing predicted image
        uid = str(uuid4())
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO prediction_sessions (uid, original_image, predicted_image, user_id) VALUES (?, ?, ?, ?)",
                (uid, "fake_original.jpg", "fake_predicted.jpg", 1),
            )

        response = client.get(f"/prediction/{uid}/image", headers=auth_headers())
        self.assertEqual(response.status_code, 404)
        self.assertIn("Predicted image file not found", response.text)

    def test_get_prediction_image_unsupported_accept(self):
        # Create a temporary image file
        uid = str(uuid4())
        image_path = os.path.join(PREDICTED_DIR, uid + ".jpg")
        Image.new("RGB", (10, 10), color="red").save(image_path)

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO prediction_sessions (uid, original_image, predicted_image, user_id) VALUES (?, ?, ?, ?)",
                (uid, "original.jpg", image_path, 1),
            )

        # Request with unsupported Accept header
        headers = auth_headers()
        headers["accept"] = "application/json"
        response = client.get(f"/prediction/{uid}/image", headers=headers)
        self.assertEqual(response.status_code, 406)
        self.assertIn("Client does not accept", response.text)

    def test_stats_endpoint_empty(self):
        # Remove all data
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM detection_objects")
            conn.execute("DELETE FROM prediction_sessions")

        response = client.get("/stats", headers=auth_headers())
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_predictions"], 0)
        self.assertEqual(data["average_confidence_score"], 0.0)
        self.assertEqual(data["most_common_labels"], {})

    def test_main_entrypoint(self):
        # Simulate __main__ check
        import importlib.util
        spec = importlib.util.spec_from_file_location("app_main", "app.py")
        app_main = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(app_main)
        self.assertTrue(hasattr(app_main, "app"))
