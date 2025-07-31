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

        # Create in-memory test image
        self.test_image = Image.new("RGB", (100, 100), color="red")
        self.image_bytes = io.BytesIO()
        self.test_image.save(self.image_bytes, format="JPEG")
        self.image_bytes.seek(0)

        # Mocked user ID and DB session
        self.fake_user_id = 123
        self.mock_db = MagicMock()

        # Override FastAPI dependencies
        app.dependency_overrides[resolve_user_id] = lambda: self.fake_user_id
        app.dependency_overrides[get_db] = lambda: self.mock_db

    def tearDown(self):
        app.dependency_overrides = {}

    def _setup_yolo_mock(self, mock_model):
        # Simulate fake image output
        fake_np_image = np.zeros((640, 640, 3), dtype=np.uint8)

        # Mock prediction results
        mock_box = MagicMock()
        mock_box.cls = [MagicMock(item=lambda: 0)]
        mock_box.conf = [0.9]
        mock_box.xyxy = [np.array([10, 20, 30, 40])]

        mock_result = MagicMock()
        mock_result.boxes = mock_box
        mock_result.plot.return_value = fake_np_image

        mock_results = [mock_result]

        # Simulate time delay to produce a time_took > 0
        def fake_model_call(*args, **kwargs):
            time.sleep(0.01)
            return mock_results

        mock_model.side_effect = fake_model_call
        mock_model.names = {0: "test_label"}

    @patch("controller.prediction.model")
    def test_predict_includes_processing_time_with_auth(self, mock_model):
        """Authenticated user: /predict returns processing time > 0"""
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

    @patch("controller.prediction.model")
    def test_predict_includes_processing_time_without_auth(self, mock_model):
        """Anonymous user: /predict returns processing time > 0"""
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
