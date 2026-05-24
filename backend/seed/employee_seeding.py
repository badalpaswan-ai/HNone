from app.database import SessionLocal
from app.models.employee import Employee

db = SessionLocal()

employees = [
    Employee(
        name="Rahul",
        email="rahul@company.com",
        department="sales",
        role="sales_exec"
    ),
    Employee(
        name="Priya",
        email="priya@company.com",
        department="sales",
        role="sales_exec"
    ),
    Employee(
        name="Amit",
        email="amit@company.com",
        department="operations",
        role="ops_exec"
    ),
]

db.add_all(employees)

db.commit()