PRIORITY_SKILLS = {
    "URGENT": {"urgent", "escalation", "vip"},
    "HIGH": {"high_priority", "escalation"},
}


from email.utils import parseaddr

from app.models.employee import Employee
from app.models.ticket import Ticket


def smart_assign(db, department, intent=None, priority=None, sender=None):
    employees = (
        db.query(Employee)
        .filter(
            Employee.department == department,
            Employee.is_active == True,
            Employee.is_available == True
        )
        .all()
    )

    employees = [
        employee for employee in employees
        if (employee.current_workload or 0) < (employee.max_workload or 5)
    ]

    if not employees:
        return None

    continuity_employee_id = _conversation_employee_id(db, department, sender)

    return sorted(
        employees,
        key=lambda employee: (
            0 if employee.id == continuity_employee_id else 1,
            _skill_penalty(employee, intent, priority),
            employee.current_workload or 0,
            employee.id,
        ),
    )[0]


def _conversation_employee_id(db, department, sender):
    normalized_sender = _normalize_email(sender)

    if not normalized_sender:
        return None

    tickets = (
        db.query(Ticket)
        .filter(Ticket.department == department)
        .filter(Ticket.assigned_employee_id.isnot(None))
        .filter(Ticket.opened_at.isnot(None))
        .order_by(Ticket.opened_at.desc())
        .limit(25)
        .all()
    )

    for ticket in tickets:
        if _normalize_email(ticket.sender) == normalized_sender:
            return ticket.assigned_employee_id

    return None


def _normalize_email(value):
    if not value:
        return None

    _, address = parseaddr(str(value))
    return (address or str(value)).strip().lower() or None


def _skill_penalty(employee, intent=None, priority=None):
    skills = {
        skill.strip().lower()
        for skill in (employee.skills or "").split(",")
        if skill.strip()
    }

    if not skills:
        return 1

    desired = {
        value.lower()
        for value in (intent, employee.department)
        if value
    }
    desired.update(PRIORITY_SKILLS.get(priority or "", set()))

    return 0 if skills.intersection(desired) else 1


def increment_workload(employee):
    if not employee:
        return None

    employee.current_workload = (employee.current_workload or 0) + 1
    return employee


def decrement_workload(employee):
    if not employee:
        return None

    employee.current_workload = max((employee.current_workload or 0) - 1, 0)
    return employee
