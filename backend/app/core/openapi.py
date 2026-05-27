from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


OPENAPI_TAGS = [
    {
        "name": "System",
        "description": "Service health and operational metadata.",
    },
    {
        "name": "Authentication",
        "description": "Login and current-user profile endpoints.",
    },
    {
        "name": "Access Control",
        "description": "Role metadata and endpoint access reference.",
    },
    {
        "name": "Email Intake",
        "description": "Classify inbound freight emails and create tickets. Manager access required.",
    },
    {
        "name": "Tickets",
        "description": "View tickets, inspect ticket history, and update ticket status.",
    },
    {
        "name": "Dashboards",
        "description": "Operational, SLA, employee, and system reporting views.",
    },
    {
        "name": "Employees",
        "description": "Employee directory, capacity, availability, and workload management.",
    },
    {
        "name": "Gmail",
        "description": "Preview, query, audit, and process Gmail messages.",
    },
    {
        "name": "Review Queue",
        "description": "Manager review of rejected or low-confidence email processing decisions.",
    },
    {
        "name": "Feedback",
        "description": "Human corrections for AI classification output.",
    },
    {
        "name": "Notifications",
        "description": "Alerts for assigned mail that has not been opened within the configured timeframe.",
    },
]

PUBLIC_ENDPOINTS = {
    ("get", "/"),
    ("post", "/auth/login"),
    ("get", "/rbac/endpoints"),
}


def configure_openapi(app: FastAPI) -> None:
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema

        schema = get_openapi(
            title=app.title,
            version=app.version,
            routes=app.routes,
            tags=app.openapi_tags,
        )
        schema.setdefault("components", {}).setdefault("securitySchemes", {})[
            "BearerAuth"
        ] = {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }

        for path, path_item in schema.get("paths", {}).items():
            for method, operation in path_item.items():
                if not isinstance(operation, dict):
                    continue

                if (method.lower(), path) not in PUBLIC_ENDPOINTS:
                    operation["security"] = [{"BearerAuth": []}]

        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi
