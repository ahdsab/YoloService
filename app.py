from fastapi import FastAPI, UploadFile, File, HTTPException, Request, status
from fastapi.responses import FileResponse, Response
from ultralytics import YOLO
from PIL import Image
import sqlite3
import os
import uuid
import shutil

import time

from collections import Counter


# Disable GPU usage
import torch
torch.cuda.is_available = lambda: False


from dependencies.auth import resolve_user_id, ensure_anonymous_account
from fastapi import Depends



app = FastAPI()

UPLOAD_DIR = "uploads/original"
PREDICTED_DIR = "uploads/predicted"
DB_PATH = "predictions.db"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PREDICTED_DIR, exist_ok=True)

# Download the AI model (tiny model ~6MB)
model = YOLO("yolov8n.pt")  

# Initialize SQLite
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        # Create the predictions main table to store the prediction session
        conn.execute("""
            CREATE TABLE IF NOT EXISTS prediction_sessions (
                uid TEXT PRIMARY KEY,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                original_image TEXT,
                predicted_image TEXT,
                user_id INTEGER,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # Create the objects table to store individual detected objects in a given image
        conn.execute("""
            CREATE TABLE IF NOT EXISTS detection_objects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prediction_uid TEXT,
                label TEXT,
                score REAL,
                box TEXT,
                FOREIGN KEY (prediction_uid) REFERENCES prediction_sessions (uid)
            )
        """)

        # Create the users table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)
        
        # Create index for faster queries
        conn.execute("CREATE INDEX IF NOT EXISTS idx_prediction_uid ON detection_objects (prediction_uid)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_label ON detection_objects (label)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_score ON detection_objects (score)")
        

init_db()

def save_prediction_session(uid, original_image, predicted_image, user_id):
    """
    Save prediction session to database
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO prediction_sessions (uid, original_image, predicted_image, user_id)
            VALUES (?, ?, ?, ?)
        """, (uid, original_image, predicted_image, user_id))

def save_detection_object(prediction_uid, label, score, box):
    """
    Save detection object to database
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO detection_objects (prediction_uid, label, score, box)
            VALUES (?, ?, ?, ?)
        """, (prediction_uid, label, score, str(box)))

@app.post("/predict")
def predict(file: UploadFile = File(...), user_id = Depends(resolve_user_id)):
    """
    Predict objects in an image
    """

    start_time = time.time()
    ext = os.path.splitext(file.filename)[1]
    uid = str(uuid.uuid4())
    original_path = os.path.join(UPLOAD_DIR, uid + ext)
    predicted_path = os.path.join(PREDICTED_DIR, uid + ext)

    with open(original_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    results = model(original_path, device="cpu")

    annotated_frame = results[0].plot()  # NumPy image with boxes
    annotated_image = Image.fromarray(annotated_frame)
    annotated_image.save(predicted_path)

    save_prediction_session(uid, original_path, predicted_path, user_id)
    
    detected_labels = []
    for box in results[0].boxes:
        label_idx = int(box.cls[0].item())
        label = model.names[label_idx]
        score = float(box.conf[0])
        bbox = box.xyxy[0].tolist()
        save_detection_object(uid, label, score, bbox)
        detected_labels.append(label)

    processing_time = round(time.time() - start_time, 2)

    return {
        "prediction_uid": uid, 
        "detection_count": len(results[0].boxes),
        "labels": detected_labels,
        "time_took": processing_time
    }

@app.get("/prediction/{uid}")
def get_prediction_by_uid(uid: str, user_id: int = Depends(resolve_user_id)):
    """
    Get prediction session by uid with all detected objects
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        # Get prediction session
        session = conn.execute("SELECT * FROM prediction_sessions WHERE uid = ? AND user_id = ?",
                               (uid, user_id)).fetchone()
        if not session:
            raise HTTPException(status_code=404, detail="Prediction not found")
            
        # Get all detection objects for this prediction
        objects = conn.execute(
            "SELECT * FROM detection_objects WHERE prediction_uid = ?", 
            (uid,)
        ).fetchall()
        
        return {
            "uid": session["uid"],
            "timestamp": session["timestamp"],
            "original_image": session["original_image"],
            "predicted_image": session["predicted_image"],
            "detection_objects": [
                {
                    "id": obj["id"],
                    "label": obj["label"],
                    "score": obj["score"],
                    "box": obj["box"]
                } for obj in objects
            ]
        }

@app.get("/predictions/label/{label}")
def get_predictions_by_label(label: str, user_id: int = Depends(resolve_user_id)):
    """
    Get prediction sessions containing objects with specified label
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT DISTINCT ps.uid, ps.timestamp
            FROM prediction_sessions ps
            JOIN detection_objects do ON ps.uid = do.prediction_uid
            WHERE do.label = ?  AND ps.user_id = ?
        """, (label, user_id)).fetchall()
        
        return [{"uid": row["uid"], "timestamp": row["timestamp"]} for row in rows]

@app.get("/predictions/score/{min_score}")
def get_predictions_by_score(min_score: float, user_id: int = Depends(resolve_user_id)):
    """
    Get prediction sessions containing objects with score >= min_score
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT DISTINCT ps.uid, ps.timestamp
            FROM prediction_sessions ps
            JOIN detection_objects do ON ps.uid = do.prediction_uid
            WHERE do.score >= ?  AND ps.user_id = ?
        """, (min_score, user_id)).fetchall()
        
        return [{"uid": row["uid"], "timestamp": row["timestamp"]} for row in rows]

@app.get("/image/{type}/{filename}")
def get_image(type: str, filename: str, user_id: int = Depends(resolve_user_id)):
    """
    Get image by type and filename
    """
    if type not in ["original", "predicted"]:
        raise HTTPException(status_code=400, detail="Invalid image type")
    path = os.path.join("uploads", type, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path)

@app.get("/prediction/{uid}/image")
def get_prediction_image(uid: str):
    """
    Get prediction image by uid
    """
    accept = request.headers.get("accept", "")
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT predicted_image FROM prediction_sessions WHERE uid = ?", (uid,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Prediction not found")
        image_path = row[0]

    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Predicted image file not found")

    if "image/png" in accept:
        return FileResponse(image_path, media_type="image/png")
    elif "image/jpeg" in accept or "image/jpg" in accept:
        return FileResponse(image_path, media_type="image/jpeg")
    else:
        # If the client doesn't accept image, respond with 406 Not Acceptable
        raise HTTPException(status_code=406, detail="Client does not accept an image format")

@app.get("/health")
def health():
    """
    Health check endpoint
    """
    return {"status": "ok"}

@app.get("/predictions/count")
def predictions_count():
    """
        Get the total number of predictions made in the last week.
        return: single integer value representing the count of predictions made in the last 7 days
    """

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        query = """
                SELECT COUNT(*) FROM prediction_sessions
                WHERE timestamp >= datetime('now', '-7 days');
                """
        cursor.execute(query)
        count = cursor.fetchone()[0]
    return {"count": count}


@app.get("/labels")
def get_unique_labels_last_week():
    """
    Return all unique object labels detected in the last 7 days
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        query = """
            SELECT DISTINCT do.label
            FROM detection_objects do
            JOIN prediction_sessions ps ON do.prediction_uid = ps.uid
            WHERE ps.timestamp >= datetime('now', '-7 days');
        """
        cursor.execute(query)
        labels = [row[0] for row in cursor.fetchall()]
    return {"labels": labels}


@app.delete("/prediction/{uid}")
def delete_prediction(uid: str, user_id: int = Depends(resolve_user_id)):
    """
        Delete a specific prediction and clean up associated files.
        Remove prediction from database
        Delete original and predicted image files
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # Fetch image paths before deleting
        row = cursor.execute("""
            SELECT original_image, predicted_image FROM prediction_sessions WHERE uid = ? AND user_id = ?
        """, (uid, user_id)).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Prediction not found")

        original_image_path, predicted_image_path = row

        # Delete detection objects
        cursor.execute("DELETE FROM detection_objects WHERE prediction_uid = ?", (uid,))

        # Delete prediction session
        cursor.execute("DELETE FROM prediction_sessions WHERE uid = ?", (uid,))

    # Remove files if they exist
    for path in [original_image_path, predicted_image_path]:
        if path and os.path.exists(path):
            os.remove(path)

    return Response(status_code=status.HTTP_204_NO_CONTENT)



@app.get("/stats")
def get_prediction_stats(user_id: int = Depends(resolve_user_id)):
    """
    Return analytics for predictions made in the last 7 days:
    - total number of predictions
    - average confidence score
    - most common labels
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # Total number of predictions in the last 7 days
        cursor.execute("""
            SELECT COUNT(*) FROM prediction_sessions
            WHERE timestamp >= datetime('now', '-7 days') AND user_id = ?;
        """,(user_id,))
        total_predictions = cursor.fetchone()[0]

        # All confidence scores for detections in the last 7 days
        cursor.execute("""
            SELECT do.score FROM detection_objects do
            JOIN prediction_sessions ps ON do.prediction_uid = ps.uid
            WHERE ps.timestamp >= datetime('now', '-7 days') AND ps.user_id = ?;
        """,(user_id,))
        scores = [row[0] for row in cursor.fetchall()]
        avg_score = round(sum(scores) / len(scores), 3) if scores else 0.0

        # Most frequent labels
        cursor.execute("""
            SELECT do.label FROM detection_objects do
            JOIN prediction_sessions ps ON do.prediction_uid = ps.uid
            WHERE ps.timestamp >= datetime('now', '-7 days') AND ps.user_id = ?;
        """,(user_id,))
        labels = [row[0] for row in cursor.fetchall()]
        label_counts = Counter(labels).most_common(5)

    return {
        "total_predictions": total_predictions,
        "average_confidence_score": avg_score,
        "most_common_labels": {label:count for label, count in label_counts}
    }

        

if __name__ == "__main__": # pragma: no cover
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)  # pragma: no cover
