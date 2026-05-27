from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from datetime import datetime

from app.db.session import Base
from app.models.employee import Employee


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

    priority = Column(String)

    status = Column(String)

    department = Column(String)

    customer_name = Column(String)

    origin = Column(String)

    destination = Column(String)

    assigned_employee_id = Column(
        Integer,
        ForeignKey("employees.id")
    )

    assigned_employee = relationship(Employee)

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    assigned_at = Column(DateTime)

    opened_at = Column(DateTime)

    first_response_at = Column(DateTime)

    closed_at = Column(DateTime)

    sla_due_at = Column(DateTime)

    sla_breached = Column(
        Integer,
        default=0
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
