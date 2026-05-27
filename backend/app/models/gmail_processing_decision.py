from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.db.session import Base


class GmailProcessingDecision(Base):

    __tablename__ = "gmail_processing_decisions"

    id = Column(
        Integer,
        primary_key=True
    )

    gmail_message_id = Column(
        String,
        unique=True,
        index=True,
        nullable=False
    )

    decision = Column(String)

    reason = Column(Text)

    ticket_id = Column(Integer)

    subject = Column(String)

    sender = Column(String)

    body = Column(Text)

    snippet = Column(Text)

    internal_date = Column(Integer)

    classification_json = Column(Text)

    welcome_sent_at = Column(DateTime)

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
