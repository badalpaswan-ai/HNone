<<<<<<< HEAD
from app.api.v1.endpoints.tickets import router

__all__ = ["router"]
=======
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.agents.freight_agent import classify_email
from app.database import SessionLocal
from app.models.employee import Employee
from app.models.ticket_event import TicketEvent
from app.schemas import (
    Department,
    EmployeeCreateRequest,
    EmployeeResponse,
    ProcessEmailRequest,
    StatusUpdateRequest,
    TicketResponse,
    TicketStatus
)
from app.services.ticket_service import (
    create_ticket,
    get_ticket,
    list_tickets,
    update_ticket_status
)
from app.utils.analytics import (
    dashboard_metrics,
    employee_metrics
)

router = APIRouter()


def get_db():
    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


@router.post("/process-email")
def process_email(
    payload: ProcessEmailRequest,
    db: Session = Depends(get_db)
):
    try:
        ai_result = classify_email(payload.body)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI classification failed: {exc}"
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


@router.get("/tickets", response_model=list[TicketResponse])
def tickets(
    status_filter: TicketStatus | None = None,
    department: Department | None = None,
    db: Session = Depends(get_db)
):
    return list_tickets(
        db,
        status_filter.value if status_filter else None,
        department.value if department else None
    )


@router.get("/tickets/{ticket_id}")
def ticket_detail(
    ticket_id: int,
    db: Session = Depends(get_db)
):
    ticket = get_ticket(db, ticket_id)

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


@router.put("/tickets/{ticket_id}/status")
def update_status(
    ticket_id: int,
    payload: StatusUpdateRequest,
    db: Session = Depends(get_db)
):
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


@router.get("/dashboard")
def dashboard(
    db: Session = Depends(get_db)
):
    return {
        "summary": dashboard_metrics(db),
        "recent_tickets": list_tickets(db)[:10]
    }


@router.get("/employee-metrics")
def metrics(
    db: Session = Depends(get_db)
):
    return employee_metrics(db)


@router.get("/employees", response_model=list[EmployeeResponse])
def employees(
    db: Session = Depends(get_db)
):
    return (
        db.query(Employee)
        .order_by(Employee.department.asc(), Employee.current_workload.asc())
        .all()
    )


@router.post(
    "/employees",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED
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
        is_active=True,
        current_workload=0
    )

    db.add(employee)
    db.commit()
    db.refresh(employee)

    return employee
>>>>>>> 8fb891641c9da45804261409e0f79589b417a299
