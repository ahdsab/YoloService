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
    @patch("controller.prediction.os.remove")
    @patch("controller.prediction.os.path.exists")
    def test_delete_prediction_success(self, mock_exists, mock_remove, mock_query):
        # Simulate files exist
        mock_exists.return_value = True

        # Simulate returned file paths
        mock_query.return_value = ("/tmp/fake_original.jpg", "/tmp/fake_predicted.jpg")

        response = self.client.delete(f"/prediction/{self.fake_uid}")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        mock_query.assert_called_once_with(self.mock_db, self.fake_uid, self.fake_user_id)
        self.assertEqual(mock_remove.call_count, 2)

    @patch("controller.prediction.query_delete_prediction_by_uid")
    @patch("controller.prediction.os.remove")
    @patch("controller.prediction.os.path.exists")
    def test_delete_prediction_files_do_not_exist(self, mock_exists, mock_remove, mock_query):
        # Simulate files do not exist
        mock_exists.return_value = False
        mock_query.return_value = ("/tmp/missing1.jpg", "/tmp/missing2.jpg")

        response = self.client.delete(f"/prediction/{self.fake_uid}")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        mock_remove.assert_not_called()
