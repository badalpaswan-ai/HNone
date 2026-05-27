from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.access import resolve_access_scope
from app.api.deps import get_db
from app.core.security import ROLE_EMPLOYEE, ROLE_MANAGER, require_roles
from app.models.notification import Notification
from app.models.ticket import Ticket
from app.schemas import NotificationResponse
from app.services.notification_service import (
    create_due_notifications,
    create_mail_open_notifications,
    create_mail_resolve_notifications,
    list_notifications,
    mark_notification_read,
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get(
    "",
    response_model=list[NotificationResponse],
    summary="List notification alerts",
)
def notifications(
    recipient_role: str | None = None,
    employee_id: int | None = None,
    unread_only: bool = True,
    user=Depends(require_roles(ROLE_EMPLOYEE, ROLE_MANAGER)),
    db: Session = Depends(get_db)
):
    scope = resolve_access_scope(db, user)

    if scope.full_access:
        return list_notifications(
            db,
            recipient_role=recipient_role,
            employee_id=employee_id,
            unread_only=unread_only,
        )

    if scope.role == ROLE_EMPLOYEE:
        employee_id = scope.employee_id
        recipient_role = ROLE_EMPLOYEE

    notifications = list_notifications(
        db,
        recipient_role=recipient_role,
        employee_id=employee_id,
        unread_only=unread_only,
    )

    if scope.role == ROLE_MANAGER:
        ticket_ids = [
            notification.ticket_id
            for notification in notifications
            if notification.ticket_id
        ]
        visible_ticket_ids = {
            ticket.id
            for ticket in (
                db.query(Ticket)
                .filter(Ticket.id.in_(ticket_ids))
                .filter(Ticket.department == scope.department)
                .all()
                if ticket_ids
                else []
            )
        }
        return [
            notification for notification in notifications
            if notification.ticket_id in visible_ticket_ids
        ]

    return notifications


@router.post(
    "/check-mail-open",
    response_model=list[NotificationResponse],
    summary="Create alerts for assigned mail that was not opened in time",
    dependencies=[Depends(require_roles(ROLE_MANAGER))]
)
def check_mail_open_notifications(
    timeframe_seconds: int | None = None,
    db: Session = Depends(get_db)
):
    return create_mail_open_notifications(db, timeframe_seconds)


@router.post(
    "/check-mail-resolve",
    response_model=list[NotificationResponse],
    summary="Create alerts for opened mail that was not resolved in time",
    dependencies=[Depends(require_roles(ROLE_MANAGER))]
)
def check_mail_resolve_notifications(
    timeframe_seconds: int | None = None,
    db: Session = Depends(get_db)
):
    return create_mail_resolve_notifications(db, timeframe_seconds)


@router.post(
    "/check-due",
    response_model=list[NotificationResponse],
    summary="Create alerts for all due mail notification rules",
    dependencies=[Depends(require_roles(ROLE_MANAGER))]
)
def check_due_notifications(
    db: Session = Depends(get_db)
):
    return create_due_notifications(db)


@router.put(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Mark a notification as read",
)
def read_notification(
    notification_id: int,
    user=Depends(require_roles(ROLE_EMPLOYEE, ROLE_MANAGER)),
    db: Session = Depends(get_db)
):
    scope = resolve_access_scope(db, user)

    if not scope.full_access:
        notification = (
            db.query(Notification)
            .filter(Notification.id == notification_id)
            .first()
        )

        if scope.role == ROLE_EMPLOYEE and (
            not notification
            or notification.employee_id != scope.employee_id
            or notification.recipient_role != ROLE_EMPLOYEE
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this notification"
            )

        if scope.role == ROLE_MANAGER:
            ticket = (
                db.query(Ticket)
                .filter(Ticket.id == notification.ticket_id)
                .first()
                if notification
                else None
            )

            if not ticket or ticket.department != scope.department:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have access to this notification"
                )

    return mark_notification_read(db, notification_id)
