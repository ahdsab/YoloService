from fastapi import HTTPException
import os
from fastapi.responses import FileResponse
from dependencies.auth import resolve_user_id
from fastapi import Depends
from fastapi import APIRouter

router = APIRouter()

@router.get("/image/{type}/{filename}")
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
