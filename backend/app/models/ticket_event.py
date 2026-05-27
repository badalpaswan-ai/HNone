from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey
)

from datetime import datetime

from app.db.session import Base


class TicketEvent(Base):

    __tablename__ = "ticket_events"

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

    event_type = Column(String)

    old_status = Column(String)

    new_status = Column(String)

    note = Column(String)

    timestamp = Column(
        DateTime,
        default=datetime.utcnow
    )
