from fastapi import Depends
from fastapi import APIRouter
from database.queries import *
from database.connections import get_db

router = APIRouter()

@router.get("/labels")
def get_unique_labels_last_week(db: Session=Depends(get_db)):
    """
    Return all unique object labels detected in the last 7 days
    """
    labels = query_unique_labels_last_7_days(db)
    return {"labels": labels}