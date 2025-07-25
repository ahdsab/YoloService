import unittest
import os
import base64
from fastapi.testclient import TestClient
from app import app, DB_PATH, init_db  # use init_db here

client = TestClient(app)

def encode_basic_auth(username, password):
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}

class AuthTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        init_db()  # ensures prediction_sessions table exists

    def test_01_health_no_auth(self):
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_02_predict_no_auth(self):
        with open("beatles.jpeg", "rb") as img:
            response = client.post("/predict", files={"file": ("image.jpg", img, "image/jpeg")})
        self.assertEqual(response.status_code, 200)
        self.assertIn("prediction_uid", response.json())

    def test_03_create_user_and_predict(self):
        creds = encode_basic_auth("newuser", "mypassword")
        with open("beatles.jpeg", "rb") as img:
            response = client.post("/predict", headers=creds, files={"file": ("image.jpg", img, "image/jpeg")})
        self.assertEqual(response.status_code, 200)
        self.assertIn("labels", response.json())

    def test_04_missing_password(self):
        token = base64.b64encode("useronly:".encode()).decode()
        headers = {"Authorization": f"Basic {token}"}
        with open("beatles.jpeg", "rb") as img:
            response = client.post("/predict", headers=headers, files={"file": ("image.jpg", img, "image/jpeg")})
        self.assertEqual(response.status_code, 401)
        self.assertIn("Password is required", response.text)

    def test_05_wrong_password(self):
        correct_creds = encode_basic_auth("user2", "rightpass")
        with open("beatles.jpeg", "rb") as img:
            _ = client.post("/predict", headers=correct_creds, files={"file": ("image.jpg", img, "image/jpeg")})

        wrong_creds = encode_basic_auth("user2", "wrongpass")
        with open("beatles.jpeg", "rb") as img:
            response = client.post("/predict", headers=wrong_creds, files={"file": ("image.jpg", img, "image/jpeg")})
        self.assertEqual(response.status_code, 401)
        self.assertIn("Incorrect password", response.text)
