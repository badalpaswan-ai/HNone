from app.database import SessionLocal
from app.models.employee import Employee

db = SessionLocal()

employees = [
    Employee(
        name="Rahul Sharma",
        email="rahul@company.com",
        department="sales",
        role="sales_exec"
    ),
    Employee(
        name="Priya Nair",
        email="priya@company.com",
        department="sales",
        role="sales_exec"
    ),
    Employee(
        name="Amit Verma",
        email="amit@company.com",
        department="operations",
        role="ops_exec"
    ),
    Employee(
        name="Fatima Khan",
        email="fatima@company.com",
        department="finance",
        role="finance_exec"
    ),
    Employee(
        name="Neha Rao",
        email="neha@company.com",
        department="customs",
        role="customs_exec"
    ),
    Employee(
        name="Vikram Singh",
        email="vikram@company.com",
        department="support",
        role="support_exec"
    ),
]

for employee in employees:
    exists = (
        db.query(Employee)
        .filter(Employee.email == employee.email)
        .first()
    )

    if not exists:
        db.add(employee)

db.commit()
db.close()
