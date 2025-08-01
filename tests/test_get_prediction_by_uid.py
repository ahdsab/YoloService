import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app import app
from dependencies.auth import resolve_user_id
from database.connections import get_db

class TestGetPredictionByUID(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.fake_user_id = 42
        self.mock_db = MagicMock()

        app.dependency_overrides[resolve_user_id] = lambda: self.fake_user_id
        app.dependency_overrides[get_db] = lambda: self.mock_db

    def tearDown(self):
        app.dependency_overrides = {}

    @patch("controller.prediction.query_get_prediction_by_uid")
    @patch("controller.prediction.query_get_detection_objects_by_prediction_uid")
    def test_get_prediction_success(self, mock_get_objects, mock_get_session):
        # Mock session
        mock_session = MagicMock()
        mock_session.uid = "abc123"
        mock_session.timestamp = "2024-01-01T12:00:00"
        mock_session.original_image = "uploads/original/abc123.jpg"
        mock_session.predicted_image = "uploads/predicted/abc123.jpg"
        mock_get_session.return_value = mock_session

        # Mock detection objects
        mock_object = MagicMock()
        mock_object.id = 1
        mock_object.label = "cat"
        mock_object.score = 0.9
        mock_object.box = [10, 20, 30, 40]
        mock_get_objects.return_value = [mock_object]

        response = self.client.get("/prediction/abc123")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["uid"], "abc123")
        self.assertEqual(data["original_image"], "uploads/original/abc123.jpg")
        self.assertEqual(len(data["detection_objects"]), 1)
        self.assertEqual(data["detection_objects"][0]["label"], "cat")

    @patch("controller.prediction.query_get_prediction_by_uid")
    def test_get_prediction_not_found(self, mock_get_session):
        mock_get_session.return_value = None  # Simulate missing session

        response = self.client.get("/prediction/does_not_exist")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Prediction not found")
