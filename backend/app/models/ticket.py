from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text
)
from sqlalchemy.orm import relationship

from datetime import datetime

from app.database import Base

class Ticket(Base):

    __tablename__ = "tickets"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    subject = Column(
        String,
        nullable=False
    )

    sender = Column(
        String,
        nullable=False,
        index=True
    )

    body = Column(
        Text,
        nullable=False
    )

    intent = Column(
        String,
        nullable=False,
        index=True
    )

    department = Column(
        String,
        nullable=False,
        index=True
    )

    priority = Column(
        String,
        nullable=False,
        index=True
    )

    status = Column(
        String,
        nullable=False,
        index=True
    )

    customer_name = Column(String)

    origin = Column(String)

    destination = Column(String)

    assigned_employee_id = Column(
        Integer,
        ForeignKey("employees.id"),
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    assigned_at = Column(DateTime)

    first_response_at = Column(DateTime)

    closed_at = Column(DateTime)

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    assigned_employee = relationship(
        "Employee",
        back_populates="tickets"
    )
