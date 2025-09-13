from fastapi import UploadFile, File, HTTPException, status, Request
from fastapi.responses import FileResponse, Response
from ultralytics import YOLO
from PIL import Image
import os
import uuid
import shutil
import time
from io import BytesIO

# Disable GPU usage
import torch
torch.cuda.is_available = lambda: False

from dependencies.auth import resolve_user_id
from fastapi import Depends
from fastapi import APIRouter
from database.queries import *
from database.connections import get_db
from utils.s3_utils import upload_image_to_s3, download_image_from_s3, delete_file_from_s3
UPLOAD_DIR = "uploads/original"
PREDICTED_DIR = "uploads/predicted"
DB_PATH = "predictions.db"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PREDICTED_DIR, exist_ok=True)

# Download the AI model (tiny model ~6MB)
model = YOLO("yolov8n.pt")

router = APIRouter()

@router.post("/predict")
def predict(
    file: UploadFile = File(None),
    db: Session = Depends(get_db),
    user_id: int = Depends(resolve_user_id),
    img: str = None,
    ):
    """
    Predict objects in an image
    """
    print(img)
    start_time = time.time()

    # Determine source of image bytes and extension
    file_content = None
    if img and not file:
        # Try to locate the image on disk using common locations
        candidate_paths = [
            img,
            os.path.join(os.getcwd(), img),
            os.path.join(UPLOAD_DIR, img),
        ]
        image_path = next((p for p in candidate_paths if os.path.isfile(p)), None)
        if not image_path:
            raise HTTPException(status_code=400, detail=f"Image '{img}' not found on server")
        ext = os.path.splitext(image_path)[1]
        with open(image_path, "rb") as f:
            file_content = f.read()
    elif file:
        ext = os.path.splitext(file.filename)[1]
        # Read uploaded file content
        file_content = file.file.read()
    else:
        raise HTTPException(status_code=400, detail="Provide either a file upload or 'img' query parameter")
    uid = str(uuid.uuid4())
    original_filename = f"{uid}{ext}"
    predicted_filename = f"{uid}{ext}"

    # Upload original image to S3
    original_s3_url = upload_image_to_s3(file_content, "original", original_filename)
    
    # Create temporary file for YOLO processing
    temp_original_path = os.path.join(UPLOAD_DIR, original_filename)
    temp_predicted_path = os.path.join(PREDICTED_DIR, predicted_filename)
    
    # Save to temp file for YOLO processing
    with open(temp_original_path, "wb") as f:
        f.write(file_content)

    # Run YOLO prediction
    results = model(temp_original_path, device="cpu")

    # Generate predicted image
    annotated_frame = results[0].plot()  # NumPy image with boxes
    annotated_image = Image.fromarray(annotated_frame)
    annotated_image.save(temp_predicted_path)
    
    # Read predicted image and upload to S3
    with open(temp_predicted_path, "rb") as f:
        predicted_content = f.read()
    predicted_s3_url = upload_image_to_s3(predicted_content, "predicted", predicted_filename)

    # Save to database with S3 URLs
    new_session = query_save_prediction_session(db, uid, original_s3_url, predicted_s3_url, user_id)
    
    detected_labels = []
    for box in results[0].boxes:
        label_idx = int(box.cls[0].item())
        label = model.names[label_idx]
        score = float(box.conf[0])
        bbox = box.xyxy[0].tolist()
        new_detection = query_save_detection_object(db, uid, label, score, bbox)
        detected_labels.append(label)

    # Clean up temporary files
    try:
        os.remove(temp_original_path)
        os.remove(temp_predicted_path)
    except OSError:
        pass  # Files might not exist

    processing_time = round(time.time() - start_time, 2)

    return {
        "prediction_uid": uid, 
        "detection_count": len(results[0].boxes),
        "labels": detected_labels,
        "time_took": processing_time,
        "original_image_url": original_s3_url,
        "predicted_image_url": predicted_s3_url
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
        Delete original and predicted image files from S3
    """
    original_url, predicted_url = query_delete_prediction_by_uid(db, uid, user_id)

    # Delete files from S3
    if original_url:
        delete_file_from_s3(original_url)
    if predicted_url:
        delete_file_from_s3(predicted_url)

    return Response(status_code=status.HTTP_204_NO_CONTENT)