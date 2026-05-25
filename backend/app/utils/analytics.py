from app.models.ticket import Ticket
from app.models.employee import Employee

ACTIVE_STATUSES = {
    "NEW",
    "ASSIGNED",
    "IN_PROGRESS",
    "WAITING_CUSTOMER",
    "ESCALATED"
}


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


def dashboard_metrics(db):
    tickets = db.query(Ticket).all()

    by_status = {}
    by_priority = {}
    by_department = {}

    for ticket in tickets:
        by_status[ticket.status] = by_status.get(ticket.status, 0) + 1
        by_priority[ticket.priority] = by_priority.get(ticket.priority, 0) + 1
        by_department[ticket.department] = by_department.get(ticket.department, 0) + 1

    active_tickets = [
        ticket for ticket in tickets
        if ticket.status in ACTIVE_STATUSES
    ]

    return {
        "total_tickets": len(tickets),
        "active_tickets": len(active_tickets),
        "closed_tickets": by_status.get("CLOSED", 0),
        "unassigned_tickets": len([
            ticket for ticket in tickets
            if ticket.assigned_employee_id is None
        ]),
        "by_status": by_status,
        "by_priority": by_priority,
        "by_department": by_department
    }
