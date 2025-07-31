import unittest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from PIL import Image
import io
import numpy as np
import time

from app import app
from dependencies.auth import resolve_user_id
from database.connections import get_db


class TestPredictDetection(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

        # Prepare a simple in-memory image
        test_image = Image.new("RGB", (100, 100), color="white")
        self.image_bytes = io.BytesIO()
        test_image.save(self.image_bytes, format="JPEG")
        self.image_bytes.seek(0)

        self.fake_user_id = 123
        self.mock_db = MagicMock()

        app.dependency_overrides[resolve_user_id] = lambda: self.fake_user_id
        app.dependency_overrides[get_db] = lambda: self.mock_db

    def tearDown(self):
        app.dependency_overrides = {}

    @patch("controller.prediction.model")
    @patch("controller.prediction.query_save_prediction_session")
    @patch("controller.prediction.query_save_detection_object")
    def test_detection_box_data_is_processed(
        self,
        mock_save_detection,
        mock_save_session,
        mock_model,
    ):
        # Create a fake detection box
        fake_box = MagicMock()
        fake_box.cls = [MagicMock(item=lambda: 0)]  # label index 0
        fake_box.conf = [0.95]  # confidence

        # Bounding box with tolist
        mock_xyxy = MagicMock()
        mock_xyxy.tolist.return_value = [10, 20, 30, 40]
        fake_box.xyxy = [mock_xyxy]

        # Fake YOLO result
        fake_result = MagicMock()
        fake_result.boxes = [fake_box]
        fake_result.plot.return_value = (255 * np.zeros((100, 100, 3))).astype("uint8")

        # Add small delay to simulate realistic processing time
        def delayed_model_call(*args, **kwargs):
            time.sleep(0.01)
            return [fake_result]

        mock_model.side_effect = delayed_model_call
        mock_model.names = {0: "cat"}

        # Mock prediction session save
        mock_save_session.return_value = MagicMock()

        response = self.client.post(
            "/predict",
            files={"file": ("test.jpg", self.image_bytes, "image/jpeg")},
            headers={"Authorization": "Basic dGVzdHVzZXI6cGFzc3dvcmQ="}
        )

        data = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertIn("labels", data)
        self.assertEqual(data["labels"], ["cat"])
        self.assertEqual(data["detection_count"], 1)
        self.assertGreater(data["time_took"], 0)

        mock_save_detection.assert_called_once()
