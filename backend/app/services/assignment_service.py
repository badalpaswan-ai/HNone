from app.models.employee import Employee

def smart_assign(db, department):

    employees = (
        db.query(Employee)
        .filter(
            Employee.department == department,
            Employee.is_active == True
        )
        .order_by(
            Employee.current_workload.asc()
        )
        .all()
    )

    if not employees:
        return None

    selected_employee = employees[0]

    selected_employee.current_workload += 1

    db.commit()

    return selected_employee