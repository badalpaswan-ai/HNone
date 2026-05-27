from datetime import datetime, timedelta

from fastapi import HTTPException, status

from app.models.employee import Employee
from app.models.notification import Notification
from app.models.ticket import Ticket
from app.models.ticket_event import TicketEvent

from app.schemas import TicketStatus
from app.services.assignment_service import (
    decrement_workload,
    increment_workload,
    smart_assign
)

def create_ticket(db, payload, ai_result):

    employee = smart_assign(
        db,
        ai_result["department"],
        ai_result.get("intent"),
        ai_result.get("priority"),
        payload.sender
    )

    now = datetime.utcnow()
    ticket_status = (
        TicketStatus.assigned.value
        if employee
        else TicketStatus.new.value
    )

    ticket = Ticket(
        subject=payload.subject,
        sender=str(payload.sender),
        body=payload.body,

        intent=ai_result["intent"],

        department=ai_result["department"],

        priority=ai_result["priority"],

        status=ticket_status,

        customer_name=ai_result.get("customer_name"),

        origin=ai_result.get("origin"),

        destination=ai_result.get("destination"),

        assigned_employee_id=employee.id if employee else None,

        assigned_at=now if employee else None,

        sla_due_at=calculate_sla_due_at(now, ai_result["priority"])
    )

    if employee:
        increment_workload(employee)

    db.add(ticket)

    db.commit()

    db.refresh(ticket)

    event = TicketEvent(
        ticket_id=ticket.id,
        employee_id=employee.id if employee else None,
        event_type="ASSIGNMENT",
        new_status=ticket_status,
        note=(
            "Ticket assigned automatically"
            if employee
            else "No active employee available for department"
        )
    )

    db.add(event)

    db.commit()

    return ticket


def calculate_sla_due_at(started_at, priority):
    hours_by_priority = {
        "URGENT": 4,
        "HIGH": 12,
        "MEDIUM": 24,
        "LOW": 48,
    }
    return started_at + timedelta(hours=hours_by_priority.get(priority, 24))


def update_ticket_status(
    db,
    ticket_id,
    employee_id,
    requested_status,
    note=None
):

    ticket = (
        db.query(Ticket)
        .filter(
            Ticket.id == ticket_id
        )
        .first()
    )

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )

    employee = (
        db.query(Employee)
        .filter(Employee.id == employee_id)
        .first()
    )

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )

    new_status = (
        requested_status.value
        if hasattr(requested_status, "value")
        else requested_status
    )
    old_status = ticket.status

    ticket.status = new_status
    ticket.sla_breached = int(
        bool(ticket.sla_due_at and datetime.utcnow() > ticket.sla_due_at)
    )

    if new_status == TicketStatus.in_progress.value:

        if not ticket.first_response_at:
            ticket.first_response_at = datetime.utcnow()

    if (
        new_status == TicketStatus.closed.value
        and old_status != TicketStatus.closed.value
    ):
        closed_at = datetime.utcnow()
        ticket.closed_at = closed_at
        if ticket.assigned_employee:
            decrement_workload(ticket.assigned_employee)

        (
            db.query(Notification)
            .filter(Notification.ticket_id == ticket.id)
            .filter(Notification.notification_type.in_(["MAIL_NOT_OPENED", "MAIL_NOT_RESOLVED"]))
            .filter(Notification.status == "unread")
            .update(
                {
                    Notification.status: "read",
                    Notification.read_at: closed_at,
                },
                synchronize_session=False
            )
        )

    db.commit()

    event = TicketEvent(
        ticket_id=ticket.id,
        employee_id=employee_id,
        event_type="STATUS_CHANGE",
        old_status=old_status,
        new_status=new_status,
        note=note
    )

    db.add(event)

    db.commit()

    return ticket


def mark_ticket_opened(db, ticket_id, employee_id):
    ticket = get_ticket(db, ticket_id)

    if ticket.assigned_employee_id != employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ticket is not assigned to this employee"
        )

    employee = (
        db.query(Employee)
        .filter(Employee.id == employee_id)
        .first()
    )

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )

    if not ticket.opened_at:
        opened_at = datetime.utcnow()
        ticket.opened_at = opened_at

        event = TicketEvent(
            ticket_id=ticket.id,
            employee_id=employee_id,
            event_type="MAIL_OPENED",
            old_status=ticket.status,
            new_status=ticket.status,
            note="Assigned mail opened by employee"
        )
        db.add(event)

        (
            db.query(Notification)
            .filter(Notification.ticket_id == ticket.id)
            .filter(Notification.notification_type.in_(["MAIL_NOT_OPENED", "MAIL_NOT_RESOLVED"]))
            .filter(Notification.status == "unread")
            .update(
                {
                    Notification.status: "read",
                    Notification.read_at: opened_at,
                },
                synchronize_session=False
            )
        )

    db.commit()
    db.refresh(ticket)

    return ticket


def list_tickets(db, status_filter=None, department=None):
    query = db.query(Ticket)

    if status_filter:
        query = query.filter(Ticket.status == status_filter)

    if department:
        query = query.filter(Ticket.department == department)

    return (
        query
        .order_by(Ticket.created_at.desc())
        .all()
    )


def get_ticket(db, ticket_id):
    ticket = (
        db.query(Ticket)
        .filter(Ticket.id == ticket_id)
        .first()
    )

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )

    return ticket
