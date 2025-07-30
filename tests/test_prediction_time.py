import unittest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from PIL import Image
import io
import numpy as np
import time

from app import app
from dependencies.auth import resolve_user_id
from database.connections import get_db

class TestProcessingTime(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

        # Create a simple in-memory image
        self.test_image = Image.new("RGB", (100, 100), color="red")
        self.image_bytes = io.BytesIO()
        self.test_image.save(self.image_bytes, format="JPEG")
        self.image_bytes.seek(0)

        # Fake user ID and mocked DB session
        self.fake_user_id = 123
        self.mock_db = MagicMock()

        # Override dependencies
        app.dependency_overrides[resolve_user_id] = lambda: self.fake_user_id
        app.dependency_overrides[get_db] = lambda: self.mock_db

    def tearDown(self):
        app.dependency_overrides = {}

    def _setup_yolo_mock(self, mock_model):
        # Create fake NumPy image (YOLO output)
        fake_np_image = np.zeros((640, 640, 3), dtype=np.uint8)

        # Create mock YOLO results
        mock_results = MagicMock()
        mock_results[0].boxes = [MagicMock()]
        mock_results[0].boxes[0].cls = [MagicMock(item=lambda: 0)]
        mock_results[0].boxes[0].conf = [0.9]
        mock_results[0].boxes[0].xyxy = [np.array([10, 20, 30, 40])]
        mock_results[0].plot.return_value = fake_np_image

        # Simulate delay to make time_took > 0
        def fake_model_call(*args, **kwargs):
            time.sleep(0.01)
            return mock_results

        mock_model.side_effect = fake_model_call
        mock_model.names = {0: "test_label"}

    @patch("controler.prediction.model")
    def test_predict_includes_processing_time_with_auth(self, mock_model):
        """Authenticated user: /predict should return processing time > 0"""
        self._setup_yolo_mock(mock_model)

        response = self.client.post(
            "/predict",
            files={"file": ("test.jpg", self.image_bytes, "image/jpeg")},
            headers={"Authorization": "Basic dGVzdHVzZXI6dGVzdHBhc3M="}
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("time_took", data)
        self.assertIsInstance(data["time_took"], (int, float))
        self.assertGreater(data["time_took"], 0.0)

    @patch("controler.prediction.model")
    def test_predict_includes_processing_time_without_auth(self, mock_model):
        """Anonymous user: /predict should still return processing time > 0"""
        # Override resolve_user_id to simulate anonymous behavior
        app.dependency_overrides[resolve_user_id] = lambda: 0

        self._setup_yolo_mock(mock_model)

        response = self.client.post(
            "/predict",
            files={"file": ("test.jpg", self.image_bytes, "image/jpeg")}
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("time_took", data)
        self.assertIsInstance(data["time_took"], (int, float))
        self.assertGreater(data["time_took"], 0.0)
