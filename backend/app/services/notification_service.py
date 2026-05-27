from datetime import datetime, timedelta

from fastapi import HTTPException, status

from app.core.config import settings
from app.models.employee import Employee
from app.models.notification import Notification
from app.models.ticket import Ticket
from app.schemas import TicketStatus

MAIL_NOT_OPENED = "MAIL_NOT_OPENED"
MAIL_NOT_RESOLVED = "MAIL_NOT_RESOLVED"
RECIPIENT_EMPLOYEE = "employee"
RECIPIENT_MANAGER = "manager"
UNREAD = "unread"
READ = "read"


def create_mail_open_notifications(db, timeframe_seconds: int | None = None):
    timeframe = (
        settings.MAIL_OPEN_NOTIFICATION_SECONDS
        if timeframe_seconds is None
        else timeframe_seconds
    )
    cutoff = datetime.utcnow() - timedelta(seconds=timeframe)

    overdue_tickets = (
        db.query(Ticket)
        .filter(Ticket.assigned_employee_id.isnot(None))
        .filter(Ticket.assigned_at.isnot(None))
        .filter(Ticket.opened_at.is_(None))
        .filter(Ticket.assigned_at <= cutoff)
        .filter(Ticket.status != TicketStatus.closed.value)
        .all()
    )

    created = []

    for ticket in overdue_tickets:
        employee = (
            db.query(Employee)
            .filter(Employee.id == ticket.assigned_employee_id)
            .first()
        )

        created.extend(
            _create_ticket_notifications(
                db,
                ticket,
                employee,
                timeframe,
                MAIL_NOT_OPENED,
                "Assigned mail not opened",
                "opened"
            )
        )

    if created:
        db.commit()

    return created


def create_mail_resolve_notifications(db, timeframe_seconds: int | None = None):
    timeframe = (
        settings.MAIL_RESOLVE_NOTIFICATION_SECONDS
        if timeframe_seconds is None
        else timeframe_seconds
    )
    cutoff = datetime.utcnow() - timedelta(seconds=timeframe)

    overdue_tickets = (
        db.query(Ticket)
        .filter(Ticket.assigned_employee_id.isnot(None))
        .filter(Ticket.opened_at.isnot(None))
        .filter(Ticket.opened_at <= cutoff)
        .filter(Ticket.status != TicketStatus.closed.value)
        .all()
    )

    created = []

    for ticket in overdue_tickets:
        employee = (
            db.query(Employee)
            .filter(Employee.id == ticket.assigned_employee_id)
            .first()
        )

        created.extend(
            _create_ticket_notifications(
                db,
                ticket,
                employee,
                timeframe,
                MAIL_NOT_RESOLVED,
                "Opened mail not resolved",
                "resolved"
            )
        )

    if created:
        db.commit()

    return created


def create_due_notifications(db):
    return [
        *create_mail_open_notifications(db),
        *create_mail_resolve_notifications(db),
    ]


def list_notifications(
    db,
    recipient_role: str | None = None,
    employee_id: int | None = None,
    unread_only: bool = True,
):
    create_due_notifications(db)

    query = db.query(Notification)

    if recipient_role:
        query = query.filter(Notification.recipient_role == recipient_role)

    if employee_id:
        query = query.filter(Notification.employee_id == employee_id)

    if unread_only:
        query = query.filter(Notification.status == UNREAD)

    return (
        query
        .order_by(Notification.triggered_at.desc())
        .all()
    )


def mark_notification_read(db, notification_id: int):
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id)
        .first()
    )

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )

    notification.status = READ
    notification.read_at = datetime.utcnow()
    db.commit()
    db.refresh(notification)

    return notification


def _create_ticket_notifications(
    db,
    ticket,
    employee,
    timeframe,
    notification_type,
    title,
    action,
):
    created = []

    for recipient_role in (RECIPIENT_EMPLOYEE, RECIPIENT_MANAGER):
        exists = (
            db.query(Notification)
            .filter(Notification.ticket_id == ticket.id)
            .filter(Notification.employee_id == ticket.assigned_employee_id)
            .filter(Notification.recipient_role == recipient_role)
            .filter(Notification.notification_type == notification_type)
            .first()
        )

        if exists:
            continue

        employee_name = employee.name if employee else "assigned employee"
        message = (
            f"Ticket #{ticket.id} has not been {action} by {employee_name} "
            f"within {timeframe} seconds."
        )

        notification = Notification(
            ticket_id=ticket.id,
            employee_id=ticket.assigned_employee_id,
            recipient_role=recipient_role,
            notification_type=notification_type,
            title=title,
            message=message,
            status=UNREAD,
        )
        db.add(notification)
        created.append(notification)

    return created
