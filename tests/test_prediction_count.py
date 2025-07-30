import unittest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from app import app
from dependencies.auth import resolve_user_id
from database.connections import get_db
from models.PredictionSession_model import PredictionSession

class TestPredictionCount(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.fake_user_id = 1
        self.now = datetime.utcnow()

        # Dependency overrides
        self.mock_db = MagicMock()
        app.dependency_overrides[get_db] = lambda: self.mock_db
        app.dependency_overrides[resolve_user_id] = lambda: self.fake_user_id

    def tearDown(self):
        app.dependency_overrides = {}

    def _setup_mock_query(self, timestamps):
        """
        Mocks db.query(PredictionSession).filter(...).count()
        Based on whether timestamps are within the last 7 days
        """
        recent_cutoff = self.now - timedelta(days=7)
        count = sum(1 for ts in timestamps if ts >= recent_cutoff)

        query_mock = MagicMock()
        self.mock_db.query.return_value.filter.return_value.count.return_value = count

    def test_prediction_count_format(self):
        """Check response format and status with empty DB"""
        self._setup_mock_query([])

        response = self.client.get("/predictions/count")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("count", data)
        self.assertIsInstance(data["count"], int)
        self.assertEqual(data["count"], 0)

    def test_prediction_count_last_7_days(self):
        """Ensure only recent predictions are counted"""
        timestamps = [
            self.now - timedelta(days=2),   # recent
            self.now - timedelta(days=10),  # old
        ]
        self._setup_mock_query(timestamps)

        response = self.client.get("/predictions/count")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

    def test_prediction_count_multiple_recent(self):
        """Ensure multiple recent predictions are counted"""
        timestamps = [
            self.now - timedelta(days=1),
            self.now - timedelta(days=3),
            self.now - timedelta(days=6),
        ]
        self._setup_mock_query(timestamps)

        response = self.client.get("/predictions/count")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 3)

    def test_prediction_count_all_old(self):
        """Ensure old predictions are not counted"""
        timestamps = [
            self.now - timedelta(days=8),
            self.now - timedelta(days=15),
        ]
        self._setup_mock_query(timestamps)

        response = self.client.get("/predictions/count")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 0)

    def test_prediction_exactly_7_days_old(self):
        """Prediction exactly 7 days ago should be included"""
        timestamps = [self.now - timedelta(days=7)]
        self._setup_mock_query(timestamps)

        response = self.client.get("/predictions/count")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
