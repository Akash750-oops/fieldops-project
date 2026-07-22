from fastapi import FastAPI, Request, HTTPException
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette import status
import os
import asyncio
import logging
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

from .database import SessionLocal
from .routes import jobs, technicians, assignment, planning, dispatch, notifications, in_app_notifications, templates, escalations, alerts, audit, dispatch_queue, dispatch_metrics, gps, admin_gps, eta, tracking,template_version_routes,brand_safety_admin,admin_prompts
from . import models
from .services.justification_validator import JustificationValidationError
from .worker import start_scheduler, stop_scheduler
from .services.tracking_manager import connection_manager
from .services.broadcast_scheduler import BroadcastScheduler
from .routes.tracking import redis_gps_listener
from .services.default_template import seed_default_templates

scheduler = None
redis_async_client = None
redis_pubsub_client = None
listener_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global scheduler, redis_async_client, redis_pubsub_client, listener_task
    start_scheduler()
    
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", 6379))
    
    try:
        redis_async_client = aioredis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        # Test the connection before proceeding
        await redis_async_client.ping()
        
        # Pubsub listener needs decode_responses=False since GPS payloads are MsgPack binary
        redis_pubsub_client = aioredis.Redis(host=redis_host, port=redis_port, decode_responses=False)
        await redis_pubsub_client.ping()
        
        listener_task = asyncio.create_task(redis_gps_listener(redis_pubsub_client))
        
        scheduler = BroadcastScheduler(
            db_factory=SessionLocal,
            redis_async=redis_async_client,
            manager=connection_manager
        )
        await scheduler.start()
        print("Redis connected successfully")
    except Exception as e:
        print(f"Redis not available ({e}). GPS broadcast & pub/sub features are disabled.")
        redis_async_client = None
        redis_pubsub_client = None
        listener_task = None
        scheduler = None
        
    # Seed default notification templates
    db = SessionLocal()
    try:
        seed_default_templates(db)
        print("Default notification templates seeded successfully.")
    except Exception as e:
        print(f"Failed to seed default templates: {e}")
    finally:
        db.close()

    try:
        from app.services.ai.FieldOpsAI.runtime.orchestrator import ai_orchestrator
        await ai_orchestrator.provider_health_monitor.start()
    except Exception:
        logger.warning("ProviderHealthMonitor failed to start.")

    try:
        yield
    finally:
        try:
            from app.services.ai.FieldOpsAI.runtime.orchestrator import ai_orchestrator
            await ai_orchestrator.provider_health_monitor.stop()
        except Exception:
            logger.warning("ProviderHealthMonitor failed to stop.")

        if scheduler:
            await scheduler.stop()
        if listener_task:
            listener_task.cancel()
            try:
                await listener_task
            except asyncio.CancelledError:
                pass
        if redis_async_client:
            await redis_async_client.aclose()
        if redis_pubsub_client:
            await redis_pubsub_client.aclose()

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

from .context import correlation_id_ctx
import uuid

@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    token = correlation_id_ctx.set(correlation_id)
    try:
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response
    finally:
        correlation_id_ctx.reset(token)



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
    
    sanitized_errors = []
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
                 content={"error": f"{str(field).replace('_', ' ').capitalize()} cannot be empty"}
              )
              
        sanitized_errors.append({
            "loc": err.get("loc"),
            "msg": err.get("msg"),
            "type": err.get("type")
        })

    # Fallback for other validation errors
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "Bad Request",
            "detail": sanitized_errors,
        },
    )



app.include_router(jobs.router)
app.include_router(jobs.api_v1_router)
app.include_router(assignment.router)
app.include_router(dispatch.router)
app.include_router(technicians.router)
app.include_router(planning.router)
app.include_router(notifications.router)
app.include_router(in_app_notifications.router)
app.include_router(template_version_routes.router)
app.include_router(templates.router)
app.include_router(escalations.router)
app.include_router(alerts.router)
app.include_router(audit.router)
app.include_router(dispatch_queue.router)
app.include_router(dispatch_metrics.router)
app.include_router(gps.router)
app.include_router(admin_gps.router)
app.include_router(eta.router)
app.include_router(tracking.router)
app.include_router(brand_safety_admin.router)
app.include_router(admin_prompts.router)

from .services.socket_manager import sio_app
app.mount("/socket.io", sio_app)


# Lifespan events handled via asynccontextmanager lifespan handler


@app.get("/")
def home():
    return {
        "message": "FieldOps Commander backend is running"
    }