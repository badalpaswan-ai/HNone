from sqlalchemy import Column, Integer, String, Boolean

from app.db.session import Base


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

    role = Column(String)

    department = Column(String)

    skills = Column(String)

    max_workload = Column(
        Integer,
        default=5
    )

    is_available = Column(
        Boolean,
        default=True
    )

    is_active = Column(
        Boolean,
        default=True
    )

    current_workload = Column(
        Integer,
        default=0
    )
