from fastapi import HTTPException, Request
import os
from fastapi.responses import FileResponse, Response
from dependencies.auth import resolve_user_id
from fastapi import Depends
from fastapi import APIRouter
from database.connections import get_db
from database.queries import query_predicted_image_by_uid
from utils.s3_utils import download_image_from_s3
from io import BytesIO
from sqlalchemy.orm import Session

router = APIRouter()

@router.get("/image/{type}/{filename}")
def get_image(type: str, filename: str, user_id: int = Depends(resolve_user_id)):
    """
    Get image by type and filename - now redirects to S3 URL
    This endpoint is deprecated in favor of direct S3 access
    """
    if type not in ["original", "predicted"]:
        raise HTTPException(status_code=400, detail="Invalid image type")
    
    # For backward compatibility, we'll try to serve from local files first
    # but this should be phased out in favor of direct S3 access
    path = os.path.join("uploads", type, filename)
    if os.path.exists(path):
        return FileResponse(path)
    else:
        raise HTTPException(status_code=404, detail="Image not found. Please use the prediction endpoints to get S3 URLs.")

@router.get("/prediction/{uid}/image")
def get_prediction_image(uid: str, request: Request, db: Session=Depends(get_db)):
    """
    Get prediction image by uid from S3
    """
    accept = request.headers.get("accept", "")
    image_url = query_predicted_image_by_uid(db, uid=uid)
    if not image_url:
        raise HTTPException(status_code=404, detail="Prediction not found")

    try:
        # Download image from S3
        image_data = download_image_from_s3(image_url)
        
        # Determine content type
        if "image/png" in accept:
            media_type = "image/png"
        elif "image/jpeg" in accept or "image/jpg" in accept:
            media_type = "image/jpeg"
        else:
            # Default to jpeg
            media_type = "image/jpeg"
        
        return Response(
            content=image_data.getvalue(),
            media_type=media_type
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve image: {str(e)}")
