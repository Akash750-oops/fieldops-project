from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette import status

from app.database import Base, engine
from app.routes import jobs, technicians, assignment
from app import models


app = FastAPI(
    title="FieldOps Commander API",
    description="Backend API for managing field operation jobs",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Globally format HTTP exceptions to {"error": "message"}
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()

    for err in errors:
        loc = err.get("loc", [])
        is_priority = "priority" in loc
        msg = err.get("msg", "")

        if is_priority or "Invalid priority value" in msg:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "Invalid priority value"}
            )

        if "Field cannot be empty" in msg:
            field = loc[-1] if loc else "field"
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": f"{str(field).replace('_', ' ').capitalize()} cannot be empty"
                }
            )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "Bad request",
            "detail": errors
        },
    )


Base.metadata.create_all(bind=engine)

app.include_router(jobs.router)
app.include_router(assignment.router)
app.include_router(technicians.router)


@app.get("/")
def home():
    return {
        "message": "FieldOps Commander API is running"
    }