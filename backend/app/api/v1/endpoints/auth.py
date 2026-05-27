import time

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.security import (
    authenticate_user,
    create_access_token,
    get_current_user,
)
from app.models.employee import Employee
from app.schemas import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and receive a bearer token",
)
def login(payload: LoginRequest):
    user = authenticate_user(payload.username, payload.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token, expires_at = create_access_token(user)

    return {
        "access_token": token,
        "expires_in": int(max(expires_at - time.time(), 0)),
        "role": user["role"],
        "username": user["username"],
    }


@router.get(
    "/me",
    summary="Get the authenticated user profile",
)
def me(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _current_user_payload(user, db)


@router.get("/me/", include_in_schema=False)
def me_slash(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _current_user_payload(user, db)


def _current_user_payload(user, db):
    employee = _find_employee_for_user(user, db)

    return {
        **user,
        "employee": _employee_to_auth_dict(employee) if employee else None,
    }


def _find_employee_for_user(user, db):
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


def _employee_to_auth_dict(employee):
    return {
        "employee_id": employee.id,
        "name": employee.name,
        "email": employee.email,
        "department": employee.department,
        "role": employee.role,
        "skills": employee.skills,
        "is_active": employee.is_active,
        "is_available": employee.is_available,
        "current_workload": employee.current_workload,
        "max_workload": employee.max_workload,
    }
