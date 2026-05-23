from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette import status

from .database import Base, engine
from .routes import jobs, technicians, assignment, planning, dispatch, notifications, in_app_notifications, templates
from . import models


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


from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Globally format HTTP exceptions to {"error": "message"}
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": str(exc.detail)}
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
app.include_router(technicians.router)
app.include_router(planning.router)
app.include_router(dispatch.router)
app.include_router(notifications.router)
app.include_router(in_app_notifications.router)
app.include_router(templates.router)

from .services.socket_manager import sio_app
app.mount("/socket.io", sio_app)


from .worker import start_scheduler, stop_scheduler

@app.on_event("startup")
def on_startup():
    start_scheduler()

@app.on_event("shutdown")
def on_shutdown():
    stop_scheduler()


@app.get("/")
def home():
    return {
        "message": "FieldOps Commander backend is running"
    }