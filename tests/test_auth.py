import base64
from fastapi.testclient import TestClient
import app
client = TestClient(app)

def auth_header(username, password):
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}

def test_health_open():
    r = client.get("/health")
    assert r.status_code == 200

def test_predict_unauthenticated():
    r = client.post("/predict", files={"file": ("test.jpg", b"fakeimage", "image/jpeg")})
    assert r.status_code == 200

def test_predict_authenticated():
    r = client.post("/predict", files={"file": ("test.jpg", b"fakeimage", "image/jpeg")},
                    headers=auth_header("admin", "admin"))
    assert r.status_code == 200

def test_protected_endpoint_no_auth():
    r = client.get("/labels")
    assert r.status_code == 401

def test_protected_endpoint_with_auth():
    r = client.get("/labels", headers=auth_header("admin", "admin"))
    assert r.status_code == 200
