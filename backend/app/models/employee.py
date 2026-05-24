from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean
)

from app.database import Base

class Employee(Base):

    __tablename__ = "employees"

    id = Column(
        Integer,
        primary_key=True
    )

    name = Column(String)

    email = Column(
        String,
        unique=True
    )

    department = Column(String)

    role = Column(String)

    is_active = Column(
        Boolean,
        default=True
    )

    current_workload = Column(
        Integer,
        default=0
    )