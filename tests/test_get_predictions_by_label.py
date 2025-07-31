import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app import app
from dependencies.auth import resolve_user_id
from database.connections import get_db

class TestGetPredictionsByLabel(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.fake_user_id = 101
        self.mock_db = MagicMock()

        app.dependency_overrides[get_db] = lambda: self.mock_db
        app.dependency_overrides[resolve_user_id] = lambda: self.fake_user_id

    def tearDown(self):
        app.dependency_overrides = {}

    @patch("controller.prediction.query_prediction_uids_by_label_and_user")
    def test_get_predictions_by_label_success(self, mock_query):
        mock_query.return_value = [
            {"uid": "abc123", "timestamp": "2024-01-01T12:00:00"},
            {"uid": "def456", "timestamp": "2024-01-02T15:00:00"},
        ]

        response = self.client.get("/predictions/label/cat")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["uid"], "abc123")
        self.assertEqual(data[1]["uid"], "def456")

    @patch("controller.prediction.query_prediction_uids_by_label_and_user")
    def test_get_predictions_by_label_empty(self, mock_query):
        mock_query.return_value = []

        response = self.client.get("/predictions/label/unknown")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])
