import unittest
from unittest.mock import patch, MagicMock, mock_open
from fastapi.testclient import TestClient
from PIL import Image
import io
import os
import tempfile
import numpy as np

from app import app
from dependencies.auth import resolve_user_id
from database.connections import get_db


class TestPredictImgParameter(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.fake_user_id = 123
        self.mock_db = MagicMock()

        # Override FastAPI dependencies
        app.dependency_overrides[resolve_user_id] = lambda: self.fake_user_id
        app.dependency_overrides[get_db] = lambda: self.mock_db

    def tearDown(self):
        app.dependency_overrides = {}

    @patch("controller.prediction.model")
    @patch("controller.prediction.query_save_prediction_session")
    @patch("controller.prediction.query_save_detection_object")
    @patch("controller.prediction.upload_image_to_s3")
    @patch("controller.prediction.os.path.isfile")
    @patch("builtins.open", new_callable=mock_open, read_data=b"fake_image_data")
    def test_predict_with_img_parameter_success(
        self, mock_file, mock_isfile, mock_upload_s3, mock_save_detection, mock_save_session, mock_model
    ):
        """Test /predict with img parameter finds and processes image file"""
        # Mock file exists
        mock_isfile.return_value = True
        
        # Mock YOLO model
        fake_result = MagicMock()
        fake_result.boxes = []
        fake_result.plot.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_model.return_value = [fake_result]
        mock_model.names = {}
        
        # Mock database saves
        mock_save_session.return_value = MagicMock()
        mock_save_detection.return_value = MagicMock()
        
        # Mock S3 upload
        mock_upload_s3.return_value = "https://bucket.s3.region.amazonaws.com/fake.jpg"

        response = self.client.post("/predict?img=test.jpg")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("prediction_uid", data)
        self.assertEqual(data["detection_count"], 0)
        self.assertEqual(data["labels"], [])
        
        # Verify file was opened
        mock_file.assert_called()
        mock_isfile.assert_called()

    @patch("controller.prediction.os.path.isfile")
    def test_predict_with_img_parameter_file_not_found(self, mock_isfile):
        """Test /predict with img parameter when file doesn't exist"""
        mock_isfile.return_value = False

        response = self.client.post("/predict?img=nonexistent.jpg")

        self.assertEqual(response.status_code, 400)
        self.assertIn("Image 'nonexistent.jpg' not found on server", response.json()["detail"])

    @patch("controller.prediction.model")
    @patch("controller.prediction.query_save_prediction_session")
    @patch("controller.prediction.query_save_detection_object")
    @patch("controller.prediction.upload_image_to_s3")
    @patch("controller.prediction.os.path.isfile")
    @patch("builtins.open", new_callable=mock_open, read_data=b"fake_image_data")
    def test_predict_s3_fallback_on_upload_failure(
        self, mock_file, mock_isfile, mock_upload_s3, mock_save_detection, mock_save_session, mock_model
    ):
        """Test /predict falls back to local storage when S3 upload fails"""
        # Mock file exists
        mock_isfile.return_value = True
        
        # Mock YOLO model
        fake_result = MagicMock()
        fake_result.boxes = []
        fake_result.plot.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_model.return_value = [fake_result]
        mock_model.names = {}
        
        # Mock database saves
        mock_save_session.return_value = MagicMock()
        mock_save_detection.return_value = MagicMock()
        
        # Mock S3 upload to fail
        mock_upload_s3.side_effect = Exception("No credentials")

        response = self.client.post("/predict?img=test.jpg")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("prediction_uid", data)
        
        # Verify S3 was attempted
        self.assertTrue(mock_upload_s3.called)

    def test_predict_without_file_or_img_parameter(self):
        """Test /predict fails when neither file nor img parameter provided"""
        response = self.client.post("/predict")

        self.assertEqual(response.status_code, 400)
        self.assertIn("Provide either a file upload or 'img' query parameter", response.json()["detail"])

    @patch("controller.prediction.model")
    @patch("controller.prediction.query_save_prediction_session")
    @patch("controller.prediction.query_save_detection_object")
    @patch("controller.prediction.upload_image_to_s3")
    def test_predict_file_cleanup_exception_handling(
        self, mock_upload_s3, mock_save_detection, mock_save_session, mock_model
    ):
        """Test /predict handles file cleanup exceptions gracefully"""
        # Create a real test image
        test_image = Image.new("RGB", (100, 100), color="white")
        image_bytes = io.BytesIO()
        test_image.save(image_bytes, format="JPEG")
        image_bytes.seek(0)
        
        # Mock YOLO model
        fake_result = MagicMock()
        fake_result.boxes = []
        fake_result.plot.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_model.return_value = [fake_result]
        mock_model.names = {}
        
        # Mock database saves
        mock_save_session.return_value = MagicMock()
        mock_save_detection.return_value = MagicMock()
        
        # Mock S3 upload
        mock_upload_s3.return_value = "https://bucket.s3.region.amazonaws.com/fake.jpg"
        
        # Mock os.remove to raise exception (simulating cleanup failure)
        with patch("controller.prediction.os.remove", side_effect=OSError("File not found")):
            response = self.client.post(
                "/predict",
                files={"file": ("test.jpg", image_bytes, "image/jpeg")}
            )

        # Should still succeed despite cleanup failure
        self.assertEqual(response.status_code, 200)
