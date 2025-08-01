import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app import app  # adjust if your FastAPI app is created elsewhere
from dependencies.auth import resolve_user_id
from database.connections import get_db

class TestLabelsEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

        # Mock DB session and fake user ID
        self.mock_db = MagicMock()
        self.fake_user_id = 1

        # Override FastAPI dependencies
        app.dependency_overrides[get_db] = lambda: self.mock_db
        app.dependency_overrides[resolve_user_id] = lambda: self.fake_user_id

    def tearDown(self):
        app.dependency_overrides = {}

    @patch("controller.labels.query_unique_labels_last_7_days")
    def test_get_unique_labels_last_week(self, mock_query):
        # Mock return value from query
        mock_query.return_value = ["car", "person", "dog"]

        response = self.client.get("/labels")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"labels": ["car", "person", "dog"]})
        mock_query.assert_called_once_with(self.mock_db)

