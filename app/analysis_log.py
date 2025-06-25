from datetime import datetime
from app import db
import uuid
 
class AnalysisLog(db.Model):
    __tablename__ = 'analysis_log'
 
    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    useremail = db.Column(db.String, nullable=False)
    analysis_id = db.Column(db.String, nullable=False, unique=True)
    data = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
 
    @classmethod
    def create(cls, useremail, analysis_id, data):
        log = cls(useremail=useremail, analysis_id=analysis_id, data=data)
        db.session.add(log)
        db.session.commit()
        return log
 
    @classmethod
    def update_by_analysis_id(cls, analysis_id, useremail=None, data=None):
        log = cls.query.filter_by(analysis_id=analysis_id).first()
        if not log:
            return None
        if useremail:
            log.useremail = useremail
        if data:
            log.data = data
        log.updated_at = datetime.utcnow()
        db.session.commit()
        return log