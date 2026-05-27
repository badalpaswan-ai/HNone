from sqlalchemy import (
    Column,
    Integer,
    String
)

from app.db.session import Base

class Department(Base):

    __tablename__ = "departments"

    id = Column(
        Integer,
        primary_key=True
    )

    name = Column(
        String,
        unique=True
    )

    description = Column(String)

    sla_hours = Column(Integer)

    escalation_email = Column(String)
