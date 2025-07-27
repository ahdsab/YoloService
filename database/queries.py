from sqlalchemy.orm import Session
from datetime import datetime


from models.PredictionSession_model import PredictionSession
from models.DetectionObjects_model import DetectionObject
from models.Users_model import Users

def query_get_prediction_by_uid(db: Session, uid: str):
    result = db.query(PredictionSession).filter_by(uid=uid).first()
    return result

def query_save_detection_object(db: Session, uid: str, original_image: str, predicted_image: str, user_id: int):
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
    new_detection = DetectionObjects(
        prediction_uid = prediction_uid,
        label = label,
        score = score,
        box = str(box)  # assuming you store the box as a stringified list like "[0,0,100,100]"
    )
    db.add(new_detection)
    db.commit()
    db.refresh(new_detection)
    return new_detection