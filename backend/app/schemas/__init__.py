from datetime import datetime
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class Department(StrEnum):
    sales = "sales"
    operations = "operations"
    finance = "finance"
    customs = "customs"
    support = "support"


class TicketStatus(StrEnum):
    new = "NEW"
    assigned = "ASSIGNED"
    in_progress = "IN_PROGRESS"
    waiting_customer = "WAITING_CUSTOMER"
    escalated = "ESCALATED"
    closed = "CLOSED"


class Priority(StrEnum):
    low = "LOW"
    medium = "MEDIUM"
    high = "HIGH"
    urgent = "URGENT"


class ProcessEmailRequest(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    sender: EmailStr
    body: str = Field(min_length=1)


class StatusUpdateRequest(BaseModel):
    employee_id: int = Field(gt=0)
    status: TicketStatus
    note: Optional[str] = Field(default=None, max_length=500)


class TicketOpenRequest(BaseModel):
    employee_id: int = Field(gt=0)


class EmployeeCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    department: Department
    role: str = Field(min_length=1, max_length=80)
    skills: Optional[str] = Field(default=None, max_length=500)
    max_workload: int = Field(default=5, ge=1, le=100)


class EmployeeResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    department: str
    role: str
    skills: Optional[str] = None
    max_workload: Optional[int] = 5
    is_available: Optional[bool] = True
    is_active: bool
    current_workload: int

    model_config = {
        "from_attributes": True
    }


class TicketResponse(BaseModel):
    id: int
    subject: str
    sender: EmailStr
    body: Optional[str] = None
    intent: str
    department: str
    priority: str
    status: str
    customer_name: Optional[str]
    origin: Optional[str]
    destination: Optional[str]
    assigned_employee_id: Optional[int]
    created_at: datetime
    assigned_at: Optional[datetime]
    opened_at: Optional[datetime] = None
    first_response_at: Optional[datetime]
    closed_at: Optional[datetime]
    sla_due_at: Optional[datetime] = None
    sla_breached: Optional[int] = 0
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }


class EmployeeTrackingUpdateRequest(BaseModel):
    skills: Optional[str] = Field(default=None, max_length=500)
    max_workload: Optional[int] = Field(default=None, ge=1, le=100)
    is_available: Optional[bool] = None
    is_active: Optional[bool] = None


class ClassificationFeedbackRequest(BaseModel):
    ticket_id: Optional[int] = Field(default=None, gt=0)
    gmail_message_id: Optional[str] = Field(default=None, max_length=200)
    corrected_intent: str = Field(min_length=1, max_length=80)
    corrected_department: Department
    corrected_priority: Priority
    note: Optional[str] = Field(default=None, max_length=1000)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=120)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    role: str
    username: str


class NotificationResponse(BaseModel):
    id: int
    ticket_id: int
    employee_id: int
    recipient_role: str
    notification_type: str
    title: str
    message: str
    status: str
    triggered_at: datetime
    read_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True
    }
