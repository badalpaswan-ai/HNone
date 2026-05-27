import asyncio

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.openapi import OPENAPI_TAGS, configure_openapi
from app.db.seed import seed_default_employees
from app.db.session import init_db
from app.services.gmail_scheduler import gmail_auto_check_loop, stop_gmail_auto_check


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        openapi_tags=OPENAPI_TAGS,
    )

    app.include_router(api_router)
    configure_openapi(app)

    @app.on_event("startup")
    async def startup():
        init_db()
        seed_default_employees()

        if settings.GMAIL_AUTO_CHECK_ENABLED:
            app.state.gmail_auto_check_task = asyncio.create_task(
                gmail_auto_check_loop()
            )

    @app.on_event("shutdown")
    async def shutdown():
        task = getattr(app.state, "gmail_auto_check_task", None)

        if task:
            await stop_gmail_auto_check(task)

    return app


app = create_app()
