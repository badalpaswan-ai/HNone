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

class TicketEvent(Base):

    __tablename__ = "ticket_events"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    ticket_id = Column(
        Integer,
        ForeignKey("tickets.id"),
        nullable=False
    )

    employee_id = Column(
        Integer,
        ForeignKey("employees.id")
    )

    event_type = Column(String)

    old_status = Column(String)

    new_status = Column(String)

    note = Column(Text)

    timestamp = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    ticket = relationship("Ticket")
