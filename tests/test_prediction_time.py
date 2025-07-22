import unittest
from fastapi.testclient import TestClient
from PIL import Image
import io
import os
import sqlite3
from app import app, init_db, DB_PATH

class TestProcessingTime(unittest.TestCase):
    def setUp(self):
        # Ensure DB exists and add a test user
        if not os.path.exists(DB_PATH):
            init_db()
        self.client = TestClient(app)
        
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO users (username, password)
                VALUES (?, ?)
            """, ("testuser", "testpass"))
        self.auth_headers = {"Authorization": "Basic dGVzdHVzZXI6dGVzdHBhc3M="}

        # Create a simple test image
        self.test_image = Image.new('RGB', (100, 100), color='red')
        self.image_bytes = io.BytesIO()
        self.test_image.save(self.image_bytes, format='JPEG')
        self.image_bytes.seek(0)

    def test_predict_includes_processing_time(self):
        """Test that the predict endpoint returns processing time"""
        
        response = self.client.post(
            "/predict",
            files={"file": ("test.jpg", self.image_bytes, "image/jpeg")},
            headers=self.auth_headers  # Optional, since /predict supports anonymous
        )
        
        # Check response
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify new field exists
        self.assertIn("time_took", data)
        self.assertIsInstance(data["time_took"], (int, float))
        self.assertGreater(data["time_took"], 0)
