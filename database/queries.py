from sqlalchemy.orm import Session
from sqlalchemy import distinct
from datetime import datetime, timedelta
from sqlalchemy import func
from collections import Counter


from models.PredictionSession_model import PredictionSession
from models.DetectionObjects_model import DetectionObject
from models.Users_model import Users

def query_get_prediction_by_uid(db: Session, uid: str, user_id: int):
    result = db.query(PredictionSession).filter_by(uid = uid, user_id = user_id).first()
    return result

def query_save_prediction_session(db: Session, uid: str, original_image: str, predicted_image: str, user_id: int):
    new_session = PredictionSession(
        uid = uid,
        timestamp = datetime.utcnow(),  # only if not handled by default in the model
        original_image = original_image,
        predicted_image = predicted_image,
        user_id = user_id
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session

def query_save_detection_object(db: Session, prediction_uid: str, label: str, score: float, box: list):
    new_detection = DetectionObject(
        prediction_uid = prediction_uid,
        label = label,
        score = score,
        box = str(box)  # assuming you store the box as a stringified list like "[0,0,100,100]"
    )
    db.add(new_detection)
    db.commit()
    db.refresh(new_detection)
    return new_detection

def query_get_detection_objects_by_prediction_uid(db: Session, uid: str):
    return db.query(DetectionObject).filter_by(prediction_uid=uid).all()

def query_prediction_uids_by_label_and_user(db: Session, label: str, user_id: int):
    results = (
        db.query(distinct(PredictionSession.uid), PredictionSession.timestamp)
        .join(DetectionObject, DetectionObject.prediction_uid == PredictionSession.uid)
        .filter(
            DetectionObject.label == label,
            PredictionSession.user_id == user_id
        )
        .all()
    )
    return [{"uid": uid, "timestamp": timestamp} for uid, timestamp in results]

def query_prediction_sessions_by_min_score(db: Session, min_score: float, user_id: int):
    results = (
        db.query(distinct(PredictionSession.uid), PredictionSession.timestamp)
        .join(DetectionObject, DetectionObject.prediction_uid == PredictionSession.uid)
        .filter(
            DetectionObject.score >= min_score,
            PredictionSession.user_id == user_id
        )
        .all()
    )
    return [{"uid": uid, "timestamp": timestamp} for uid, timestamp in results]

def query_predicted_image_by_uid(db: Session, uid: str):
    result = (
        db.query(PredictionSession.predicted_image)
        .filter(PredictionSession.uid == uid)
        .first()
    )
    return result[0] if result else None

def query_total_predictions_last_week(db: Session):
    one_week_ago = datetime.utcnow() - timedelta(days=7)
    count = (
        db.query(PredictionSession)
        .filter(PredictionSession.timestamp >= one_week_ago)
        .count()
    )
    return {"count": count}

def query_delete_prediction_by_uid(db: Session, uid: str, user_id: int):
    """
    Deletes a prediction session and its detection objects from the DB.
    Returns the original and predicted image paths.
    Raises 404 if not found.
    """
    # Fetch prediction
    prediction = (
        db.query(PredictionSession)
        .filter(PredictionSession.uid == uid, PredictionSession.user_id == user_id)
        .first()
    )

    if not prediction:
        raise HTTPException(status_code=404, detail="Prediction not found")

    # Save image paths before deletion
    original_path = prediction.original_image
    predicted_path = prediction.predicted_image

    # Delete related detection objects
    db.query(DetectionObject).filter(DetectionObject.prediction_uid == uid).delete()

    # Delete prediction session
    db.delete(prediction)
    db.commit()

    return original_path, predicted_path

def query_unique_labels_last_7_days(db: Session):
    """
    Returns a list of unique detection labels from the last 7 days.
    """
    one_week_ago = datetime.utcnow() - timedelta(days=7)

    results = (
        db.query(distinct(DetectionObject.label))
        .join(PredictionSession, DetectionObject.prediction_uid == PredictionSession.uid)
        .filter(PredictionSession.timestamp >= one_week_ago)
        .all()
    )

    return [label for (label,) in results]  # Unpack tuples

def query_prediction_stats(db: Session, user_id: int):
    """
    Returns:
        - total_predictions: int
        - average_score: float
        - top_labels: List[Tuple[str, int]]
    """
    one_week_ago = datetime.utcnow() - timedelta(days=7)

    # Total predictions
    total_predictions = (
        db.query(func.count(PredictionSession.uid))
        .filter(
            PredictionSession.user_id == user_id,
            PredictionSession.timestamp >= one_week_ago
        )
        .scalar()
    )

    # All detection scores
    scores = (
        db.query(DetectionObject.score)
        .join(PredictionSession, DetectionObject.prediction_uid == PredictionSession.uid)
        .filter(
            PredictionSession.user_id == user_id,
            PredictionSession.timestamp >= one_week_ago
        )
        .all()
    )
    scores = [s[0] for s in scores]
    avg_score = round(sum(scores) / len(scores), 3) if scores else 0.0

    # Labels
    labels = (
        db.query(DetectionObject.label)
        .join(PredictionSession, DetectionObject.prediction_uid == PredictionSession.uid)
        .filter(
            PredictionSession.user_id == user_id,
            PredictionSession.timestamp >= one_week_ago
        )
        .all()
    )
    label_counts = Counter([l[0] for l in labels]).most_common(5)

    return total_predictions, avg_score, label_counts