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


class EmployeeCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    department: Department
    role: str = Field(min_length=1, max_length=80)


class EmployeeResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    department: str
    role: str
    is_active: bool
    current_workload: int

    model_config = {
        "from_attributes": True
    }


class TicketResponse(BaseModel):
    id: int
    subject: str
    sender: EmailStr
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
    first_response_at: Optional[datetime]
    closed_at: Optional[datetime]
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }
