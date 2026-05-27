from dataclasses import dataclass

from fastapi import HTTPException, status

from app.core.security import ROLE_EMPLOYEE, ROLE_MANAGER, ROLE_SYSTEM
from app.models.employee import Employee
from app.models.ticket import Ticket


@dataclass
class AccessScope:
    role: str
    full_access: bool
    employee_id: int | None = None
    department: str | None = None


def resolve_access_scope(db, user) -> AccessScope:
    role = user["role"]

    if role == ROLE_SYSTEM:
        return AccessScope(role=role, full_access=True)

    employee = _find_employee_for_user(db, user)

    if role == ROLE_MANAGER:
        department = user.get("department") or (employee.department if employee else None)

        if not department:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Manager account is not linked to a department",
            )

        return AccessScope(
            role=role,
            full_access=False,
            employee_id=employee.id if employee else None,
            department=department,
        )

    if role == ROLE_EMPLOYEE:
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Employee account is not linked to an employee record",
            )

        return AccessScope(
            role=role,
            full_access=False,
            employee_id=employee.id,
            department=employee.department,
        )

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Invalid role: {role}",
    )


def apply_ticket_scope(query, scope: AccessScope):
    if scope.full_access:
        return query

    if scope.role == ROLE_MANAGER:
        return query.filter(Ticket.department == scope.department)

    return query.filter(Ticket.assigned_employee_id == scope.employee_id)


def apply_employee_scope(query, scope: AccessScope):
    if scope.full_access:
        return query

    if scope.role == ROLE_MANAGER:
        return query.filter(Employee.department == scope.department)

    return query.filter(Employee.id == scope.employee_id)


def ensure_ticket_access(ticket, scope: AccessScope):
    if scope.full_access:
        return

    if scope.role == ROLE_MANAGER and ticket.department == scope.department:
        return

    if scope.role == ROLE_EMPLOYEE and ticket.assigned_employee_id == scope.employee_id:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have access to this ticket",
    )


def ensure_employee_access(employee, scope: AccessScope):
    if scope.full_access:
        return

    if scope.role == ROLE_MANAGER and employee.department == scope.department:
        return

    if scope.role == ROLE_EMPLOYEE and employee.id == scope.employee_id:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have access to this employee",
    )


def _find_employee_for_user(db, user):
    lookup_values = [
        user.get("employee_email"),
        user.get("username"),
    ]

    for value in lookup_values:
        if not value:
            continue

        employee = (
            db.query(Employee)
            .filter(Employee.email == value)
            .first()
        )

        if employee:
            return employee

    return None
