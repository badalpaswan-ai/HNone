from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.db.session import Base


class ClassificationFeedback(Base):

    __tablename__ = "classification_feedback"

    id = Column(
        Integer,
        primary_key=True
    )

    ticket_id = Column(Integer)

    gmail_message_id = Column(String)

    original_intent = Column(String)

    original_department = Column(String)

    original_priority = Column(String)

    corrected_intent = Column(String)

    corrected_department = Column(String)

    corrected_priority = Column(String)

    note = Column(Text)

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )
