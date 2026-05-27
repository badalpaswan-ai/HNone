from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from app.db.session import Base


class Notification(Base):

    __tablename__ = "notifications"

    id = Column(
        Integer,
        primary_key=True
    )

    ticket_id = Column(
        Integer,
        ForeignKey("tickets.id")
    )

    employee_id = Column(
        Integer,
        ForeignKey("employees.id")
    )

    recipient_role = Column(String)

    notification_type = Column(String)

    title = Column(String)

    message = Column(String)

    status = Column(
        String,
        default="unread"
    )

    triggered_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    read_at = Column(DateTime)
