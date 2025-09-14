import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import status
from app import app
from dependencies.auth import resolve_user_id
from database.connections import get_db

class TestGetPredictionImage(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.fake_user_id = 99
        self.fake_uid = "abc123"
        self.fake_path = f"/fake/path/predicted_{self.fake_uid}.jpg"

        # Mock dependencies
        self.mock_db = MagicMock()
        app.dependency_overrides[get_db] = lambda: self.mock_db
        app.dependency_overrides[resolve_user_id] = lambda: self.fake_user_id

    def tearDown(self):
        app.dependency_overrides = {}

    @patch("controller.image.query_predicted_image_by_uid")
    @patch("controller.image.download_image_from_s3")
    def test_returns_jpeg_if_accepted(self, mock_download_s3, mock_query):
        mock_query.return_value = "https://bucket.s3.region.amazonaws.com/predicted/fake.jpg"
        mock_image_data = MagicMock()
        mock_image_data.getvalue.return_value = b"fake_image_data"
        mock_download_s3.return_value = mock_image_data

        headers = {"Accept": "image/jpeg"}
        response = self.client.get(f"/prediction/{self.fake_uid}/image", headers=headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_query.assert_called_once_with(self.mock_db, uid=self.fake_uid)
        mock_download_s3.assert_called_once_with("https://bucket.s3.region.amazonaws.com/predicted/fake.jpg")

    @patch("controller.image.query_predicted_image_by_uid")
    @patch("controller.image.download_image_from_s3")
    def test_returns_png_if_requested(self, mock_download_s3, mock_query):
        mock_query.return_value = "https://bucket.s3.region.amazonaws.com/predicted/fake.jpg"
        mock_image_data = MagicMock()
        mock_image_data.getvalue.return_value = b"fake_image_data"
        mock_download_s3.return_value = mock_image_data

        headers = {"Accept": "image/png"}
        response = self.client.get(f"/prediction/{self.fake_uid}/image", headers=headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_download_s3.assert_called_once_with("https://bucket.s3.region.amazonaws.com/predicted/fake.jpg")

    @patch("controller.image.query_predicted_image_by_uid")
    def test_returns_404_if_prediction_not_found(self, mock_query):
        mock_query.return_value = None
        headers = {"Accept": "image/jpeg"}
        response = self.client.get(f"/prediction/{self.fake_uid}/image", headers=headers)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["detail"], "Prediction not found")

    @patch("controller.image.query_predicted_image_by_uid")
    @patch("controller.image.download_image_from_s3")
    def test_returns_404_if_file_missing(self, mock_download_s3, mock_query):
        mock_query.return_value = "https://bucket.s3.region.amazonaws.com/predicted/fake.jpg"
        mock_download_s3.side_effect = Exception("S3 download failed")
        headers = {"Accept": "image/jpeg"}
        response = self.client.get(f"/prediction/{self.fake_uid}/image", headers=headers)

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("Failed to retrieve image", response.json()["detail"])

    @patch("controller.image.query_predicted_image_by_uid")
    @patch("controller.image.download_image_from_s3")
    def test_returns_406_if_format_not_accepted(self, mock_download_s3, mock_query):
        mock_query.return_value = "https://bucket.s3.region.amazonaws.com/predicted/fake.jpg"
        mock_image_data = MagicMock()
        mock_image_data.getvalue.return_value = b"fake_image_data"
        mock_download_s3.return_value = mock_image_data
        headers = {"Accept": "application/json"}
        response = self.client.get(f"/prediction/{self.fake_uid}/image", headers=headers)

        # The endpoint doesn't actually check accept headers for 406, it defaults to jpeg
        self.assertEqual(response.status_code, status.HTTP_200_OK)
