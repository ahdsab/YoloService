import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import status
from app import app
from dependencies.auth import resolve_user_id

class TestGetImageEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.fake_user_id = 42

        # Override auth dependency
        app.dependency_overrides[resolve_user_id] = lambda: self.fake_user_id

        self.valid_filename = "sample.jpg"
        self.valid_path = f"uploads/original/{self.valid_filename}"

    def tearDown(self):
        app.dependency_overrides = {}

    @patch("controller.image.os.path.exists")
    @patch("controller.image.FileResponse")
    def test_get_image_success(self, mock_file_response, mock_exists):
        mock_exists.return_value = True
        mock_file_response.return_value = MagicMock()

        response = self.client.get(f"/image/original/{self.valid_filename}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_exists.assert_called_once_with(self.valid_path)
        mock_file_response.assert_called_once_with(self.valid_path)

    def test_get_image_invalid_type(self):
        response = self.client.get(f"/image/invalid/{self.valid_filename}")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["detail"], "Invalid image type")

    @patch("controller.image.os.path.exists")
    def test_get_image_not_found(self, mock_exists):
        mock_exists.return_value = False

        response = self.client.get(f"/image/original/{self.valid_filename}")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["detail"], "Image not found")
