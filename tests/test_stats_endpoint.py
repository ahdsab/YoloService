import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app import app  # Adjust if your FastAPI app is defined elsewhere
from database.connections import get_db
from dependencies.auth import resolve_user_id

class TestStatsEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.mock_db = MagicMock()
        self.fake_user_id = 42

        # Override FastAPI dependencies
        app.dependency_overrides[get_db] = lambda: self.mock_db
        app.dependency_overrides[resolve_user_id] = lambda: self.fake_user_id

    def tearDown(self):
        app.dependency_overrides = {}

    @patch("controller.stats.query_prediction_stats")  # Adjust this path based on your file
    def test_stats_response_structure_and_values(self, mock_query):
        # Fake return values from the query
        mock_query.return_value = (
            10,                            # total predictions
            0.87,                          # average confidence
            [("cat", 4), ("dog", 3)]       # most common labels
        )

        response = self.client.get("/stats")

        self.assertEqual(response.status_code, 200)

        expected_response = {
            "total_predictions": 10,
            "average_confidence_score": 0.87,
            "most_common_labels": {
                "cat": 4,
                "dog": 3
            }
        }

        self.assertEqual(response.json(), expected_response)

        # Ensure the query was called with mocked db and user
        mock_query.assert_called_once_with(self.mock_db, self.fake_user_id)
