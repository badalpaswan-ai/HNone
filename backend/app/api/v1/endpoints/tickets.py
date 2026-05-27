from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.access import (
    apply_employee_scope,
    apply_ticket_scope,
    ensure_employee_access,
    ensure_ticket_access,
    resolve_access_scope,
)
from app.api.deps import get_db
from app.agents.freight_agent import classify_email
from app.core.security import (
    ROLE_EMPLOYEE,
    ROLE_MANAGER,
    require_roles,
)
from app.models.classification_feedback import ClassificationFeedback
from app.models.employee import Employee
from app.models.gmail_processing_decision import GmailProcessingDecision
from app.models.ticket import Ticket
from app.models.ticket_event import TicketEvent
from app.schemas import (
    ClassificationFeedbackRequest,
    Department,
    EmployeeCreateRequest,
    EmployeeTrackingUpdateRequest,
    EmployeeResponse,
    ProcessEmailRequest,
    StatusUpdateRequest,
    TicketOpenRequest,
    TicketResponse,
    TicketStatus
)
from app.services.ticket_service import (
    create_ticket,
    get_ticket,
    list_tickets,
    mark_ticket_opened,
    update_ticket_status
)
from app.utils.analytics import (
    admin_dashboard,
    dashboard_metrics,
    employee_dashboard,
    employee_metrics,
    individual_employee_dashboard,
    sla_dashboard
)

router = APIRouter()


@router.post(
    "/process-email",
    tags=["Email Intake"],
    summary="Classify an email and create a ticket",
)
def process_email(
    payload: ProcessEmailRequest,
    user=Depends(require_roles(ROLE_MANAGER)),
    db: Session = Depends(get_db)
):
    scope = resolve_access_scope(db, user)

    try:
        ai_result = classify_email(payload.body, subject=payload.subject)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI classification failed: {exc}"
        )

    if not scope.full_access and ai_result["department"] != scope.department:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Managers can only create tickets for their department"
        )

    try:
        ticket = create_ticket(
            db,
            payload,
            ai_result
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"AI result missing required field: {exc}"
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create ticket: {exc}"
        )

    return {
        "ticket_id": ticket.id,
        "intent": ticket.intent,
        "department": ticket.department,
        "priority": ticket.priority,
        "assigned_employee_id": ticket.assigned_employee_id,
        "status": ticket.status,
        "customer_name": ticket.customer_name,
        "origin": ticket.origin,
        "destination": ticket.destination
    }


@router.get(
    "/tickets",
    response_model=list[TicketResponse],
    tags=["Tickets"],
    summary="List tickets",
)
def tickets(
    status_filter: TicketStatus | None = None,
    department: Department | None = None,
    user=Depends(require_roles(ROLE_EMPLOYEE, ROLE_MANAGER)),
    db: Session = Depends(get_db)
):
    scope = resolve_access_scope(db, user)
    query = apply_ticket_scope(db.query(Ticket), scope)

    if status_filter:
        query = query.filter(Ticket.status == status_filter.value)

    if department:
        query = query.filter(Ticket.department == department.value)

    return (
        query
        .order_by(Ticket.created_at.desc())
        .all()
    )


@router.get(
    "/tickets/{ticket_id}",
    tags=["Tickets"],
    summary="Get ticket details and event history",
)
def ticket_detail(
    ticket_id: int,
    user=Depends(require_roles(ROLE_EMPLOYEE, ROLE_MANAGER)),
    db: Session = Depends(get_db)
):
    scope = resolve_access_scope(db, user)
    ticket = get_ticket(db, ticket_id)
    ensure_ticket_access(ticket, scope)

    events = (
        db.query(TicketEvent)
        .filter(TicketEvent.ticket_id == ticket_id)
        .order_by(TicketEvent.timestamp.asc())
        .all()
    )

    return {
        "ticket": TicketResponse.model_validate(ticket),
        "events": [
            {
                "id": event.id,
                "event_type": event.event_type,
                "old_status": event.old_status,
                "new_status": event.new_status,
                "employee_id": event.employee_id,
                "note": event.note,
                "timestamp": event.timestamp
            }
            for event in events
        ]
    }


@router.put(
    "/tickets/{ticket_id}/opened",
    tags=["Tickets"],
    summary="Mark an assigned mail as opened",
)
def mark_opened(
    ticket_id: int,
    payload: TicketOpenRequest,
    user=Depends(require_roles(ROLE_EMPLOYEE, ROLE_MANAGER)),
    db: Session = Depends(get_db)
):
    scope = resolve_access_scope(db, user)
    ticket_to_open = get_ticket(db, ticket_id)
    ensure_ticket_access(ticket_to_open, scope)
    employee = db.query(Employee).filter(Employee.id == payload.employee_id).first()

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )

    ensure_employee_access(employee, scope)

    if not scope.full_access and scope.role == ROLE_EMPLOYEE and payload.employee_id != scope.employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employees can only open their own assigned mail"
        )

    ticket = mark_ticket_opened(db, ticket_id, payload.employee_id)

    return {
        "ticket_id": ticket.id,
        "opened_at": ticket.opened_at,
    }


@router.put(
    "/tickets/{ticket_id}/status",
    tags=["Tickets"],
    summary="Update ticket status",
)
def update_status(
    ticket_id: int,
    payload: StatusUpdateRequest,
    user=Depends(require_roles(ROLE_EMPLOYEE, ROLE_MANAGER)),
    db: Session = Depends(get_db)
):
    scope = resolve_access_scope(db, user)
    ticket_to_update = get_ticket(db, ticket_id)
    ensure_ticket_access(ticket_to_update, scope)
    employee = db.query(Employee).filter(Employee.id == payload.employee_id).first()

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )

    ensure_employee_access(employee, scope)

    if not scope.full_access and scope.role == ROLE_EMPLOYEE and payload.employee_id != scope.employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employees can only update their own assigned tickets"
        )

    ticket = update_ticket_status(
        db,
        ticket_id,
        payload.employee_id,
        payload.status,
        payload.note
    )

    return {
        "ticket_id": ticket.id,
        "new_status": ticket.status
    }


@router.get(
    "/dashboard",
    tags=["Dashboards"],
    summary="Get the main operations dashboard",
)
def dashboard(
    user=Depends(require_roles(ROLE_EMPLOYEE, ROLE_MANAGER)),
    db: Session = Depends(get_db)
):
    scope = resolve_access_scope(db, user)

    if not scope.full_access:
        return _scoped_dashboard(db, scope)

    return {
        "summary": dashboard_metrics(db),
        "recent_tickets": list_tickets(db)[:10]
    }


@router.get(
    "/system/dashboard",
    tags=["Dashboards"],
    summary="Get the system dashboard",
    dependencies=[Depends(require_roles())]
)
def system_dashboard(
    db: Session = Depends(get_db)
):
    return admin_dashboard(db)


@router.get(
    "/admin/dashboard",
    tags=["Dashboards"],
    summary="Get the system dashboard",
    dependencies=[Depends(require_roles())]
)
def admin_dashboard_compat(
    db: Session = Depends(get_db)
):
    return admin_dashboard(db)


@router.get(
    "/sla-dashboard",
    tags=["Dashboards"],
    summary="Get SLA risk and breach dashboard",
)
def sla(
    user=Depends(require_roles(ROLE_EMPLOYEE, ROLE_MANAGER)),
    db: Session = Depends(get_db)
):
    scope = resolve_access_scope(db, user)

    if not scope.full_access:
        return _scoped_sla_dashboard(db, scope)

    return sla_dashboard(db)


@router.get(
    "/employee-metrics",
    tags=["Dashboards"],
    summary="Get employee performance metrics",
)
def metrics(
    user=Depends(require_roles(ROLE_EMPLOYEE, ROLE_MANAGER)),
    db: Session = Depends(get_db)
):
    scope = resolve_access_scope(db, user)

    if not scope.full_access:
        return _scoped_employee_metrics(db, scope)

    return employee_metrics(db)


@router.get(
    "/employees/dashboard",
    tags=["Dashboards"],
    summary="Get employee workload dashboard",
)
def employees_dashboard(
    user=Depends(require_roles(ROLE_EMPLOYEE, ROLE_MANAGER)),
    db: Session = Depends(get_db)
):
    scope = resolve_access_scope(db, user)

    if not scope.full_access:
        return _scoped_employees_dashboard(db, scope)

    return employee_dashboard(db)


@router.get(
    "/employees/{employee_id}/dashboard",
    tags=["Dashboards"],
    summary="Get one employee dashboard",
)
def employee_detail_dashboard(
    employee_id: int,
    user=Depends(require_roles(ROLE_EMPLOYEE, ROLE_MANAGER)),
    db: Session = Depends(get_db)
):
    scope = resolve_access_scope(db, user)
    employee = db.query(Employee).filter(Employee.id == employee_id).first()

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )

    ensure_employee_access(employee, scope)
    dashboard_data = individual_employee_dashboard(db, employee_id)

    if not dashboard_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )

    return dashboard_data


@router.get(
    "/review-queue",
    tags=["Review Queue"],
    summary="List emails that need manager review",
)
def review_queue(
    user=Depends(require_roles(ROLE_MANAGER)),
    db: Session = Depends(get_db)
):
    scope = resolve_access_scope(db, user)
    query = (
        db.query(GmailProcessingDecision)
        .filter(GmailProcessingDecision.decision.in_(["not_accepted", "review_required"]))
    )

    if not scope.full_access:
        query = (
            query
            .join(Ticket, GmailProcessingDecision.ticket_id == Ticket.id)
            .filter(Ticket.department == scope.department)
        )

    decisions = query.order_by(GmailProcessingDecision.updated_at.desc()).all()

    return {
        "count": len(decisions),
        "items": [
            {
                "id": decision.id,
                "gmail_message_id": decision.gmail_message_id,
                "decision": decision.decision,
                "reason": decision.reason,
                "subject": decision.subject,
                "sender": decision.sender,
                "ticket_id": decision.ticket_id,
                "classification_json": decision.classification_json,
                "created_at": decision.created_at,
                "updated_at": decision.updated_at,
            }
            for decision in decisions
        ],
    }


@router.get(
    "/employees",
    response_model=list[EmployeeResponse],
    tags=["Employees"],
    summary="List employees",
)
def employees(
    user=Depends(require_roles(ROLE_EMPLOYEE, ROLE_MANAGER)),
    db: Session = Depends(get_db)
):
    scope = resolve_access_scope(db, user)
    return (
        apply_employee_scope(db.query(Employee), scope)
        .order_by(Employee.department.asc(), Employee.current_workload.asc())
        .all()
    )


@router.put(
    "/employees/{employee_id}/tracking",
    response_model=EmployeeResponse,
    tags=["Employees"],
    summary="Update employee capacity and availability",
)
def update_employee_tracking(
    employee_id: int,
    payload: EmployeeTrackingUpdateRequest,
    user=Depends(require_roles(ROLE_MANAGER)),
    db: Session = Depends(get_db)
):
    scope = resolve_access_scope(db, user)
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

    ensure_employee_access(employee, scope)

    for field in ("skills", "max_workload", "is_available", "is_active"):
        value = getattr(payload, field)

        if value is not None:
            setattr(employee, field, value)

    db.commit()
    db.refresh(employee)

    return employee


@router.post(
    "/employees",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Employees"],
    summary="Create an employee",
    dependencies=[Depends(require_roles())]
)
def create_employee(
    payload: EmployeeCreateRequest,
    db: Session = Depends(get_db)
):
    existing = (
        db.query(Employee)
        .filter(Employee.email == str(payload.email))
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Employee email already exists"
        )

    employee = Employee(
        name=payload.name,
        email=str(payload.email),
        department=payload.department.value,
        role=payload.role,
        skills=payload.skills,
        max_workload=payload.max_workload,
        is_available=True,
        is_active=True,
        current_workload=0
    )

    db.add(employee)
    db.commit()
    db.refresh(employee)

    return employee


@router.post(
    "/classification-feedback",
    status_code=status.HTTP_201_CREATED,
    tags=["Feedback"],
    summary="Submit classification feedback",
)
def create_classification_feedback(
    payload: ClassificationFeedbackRequest,
    user=Depends(require_roles(ROLE_EMPLOYEE, ROLE_MANAGER)),
    db: Session = Depends(get_db)
):
    scope = resolve_access_scope(db, user)
    ticket = None

    if payload.ticket_id:
        ticket = get_ticket(db, payload.ticket_id)
        ensure_ticket_access(ticket, scope)

    feedback = ClassificationFeedback(
        ticket_id=payload.ticket_id,
        gmail_message_id=payload.gmail_message_id,
        original_intent=ticket.intent if ticket else None,
        original_department=ticket.department if ticket else None,
        original_priority=ticket.priority if ticket else None,
        corrected_intent=payload.corrected_intent,
        corrected_department=payload.corrected_department.value,
        corrected_priority=payload.corrected_priority.value,
        note=payload.note,
    )

    db.add(feedback)

    if ticket:
        ticket.intent = payload.corrected_intent
        ticket.department = payload.corrected_department.value
        ticket.priority = payload.corrected_priority.value

        event = TicketEvent(
            ticket_id=ticket.id,
            event_type="CLASSIFICATION_FEEDBACK",
            old_status=ticket.status,
            new_status=ticket.status,
            note="Classification corrected by human feedback"
        )
        db.add(event)

    db.commit()
    db.refresh(feedback)

    return {
        "feedback_id": feedback.id,
        "ticket_id": feedback.ticket_id,
        "gmail_message_id": feedback.gmail_message_id,
        "corrected_intent": feedback.corrected_intent,
        "corrected_department": feedback.corrected_department,
        "corrected_priority": feedback.corrected_priority,
    }


def _scoped_dashboard(db, scope):
    tickets = apply_ticket_scope(db.query(Ticket), scope).all()
    active = [ticket for ticket in tickets if ticket.status != TicketStatus.closed.value]
    closed = [ticket for ticket in tickets if ticket.status == TicketStatus.closed.value]

    return {
        "summary": {
            "total_tickets": len(tickets),
            "active_tickets": len(active),
            "closed_tickets": len(closed),
            "assigned_tickets": len([
                ticket for ticket in tickets
                if ticket.assigned_employee_id is not None
            ]),
        },
        "recent_tickets": sorted(
            tickets,
            key=lambda ticket: ticket.created_at,
            reverse=True,
        )[:10],
    }


def _scoped_sla_dashboard(db, scope):
    tickets = apply_ticket_scope(db.query(Ticket), scope).all()
    active = [ticket for ticket in tickets if ticket.status != TicketStatus.closed.value]
    breached = [
        ticket for ticket in active
        if ticket.sla_due_at and ticket.sla_due_at < datetime.utcnow()
    ]

    return {
        "summary": {
            "active_tickets": len(active),
            "breached_tickets": len(breached),
        },
        "breached_tickets": breached,
    }


def _scoped_employee_metrics(db, scope):
    employees = apply_employee_scope(db.query(Employee), scope).all()
    rows = []

    for employee in employees:
        tickets = (
            db.query(Ticket)
            .filter(Ticket.assigned_employee_id == employee.id)
            .all()
        )
        rows.append({
            "employee": employee.name,
            "department": employee.department,
            "assigned_tickets": len(tickets),
            "closed_tickets": len([
                ticket for ticket in tickets
                if ticket.status == TicketStatus.closed.value
            ]),
            "current_workload": employee.current_workload,
        })

    return rows


def _scoped_employees_dashboard(db, scope):
    employees = apply_employee_scope(db.query(Employee), scope).all()
    employee_ids = [employee.id for employee in employees]
    tickets = (
        db.query(Ticket)
        .filter(Ticket.assigned_employee_id.in_(employee_ids))
        .all()
        if employee_ids
        else []
    )

    return {
        "summary": {
            "total_employees": len(employees),
            "active_employees": len([
                employee for employee in employees
                if employee.is_active
            ]),
            "assigned_active_tickets": len([
                ticket for ticket in tickets
                if ticket.status != TicketStatus.closed.value
            ]),
        },
        "employees": employees,
    }
