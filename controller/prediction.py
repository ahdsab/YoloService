from fastapi import UploadFile, File, HTTPException, status, Request
from fastapi.responses import FileResponse, Response
from ultralytics import YOLO
from PIL import Image
import os
import uuid
import shutil
import time

# Disable GPU usage
import torch
torch.cuda.is_available = lambda: False


from dependencies.auth import resolve_user_id
from fastapi import Depends
from fastapi import APIRouter
from database.queries import *
from database.connections import get_db
UPLOAD_DIR = "uploads/original"
PREDICTED_DIR = "uploads/predicted"
DB_PATH = "predictions.db"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PREDICTED_DIR, exist_ok=True)

# Download the AI model (tiny model ~6MB)
model = YOLO("yolov8n.pt")

router = APIRouter()

@router.post("/predict")
def predict(file: UploadFile=File(...), user_id=Depends(resolve_user_id), db: Session=Depends(get_db)):
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

    new_session = query_save_prediction_session(db, uid, original_path, predicted_path, user_id)
    
    detected_labels = []
    for box in results[0].boxes:
        label_idx = int(box.cls[0].item())
        label = model.names[label_idx]
        score = float(box.conf[0])
        bbox = box.xyxy[0].tolist()
        new_detection = query_save_detection_object(db, uid, label, score, bbox)
        detected_labels.append(label)

    processing_time = round(time.time() - start_time, 2)

    return {
        "prediction_uid": uid, 
        "detection_count": len(results[0].boxes),
        "labels": detected_labels,
        "time_took": processing_time
    }

@router.get("/prediction/{uid}")
def get_prediction_by_uid(uid: str, user_id: int=Depends(resolve_user_id), db: Session=Depends(get_db)):
    """
    Get prediction session by uid with all detected objects
    """
    session = query_get_prediction_by_uid(db, uid=uid, user_id=user_id)
    if not session:
        raise HTTPException(status_code=404, detail="Prediction not found")
    
    objects = query_get_detection_objects_by_prediction_uid(db, uid=uid)
    
        
    return {
        "uid": session.uid,
        "timestamp": session.timestamp,
        "original_image": session.original_image,
        "predicted_image": session.predicted_image,
        "detection_objects": [
            {
                "id": obj.id,
                "label": obj.label,
                "score": obj.score,
                "box": obj.box
            } for obj in objects
        ]
    }

@router.get("/predictions/label/{label}")
def get_predictions_by_label(label: str, user_id: int=Depends(resolve_user_id), db: Session=Depends(get_db)):
    """
    Get prediction sessions containing objects with specified label
    """ 
    return query_prediction_uids_by_label_and_user(db, label=label, user_id=user_id)

@router.get("/predictions/score/{min_score}")
def get_predictions_by_score(min_score: float, user_id: int = Depends(resolve_user_id), db: Session=Depends(get_db)):
    """
    Get prediction sessions containing objects with score >= min_score
    """
    return query_prediction_sessions_by_min_score(db, min_score=min_score, user_id=user_id)

@router.get("/prediction/{uid}/image")
def get_prediction_image(uid: str, request: Request,db: Session=Depends(get_db)):
    """
    Get prediction image by uid
    """
    accept = request.headers.get("accept", "")
    image_path = query_predicted_image_by_uid(db, uid=uid)
    if not image_path:
        raise HTTPException(status_code=404, detail="Prediction not found")

    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Predicted image file not found")

    if "image/png" in accept:
        return FileResponse(image_path, media_type="image/png")
    elif "image/jpeg" in accept or "image/jpg" in accept:
        return FileResponse(image_path, media_type="image/jpeg")
    else:
        # If the client doesn't accept image, respond with 406 Not Acceptable
        raise HTTPException(status_code=406, detail="Client does not accept an image format")

@router.get("/predictions/count")
def predictions_count(db: Session=Depends(get_db)):
    """
        Get the total number of predictions made in the last week.
        return: single integer value representing the count of predictions made in the last 7 days
    """
    return query_total_predictions_last_week(db)

@router.delete("/prediction/{uid}")
def delete_prediction(uid: str, user_id: int = Depends(resolve_user_id), db: Session=Depends(get_db)):
    """
        Delete a specific prediction and clean up associated files.
        Remove prediction from database
        Delete original and predicted image files
    """
    original_path, predicted_path = query_delete_prediction_by_uid(db, uid, user_id)

    # Remove files if they exist
    for path in [original_path, predicted_path]:
        if path and os.path.exists(path):
            os.remove(path)

    return Response(status_code=status.HTTP_204_NO_CONTENT)