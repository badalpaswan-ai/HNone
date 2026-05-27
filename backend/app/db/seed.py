from app.db.session import SessionLocal
from app.models.employee import Employee

DEFAULT_EMPLOYEES = [
    {
        "name": "Rahul Sharma",
        "email": "rahul@company.com",
        "department": "sales",
        "role": "sales_exec",
    },
    {
        "name": "Priya Nair",
        "email": "priya@company.com",
        "department": "sales",
        "role": "sales_exec",
    },
    {
        "name": "Amit Verma",
        "email": "amit@company.com",
        "department": "operations",
        "role": "ops_exec",
    },
    {
        "name": "Fatima Khan",
        "email": "fatima@company.com",
        "department": "finance",
        "role": "finance_exec",
    },
    {
        "name": "Neha Rao",
        "email": "neha@company.com",
        "department": "customs",
        "role": "customs_exec",
    },
    {
        "name": "Vikram Singh",
        "email": "vikram@company.com",
        "department": "support",
        "role": "support_exec",
    },
]


def seed_default_employees() -> None:
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
