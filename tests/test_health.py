import sys
import os
import unittest
from fastapi.testclient import TestClient

# Ensure the app module is importable
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

from app import app

class TestHealthEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_endpoint(self):
        """Test that /health returns status ok"""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

if __name__ == "__main__":
    unittest.main()
