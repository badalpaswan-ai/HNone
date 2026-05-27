import base64
import hashlib
import hmac
import json
import time

from fastapi import Header, HTTPException, status

from app.core.config import settings

ROLE_SYSTEM = "system"
ROLE_MANAGER = "manager"
ROLE_EMPLOYEE = "employee"

VALID_ROLES = {
    ROLE_SYSTEM,
    ROLE_MANAGER,
    ROLE_EMPLOYEE,
}

ROLE_DESCRIPTIONS = {
    ROLE_SYSTEM: "Full access to operational, employee, Gmail, review, and feedback APIs.",
    ROLE_MANAGER: "Can manage department work, employees, tickets, review queues, dashboards, and Gmail processing.",
    ROLE_EMPLOYEE: "Can view assigned work context and update ticket status or classification feedback.",
}

ENDPOINT_ROLE_MAP = {
    "Public": [
        "GET /",
        "POST /auth/login",
        "GET /auth/me",
        "GET /rbac/endpoints",
    ],
    "Employee": [
        "GET /tickets",
        "GET /tickets/{ticket_id}",
        "PUT /tickets/{ticket_id}/opened",
        "GET /dashboard",
        "GET /sla-dashboard",
        "GET /employee-metrics",
        "GET /employees/dashboard",
        "GET /employees/{employee_id}/dashboard",
        "GET /employees",
        "GET /notifications",
        "PUT /notifications/{notification_id}/read",
        "PUT /tickets/{ticket_id}/status",
        "POST /classification-feedback",
    ],
    "Manager": [
        "POST /process-email",
        "GET /review-queue",
        "PUT /employees/{employee_id}/tracking",
        "GET /gmail/unread",
        "POST /gmail/process-unread",
        "GET /gmail/processed",
        "GET /gmail/query",
        "POST /notifications/check-due",
        "POST /notifications/check-mail-open",
        "POST /notifications/check-mail-resolve",
    ],
    "System": [
        "GET /system/dashboard",
        "GET /admin/dashboard",
        "POST /employees",
    ],
}

DEMO_USERS = {
    "system": {
        "password": "system123",
        "role": ROLE_SYSTEM,
        "display_name": "System User",
    },
    "manager": {
        "password": "manager123",
        "role": ROLE_MANAGER,
        "display_name": "Operations Manager",
        "department": "operations",
    },
    "employee": {
        "password": "employee123",
        "role": ROLE_EMPLOYEE,
        "display_name": "Employee User",
        "employee_email": "rahul@company.com",
    },
}


def authenticate_user(username: str, password: str):
    user = DEMO_USERS.get(username.strip().lower())

    if not user:
        return None

    if not hmac.compare_digest(user["password"], password):
        return None

    return {
        "username": username.strip().lower(),
        "role": user["role"],
        "display_name": user["display_name"],
        "employee_email": user.get("employee_email"),
        "department": user.get("department"),
    }


def create_access_token(user: dict):
    now = int(time.time())
    expires_at = now + settings.JWT_EXPIRE_MINUTES * 60
    payload = {
        "sub": user["username"],
        "role": user["role"],
        "name": user.get("display_name"),
        "employee_email": user.get("employee_email"),
        "department": user.get("department"),
        "iat": now,
        "exp": expires_at,
    }

    return _encode_jwt(payload), expires_at


def get_current_user(
    authorization: str | None = Header(default=None, alias="Authorization")
):
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    token = _extract_bearer_token(authorization)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization must be Bearer token",
        )

    return _decode_jwt(token)


def require_roles(*allowed_roles):
    allowed = set(allowed_roles)

    def dependency(
        authorization: str | None = Header(default=None, alias="Authorization")
    ):
        user = get_current_user(authorization)
        role = user["role"]

        if role not in VALID_ROLES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Invalid role: {role}",
            )

        if role == ROLE_SYSTEM or role in allowed:
            return user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{role}' is not allowed for this endpoint",
        )

    return dependency


def _extract_bearer_token(authorization: str):
    value = authorization.strip()

    if not value:
        return None

    # Swagger's HTTP bearer dialog expects the raw token only. If someone pastes
    # "Bearer <token>" there, the actual header becomes "Bearer Bearer <token>".
    while value.lower().startswith("bearer "):
        value = value[7:].strip()

    if value.count(".") == 2:
        return value

    return None


def _encode_jwt(payload: dict):
    header = {
        "alg": "HS256",
        "typ": "JWT",
    }
    header_b64 = _b64encode_json(header)
    payload_b64 = _b64encode_json(payload)
    signature = _sign(f"{header_b64}.{payload_b64}")
    return f"{header_b64}.{payload_b64}.{signature}"


def _decode_jwt(token: str):
    parts = token.split(".")

    if len(parts) != 3:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    header_b64, payload_b64, signature = parts
    expected_signature = _sign(f"{header_b64}.{payload_b64}")

    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token signature",
        )

    try:
        payload = json.loads(_b64decode(payload_b64))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        ) from exc

    if int(payload.get("exp", 0)) < int(time.time()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )

    role = str(payload.get("role") or "").lower()

    if role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token role",
        )

    return {
        "username": payload.get("sub"),
        "role": role,
        "display_name": payload.get("name"),
        "employee_email": payload.get("employee_email"),
        "department": payload.get("department"),
        "expires_at": payload.get("exp"),
    }


def _sign(value: str):
    digest = hmac.new(
        settings.JWT_SECRET_KEY.encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return _b64encode(digest)


def _b64encode_json(value: dict):
    return _b64encode(
        json.dumps(value, separators=(",", ":")).encode("utf-8")
    )


def _b64encode(value: bytes):
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str):
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding).decode("utf-8")


def rbac_metadata():
    return {
        "roles": ROLE_DESCRIPTIONS,
        "endpoint_groups": ENDPOINT_ROLE_MAP,
        "auth_header": "Authorization: Bearer <token>",
        "login_endpoint": "POST /auth/login",
        "example": {
            "Authorization": "Bearer <token>",
        },
        "demo_users": {
            username: {
                "role": user["role"],
                "password": user["password"],
            }
            for username, user in DEMO_USERS.items()
        },
    }
