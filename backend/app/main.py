from fastapi import FastAPI

from app.database import (
    init_db,
    SessionLocal
)
from app.config import settings
from app.models.employee import Employee

from app.routes.ticket_routes import router as ticket_router
from app.routes.gmail_routes import router as gmail_router

DEFAULT_EMPLOYEES = [
    {
        "name": "Rahul Sharma",
        "email": "rahul@company.com",
        "department": "sales",
        "role": "sales_exec"
    },
    {
        "name": "Priya Nair",
        "email": "priya@company.com",
        "department": "sales",
        "role": "sales_exec"
    },
    {
        "name": "Amit Verma",
        "email": "amit@company.com",
        "department": "operations",
        "role": "ops_exec"
    },
    {
        "name": "Fatima Khan",
        "email": "fatima@company.com",
        "department": "finance",
        "role": "finance_exec"
    },
    {
        "name": "Neha Rao",
        "email": "neha@company.com",
        "department": "customs",
        "role": "customs_exec"
    },
    {
        "name": "Vikram Singh",
        "email": "vikram@company.com",
        "department": "support",
        "role": "support_exec"
    }
]

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION
)

app.include_router(ticket_router)
app.include_router(gmail_router)


@app.on_event("startup")
def startup():
    init_db()
    seed_default_employees()


@app.get("/")
def health():

    return {
        "status": "running",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


def seed_default_employees():
    db = SessionLocal()

    try:
        for employee_data in DEFAULT_EMPLOYEES:
            existing = (
                db.query(Employee)
                .filter(Employee.email == employee_data["email"])
                .first()
            )

            if existing:
                continue

            db.add(Employee(**employee_data))

        db.commit()

    finally:
        db.close()
