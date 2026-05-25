from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}
    if settings.DATABASE_URL.startswith("sqlite")
    else {}
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)

Base = declarative_base()

REQUIRED_COLUMNS = {
    "employees": {
        "id",
        "name",
        "email",
        "department",
        "role",
        "is_active",
        "current_workload"
    },
    "tickets": {
        "id",
        "subject",
        "sender",
        "body",
        "intent",
        "department",
        "priority",
        "status",
        "customer_name",
        "origin",
        "destination",
        "assigned_employee_id",
        "created_at",
        "assigned_at",
        "first_response_at",
        "closed_at",
        "updated_at"
    },
    "ticket_events": {
        "id",
        "ticket_id",
        "employee_id",
        "event_type",
        "old_status",
        "new_status",
        "note",
        "timestamp"
    }
}


def init_db():
    import app.models.employee
    import app.models.ticket
    import app.models.ticket_event

    if (
        settings.DATABASE_URL.startswith("sqlite")
        and settings.RESET_INCOMPATIBLE_SQLITE_SCHEMA
        and _schema_is_incompatible()
    ):
        Base.metadata.drop_all(bind=engine)

    Base.metadata.create_all(bind=engine)


def _schema_is_incompatible():
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    for table_name, required_columns in REQUIRED_COLUMNS.items():
        if table_name not in existing_tables:
            continue

        existing_columns = {
            column["name"]
            for column in inspector.get_columns(table_name)
        }

        if not required_columns.issubset(existing_columns):
            return True

    return False
