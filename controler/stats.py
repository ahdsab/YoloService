from fastapi import Depends
from fastapi import APIRouter
from database.queries import *
from database.connections import get_db
from dependencies.auth import resolve_user_id

router = APIRouter()

@router.get("/stats")
def get_prediction_stats(user_id: int = Depends(resolve_user_id), db: Session=Depends(get_db)):
    """
    Return analytics for predictions made in the last 7 days:
    - total number of predictions
    - average confidence score
    - most common labels
    """
    total, avg_score, label_counts = query_prediction_stats(db, user_id)

    return {
        "total_predictions": total,
        "average_confidence_score": avg_score,
        "most_common_labels": {label: count for label, count in label_counts}
    }