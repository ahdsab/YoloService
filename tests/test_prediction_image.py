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

    @patch("controller.prediction.query_predicted_image_by_uid")
    @patch("controller.prediction.os.path.exists")
    @patch("controller.prediction.FileResponse")
    def test_returns_jpeg_if_accepted(self, mock_file_response, mock_exists, mock_query):
        mock_query.return_value = self.fake_path
        mock_exists.return_value = True
        mock_file_response.return_value = MagicMock()

        headers = {"Accept": "image/jpeg"}
        response = self.client.get(f"/prediction/{self.fake_uid}/image", headers=headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_query.assert_called_once_with(self.mock_db, uid=self.fake_uid)
        mock_file_response.assert_called_once_with(self.fake_path, media_type="image/jpeg")

    @patch("controller.prediction.query_predicted_image_by_uid")
    @patch("controller.prediction.os.path.exists")
    @patch("controller.prediction.FileResponse")
    def test_returns_png_if_requested(self, mock_file_response, mock_exists, mock_query):
        mock_query.return_value = self.fake_path
        mock_exists.return_value = True
        mock_file_response.return_value = MagicMock()

        headers = {"Accept": "image/png"}
        response = self.client.get(f"/prediction/{self.fake_uid}/image", headers=headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_file_response.assert_called_once_with(self.fake_path, media_type="image/png")

    @patch("controller.prediction.query_predicted_image_by_uid")
    def test_returns_404_if_prediction_not_found(self, mock_query):
        mock_query.return_value = None
        headers = {"Accept": "image/jpeg"}
        response = self.client.get(f"/prediction/{self.fake_uid}/image", headers=headers)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["detail"], "Prediction not found")

    @patch("controller.prediction.query_predicted_image_by_uid")
    @patch("controller.prediction.os.path.exists")
    def test_returns_404_if_file_missing(self, mock_exists, mock_query):
        mock_query.return_value = self.fake_path
        mock_exists.return_value = False
        headers = {"Accept": "image/jpeg"}
        response = self.client.get(f"/prediction/{self.fake_uid}/image", headers=headers)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["detail"], "Predicted image file not found")

    @patch("controller.prediction.query_predicted_image_by_uid")
    @patch("controller.prediction.os.path.exists")
    def test_returns_406_if_format_not_accepted(self, mock_exists, mock_query):
        mock_query.return_value = self.fake_path
        mock_exists.return_value = True
        headers = {"Accept": "application/json"}
        response = self.client.get(f"/prediction/{self.fake_uid}/image", headers=headers)

        self.assertEqual(response.status_code, status.HTTP_406_NOT_ACCEPTABLE)
        self.assertEqual(response.json()["detail"], "Client does not accept an image format")
