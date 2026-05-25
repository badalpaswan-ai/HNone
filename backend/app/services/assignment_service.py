from app.models.employee import Employee


def smart_assign(db, department_id):
    employees = (
        db.query(Employee)
        .filter(
            Employee.department == department_id,
            Employee.is_active == True
        )
        .order_by(Employee.current_workload.asc())
        .all()
    )

    if not employees:
        return None

    return employees[0]


def increment_workload(employee):
    if not employee:
        return None

    employee.current_workload = (employee.current_workload or 0) + 1
    return employee

    return employee


def decrement_workload(employee):
    if not employee:
        return None

    employee.current_workload = max((employee.current_workload or 0) - 1, 0)
    return employee