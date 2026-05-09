from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette import status

from app.database import Base, engine
from app.routes import jobs, technicians
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


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    
    # Check if this is our custom priority error or priority field error
    for err in errors:
        loc = err.get("loc", [])
        is_priority = "priority" in loc
        
        if is_priority or "Invalid priority value" in err.get("msg", ""):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "Invalid priority value"}
            )
            
        # Handle field_must_not_be_empty or other generic field errors
        if "Field cannot be empty" in err.get("msg", ""):
             field = loc[-1] if loc else "field"
             return JSONResponse(
                 status_code=status.HTTP_400_BAD_REQUEST,
                 content={"error": f"{field.replace('_', ' ').capitalize()} cannot be empty"}
             )

    # Fallback for other validation errors
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "message": "Bad request",
            "detail": errors
        },
    )


Base.metadata.create_all(bind=engine)

app.include_router(jobs.router)
app.include_router(technicians.router)


@app.get("/")
def home():
    return {
        "message": "FieldOps Commander API is running"
    }