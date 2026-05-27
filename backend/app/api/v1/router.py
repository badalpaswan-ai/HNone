from fastapi import APIRouter

from app.api.v1.endpoints import auth, gmail, notifications, system, tickets

api_router = APIRouter()
api_router.include_router(system.router)
api_router.include_router(auth.router)
api_router.include_router(tickets.router)
api_router.include_router(gmail.router)
api_router.include_router(notifications.router)
