from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    String
)
from sqlalchemy.orm import relationship

from app.database import Base

class Employee(Base):

    __tablename__ = "employees"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    name = Column(
        String,
        nullable=False
    )

    email = Column(
        String,
        unique=True,
        nullable=False,
        index=True
    )

    department = Column(
        String,
        nullable=False,
        index=True
    )

    role = Column(
        String,
        nullable=False
    )

    is_active = Column(
        Boolean,
        default=True,
        nullable=False
    )

    current_workload = Column(
        Integer,
        default=0,
        nullable=False
    )

    tickets = relationship(
        "Ticket",
        back_populates="assigned_employee"
    )
