import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app import app
from dependencies.auth import resolve_user_id
from database.connections import get_db

class TestGetPredictionsByScore(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.fake_user_id = 999
        self.mock_db = MagicMock()

        app.dependency_overrides[get_db] = lambda: self.mock_db
        app.dependency_overrides[resolve_user_id] = lambda: self.fake_user_id

    def tearDown(self):
        app.dependency_overrides = {}

    @patch("controller.prediction.query_prediction_sessions_by_min_score")
    def test_get_predictions_by_score_success(self, mock_query):
        mock_query.return_value = [
            {
                "uid": "uid123",
                "timestamp": "2025-07-30T10:00:00",
                "original_image": "path/to/original.jpg",
                "predicted_image": "path/to/predicted.jpg",
            },
            {
                "uid": "uid456",
                "timestamp": "2025-07-30T11:00:00",
                "original_image": "path/to/another.jpg",
                "predicted_image": "path/to/another_pred.jpg",
            }
        ]

        response = self.client.get("/predictions/score/0.8")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["uid"], "uid123")
        self.assertGreaterEqual(0.8, 0.0)  # Assert for logic consistency if needed

    @patch("controller.prediction.query_prediction_sessions_by_min_score")
    def test_get_predictions_by_score_empty(self, mock_query):
        mock_query.return_value = []

        response = self.client.get("/predictions/score/0.99")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    @patch("controller.prediction.query_prediction_sessions_by_min_score")
    def test_get_predictions_by_score_invalid(self, mock_query):
        # FastAPI should return 422 on invalid float input
        response = self.client.get("/predictions/score/notafloat")
        self.assertEqual(response.status_code, 422)
        mock_query.assert_not_called()
