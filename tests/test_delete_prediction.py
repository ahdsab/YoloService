import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import status
from app import app
from dependencies.auth import resolve_user_id
from database.connections import get_db

class TestDeletePredictionEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.fake_user_id = 99
        self.fake_uid = "abc123"

        # Mock database session
        self.mock_db = MagicMock()
        app.dependency_overrides[get_db] = lambda: self.mock_db
        app.dependency_overrides[resolve_user_id] = lambda: self.fake_user_id

    def tearDown(self):
        app.dependency_overrides = {}

    @patch("controller.prediction.query_delete_prediction_by_uid")
    @patch("controller.prediction.delete_file_from_s3")
    def test_delete_prediction_success(self, mock_delete_s3, mock_query):
        # Simulate returned S3 URLs
        mock_query.return_value = ("https://bucket.s3.region.amazonaws.com/original/fake.jpg", "https://bucket.s3.region.amazonaws.com/predicted/fake.jpg")
        mock_delete_s3.return_value = True

        response = self.client.delete(f"/prediction/{self.fake_uid}")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        mock_query.assert_called_once_with(self.mock_db, self.fake_uid, self.fake_user_id)
        self.assertEqual(mock_delete_s3.call_count, 2)

    @patch("controller.prediction.query_delete_prediction_by_uid")
    @patch("controller.prediction.delete_file_from_s3")
    def test_delete_prediction_files_do_not_exist(self, mock_delete_s3, mock_query):
        # Simulate returned S3 URLs
        mock_query.return_value = ("https://bucket.s3.region.amazonaws.com/original/missing1.jpg", "https://bucket.s3.region.amazonaws.com/predicted/missing2.jpg")
        mock_delete_s3.return_value = True

        response = self.client.delete(f"/prediction/{self.fake_uid}")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(mock_delete_s3.call_count, 2)
