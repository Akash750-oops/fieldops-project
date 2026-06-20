from fastapi import FastAPI, Request, HTTPException
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette import status

from .database import Base, engine
from .routes import jobs, technicians, assignment, planning, dispatch, notifications, in_app_notifications, templates, escalations, alerts, audit, dispatch_queue, dispatch_metrics
from . import models
from .services.justification_validator import JustificationValidationError
from .worker import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="FieldOps Commander API",
    description="Backend API for managing field operation jobs",
    version="1.0.0",
    lifespan=lifespan
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Globally format HTTP exceptions to {"error": "message"}
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(JustificationValidationError)
async def justification_validation_exception_handler(request: Request, exc: JustificationValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "VALIDATION_FAILED",
            "field": "justification",
            "message": exc.message,
            "current_length": exc.current_length,
            "min_length": exc.min_length,
            "max_length": exc.max_length
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    
    # Check if this is our custom priority error or priority field error
    for err in errors:
        loc = err.get("loc", [])
        is_priority = "priority" in loc
        msg = err.get("msg", "")
        
        if is_priority or "Invalid priority value" in msg:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "Invalid priority value"}
            )
            
        # Handle field_must_not_be_empty or other generic field errors
        if "Field cannot be empty" in msg:
             field = loc[-1] if loc else "field"
             return JSONResponse(
                 status_code=status.HTTP_400_BAD_REQUEST,
                 content={"error": f"{str(field).replace('_', ' ').capitalize()} cannot be empty"}
             )

    # Fallback for other validation errors
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "Bad request",
            "detail": errors
        },
    )


try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Warning: Could not create tables on startup: {e}")

app.include_router(jobs.router)
app.include_router(assignment.router)
app.include_router(dispatch.router)
app.include_router(technicians.router)
app.include_router(planning.router)
app.include_router(notifications.router)
app.include_router(in_app_notifications.router)
app.include_router(templates.router)
app.include_router(escalations.router)
app.include_router(alerts.router)
app.include_router(audit.router)
app.include_router(dispatch_queue.router)
app.include_router(dispatch_metrics.router)

from .services.socket_manager import sio_app
app.mount("/socket.io", sio_app)


# Lifespan events handled via asynccontextmanager lifespan handler


@app.get("/")
def home():
    return {
        "message": "FieldOps Commander backend is running"
    }