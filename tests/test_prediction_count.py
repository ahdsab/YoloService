import os
import sqlite3
import pytest
from fastapi.testclient import TestClient
from app import app, DB_PATH, init_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_and_teardown():
    # Before each test: clear DB and setup tables
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    init_db()
    yield
    # After each test: cleanup
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

def test_predictions_count_empty():
    # Initially there should be 0 predictions
    response = client.get("/predictions/count")
    assert response.status_code == 200
    assert response.json() == {"count": 0}

def test_predictions_count_with_data():
    # Insert a fake prediction into the last 7 days
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO prediction_sessions (uid, original_image, predicted_image)
            VALUES ('1234', 'img1.jpg', 'img1_pred.jpg')
        """)

    response = client.get("/predictions/count")
    assert response.status_code == 200
    assert response.json() == {"count": 1}
