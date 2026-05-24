from fastapi import FastAPI

from app.database import (
    Base,
    engine
)

from app.routes.ticket_routes import router

Base.metadata.create_all(
    bind=engine
)

app = FastAPI(
    title="Freight AI Operations POC"
)

app.include_router(router)

@app.get("/")
def health():

    return {
        "status": "running"
    }


if __name__ == '__main__':
    print("hello World")