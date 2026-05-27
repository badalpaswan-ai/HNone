from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

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
    import app.models.classification_feedback
    import app.models.department
    import app.models.employee
    import app.models.gmail_processing_decision
    import app.models.notification
    import app.models.ticket
    import app.models.ticket_event

    if (
        settings.DATABASE_URL.startswith("sqlite")
        and settings.RESET_INCOMPATIBLE_SQLITE_SCHEMA
        and _schema_is_incompatible()
    ):
        Base.metadata.drop_all(bind=engine)

    Base.metadata.create_all(bind=engine)
    _apply_sqlite_compat_migrations()


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


def _apply_sqlite_compat_migrations():
    if not settings.DATABASE_URL.startswith("sqlite"):
        return

    inspector = inspect(engine)

    migrations = {
        "gmail_processing_decisions.ticket_id": "INTEGER",
        "gmail_processing_decisions.body": "TEXT",
        "gmail_processing_decisions.snippet": "TEXT",
        "gmail_processing_decisions.internal_date": "INTEGER",
        "gmail_processing_decisions.welcome_sent_at": "DATETIME",
        "employees.skills": "VARCHAR",
        "employees.max_workload": "INTEGER DEFAULT 5",
        "employees.is_available": "BOOLEAN DEFAULT 1",
        "tickets.sla_due_at": "DATETIME",
        "tickets.sla_breached": "INTEGER DEFAULT 0",
        "tickets.opened_at": "DATETIME",
    }

    with engine.begin() as connection:
        for table_column, column_type in migrations.items():
            table_name, column_name = table_column.split(".", 1)

            if table_name not in inspector.get_table_names():
                continue

            table_columns = {
                column["name"]
                for column in inspector.get_columns(table_name)
            }

            if column_name not in table_columns:
                connection.exec_driver_sql(
                    f"ALTER TABLE {table_name} "
                    f"ADD COLUMN {column_name} {column_type}"
                )
