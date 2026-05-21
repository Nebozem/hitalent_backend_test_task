from fastapi import FastAPI
from app.routers import departments
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI(title="hitalent_test")

app.include_router(departments.router, prefix="/departments", tags=["departments"])

@app.get("/")
def root():
    return {"message": "API is working"}