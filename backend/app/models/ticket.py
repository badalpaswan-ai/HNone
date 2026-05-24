from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey
)

from datetime import datetime

from app.database import Base

class Ticket(Base):

    __tablename__ = "tickets"

    id = Column(
        Integer,
        primary_key=True
    )

    subject = Column(String)

    sender = Column(String)

    body = Column(String)

    intent = Column(String)

    department = Column(String)

    priority = Column(String)

    status = Column(String)

    assigned_employee_id = Column(
        Integer,
        ForeignKey("employees.id")
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    assigned_at = Column(DateTime)

    first_response_at = Column(DateTime)

    closed_at = Column(DateTime)