from app.models.ticket import Ticket
from app.models.employee import Employee

def employee_metrics(db):

    employees = db.query(Employee).all()

    response = []

    for employee in employees:

        tickets = (
            db.query(Ticket)
            .filter(
                Ticket.assigned_employee_id == employee.id
            )
            .all()
        )

        assigned = len(tickets)

        closed = len([
            t for t in tickets
            if t.status == "CLOSED"
        ])

        response.append({
            "employee": employee.name,
            "department": employee.department,
            "assigned_tickets": assigned,
            "closed_tickets": closed,
            "current_workload": employee.current_workload
        })

    return response