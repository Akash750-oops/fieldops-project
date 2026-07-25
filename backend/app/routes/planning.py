from fastapi import APIRouter, Depends, Header, Response, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone, timedelta
from typing import Optional

from ..database import get_db
from ..models import Job, Technician
from .. import schemas

from app.auth.dependencies import get_current_user_or_tenant, AuthenticatedUser

router = APIRouter(
    tags=["Planning"]
)

@router.get("/planned-assignments", response_model=list[schemas.PlannedAssignmentResponse])
def get_planned_assignments(
    response: Response,
    search: Optional[str] = None,
    page: Optional[int] = Query(None, ge=1),
    limit: Optional[int] = Query(None, ge=1),
    user_tenant: tuple[Optional[AuthenticatedUser], str] = Depends(get_current_user_or_tenant),
    db: Session = Depends(get_db)
):
    """
    Fetch all jobs that are assigned to a technician.
    """
    user, tenant_id = user_tenant
    query = db.query(
        Job.id.label("job_id"),
        Technician.technician_name.label("technician"),
        Technician.technician_skill.label("skill"),
        Job.customer_name.label("customer"),
        Job.location,
        Job.priority,
        Job.status,
        Technician.current_jobs,
        Technician.max_jobs
    ).join(Technician, Job.assigned_technician_id == Technician.technician_id)
    
    if not user or not user.is_super_admin:
        query = query.filter(Job.tenant_id == tenant_id)
        
    if search:
        search_pattern = f"%{search}%"
        id_filter = None
        try:
            id_val = int(search.replace("#", "").strip())
            id_filter = (Job.id == id_val)
        except ValueError:
            pass
            
        text_filters = (
            (Job.customer_name.ilike(search_pattern)) |
            (Technician.technician_name.ilike(search_pattern)) |
            (Technician.technician_skill.ilike(search_pattern)) |
            (Job.location.ilike(search_pattern)) |
            (Job.priority.ilike(search_pattern))
        )
        
        if id_filter is not None:
            query = query.filter(id_filter | text_filters)
        else:
            query = query.filter(text_filters)
            
    total_count = query.count()
    response.headers["X-Total-Count"] = str(total_count)
    response.headers["Access-Control-Expose-Headers"] = "X-Total-Count"
    
    query = query.order_by(Job.id.desc())
    if page and limit:
        query = query.offset((page - 1) * limit).limit(limit)
        
    return query.all()


@router.get("/planning/kpi")
def get_planning_kpi(
    user_tenant: tuple[Optional[AuthenticatedUser], str] = Depends(get_current_user_or_tenant),
    db: Session = Depends(get_db)
):
    """
    Return live KPI metrics for the Planning page dispatch cards.
    Counts are calculated from ALL jobs (not date-filtered) for always-meaningful numbers.
    Also provides yesterday-vs-today trend for jobs created today vs yesterday.
    """
    user, tenant_id = user_tenant
    now_utc = datetime.now(timezone.utc)
    today_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)

    # Base query - filter by tenant
    base = db.query(Job)
    if not user or not user.is_super_admin:
        base = base.filter(Job.tenant_id == tenant_id)

    today_q = base.filter(Job.created_at >= today_start)
    yesterday_q = base.filter(
        Job.created_at >= yesterday_start,
        Job.created_at < today_start
    )

    # --- ALL-TIME totals (for KPI cards - always meaningful) ---
    # Dispatched = jobs that have a technician actively assigned to them
    # NOTE: EXCLUDED_FROM_PENDING must match the statuses removed by normalPendingJobs
    # in the frontend (PlanningPage.tsx). ESCALATED jobs go to the SLA Escalations tab,
    # not the Pending Jobs tab, so they must be excluded from Pending/Expired/Re-Dispatched KPIs.
    EXCLUDED_FROM_PENDING = [
        "completed", "cancelled", "canceled",
        "COMPLETED", "CANCELLED", "CANCELED",
        "ESCALATED", "ESCALATED_TO_CTO"
    ]

    jobs_dispatched = base.filter(
        Job.assigned_technician_id.isnot(None)
    ).count()

    # Pending = unassigned jobs excluding terminal + escalated statuses
    jobs_pending = base.filter(
        Job.assigned_technician_id.is_(None),
        Job.status.notin_(EXCLUDED_FROM_PENDING)
    ).count()

    # Expired = unresolved, non-escalated jobs with SLA past due
    jobs_expired = base.filter(
        Job.sla_deadline.isnot(None),
        Job.sla_deadline < now_utc,
        Job.assigned_technician_id.is_(None),
        Job.status.notin_(EXCLUDED_FROM_PENDING)
    ).count()

    # Re-dispatched = unassigned, non-terminal, non-escalated jobs attempted more than once.
    # Must match /jobs/pending endpoint + normalPendingJobs frontend filter.
    jobs_redispatched = base.filter(
        Job.attempt_count > 1,
        Job.assigned_technician_id.is_(None),
        Job.status.notin_(EXCLUDED_FROM_PENDING)
    ).count()

    # --- TODAY vs YESTERDAY trend ---
    def count_today(q, filters):
        return today_q.filter(*filters).count() if filters else today_q.count()

    def count_yesterday(q, filters):
        return yesterday_q.filter(*filters).count() if filters else yesterday_q.count()

    # Today/yesterday dispatched (same corrected rules)
    t_dispatched = today_q.filter(Job.assigned_technician_id.isnot(None)).count()
    y_dispatched = yesterday_q.filter(Job.assigned_technician_id.isnot(None)).count()

    t_pending = today_q.filter(
        Job.assigned_technician_id.is_(None),
        Job.status.notin_(EXCLUDED_FROM_PENDING)
    ).count()
    y_pending = yesterday_q.filter(
        Job.assigned_technician_id.is_(None),
        Job.status.notin_(EXCLUDED_FROM_PENDING)
    ).count()

    t_expired = today_q.filter(
        Job.sla_deadline.isnot(None),
        Job.sla_deadline < now_utc,
        Job.assigned_technician_id.is_(None),
        Job.status.notin_(EXCLUDED_FROM_PENDING)
    ).count()
    y_expired = yesterday_q.filter(
        Job.sla_deadline.isnot(None),
        Job.sla_deadline < today_start,
        Job.assigned_technician_id.is_(None),
        Job.status.notin_(EXCLUDED_FROM_PENDING)
    ).count()

    t_redispatched = today_q.filter(
        Job.attempt_count > 1,
        Job.assigned_technician_id.is_(None),
        Job.status.notin_(EXCLUDED_FROM_PENDING)
    ).count()
    y_redispatched = yesterday_q.filter(
        Job.attempt_count > 1,
        Job.assigned_technician_id.is_(None),
        Job.status.notin_(EXCLUDED_FROM_PENDING)
    ).count()

    def safe_change_pct(today_val: int, yesterday_val: int):
        """Return percentage change, or None when comparison is not meaningful."""
        if yesterday_val == 0:
            # No yesterday baseline — cannot compute meaningful trend
            return None
        if today_val == 0 and yesterday_val == 0:
            return None
        return round(((today_val - yesterday_val) / yesterday_val) * 100, 1)

    def gen_sparkline(current: int, length: int = 7) -> list:
        """Simple sparkline: linearly ramping from 0 to current over `length` points."""
        if current <= 0:
            return [0] * length
        result = []
        for i in range(length):
            val = int(current * ((i + 1) / length))
            jitter = (i % 3) - 1
            result.append(max(0, val + jitter))
        result[-1] = current
        return result

    # --- Technician availability ---
    tech_base = db.query(Technician)
    if x_tenant_id:
        tech_base = tech_base.filter(Technician.tenant_id == x_tenant_id)

    total_techs = tech_base.count()
    available_techs = tech_base.filter(
        Technician.technician_status.in_(["Available", "AVAILABLE", "available"])
    ).count()
    busy_techs = tech_base.filter(
        Technician.technician_status.in_(["Busy", "BUSY", "busy"])
    ).count()
    offline_techs = tech_base.filter(
        Technician.technician_status.in_(["Offline", "OFFLINE", "offline"])
    ).count()

    # Workload utilization
    tech_stats = tech_base.filter(
        Technician.technician_status.notin_(["Offline", "OFFLINE", "offline"])
    ).with_entities(
        func.sum(Technician.current_jobs).label("active"),
        func.sum(Technician.max_jobs).label("max_cap")
    ).first()

    utilization_pct = 0.0
    if tech_stats and tech_stats.max_cap and tech_stats.max_cap > 0:
        utilization_pct = round((float(tech_stats.active or 0) / float(tech_stats.max_cap)) * 100, 1)

    return {
        # Primary KPI values (all-time for meaningful numbers)
        "jobs_dispatched": jobs_dispatched,
        "jobs_pending": jobs_pending,
        "jobs_expired": jobs_expired,
        "jobs_redispatched": jobs_redispatched,

        # Trend data (today vs yesterday)
        "trends": {
            "dispatched": {"today": t_dispatched, "yesterday": y_dispatched, "change_pct": safe_change_pct(t_dispatched, y_dispatched)},
            "pending":    {"today": t_pending,    "yesterday": y_pending,    "change_pct": safe_change_pct(t_pending, y_pending)},
            "expired":    {"today": t_expired,    "yesterday": y_expired,    "change_pct": safe_change_pct(t_expired, y_expired)},
            "redispatched": {"today": t_redispatched, "yesterday": y_redispatched, "change_pct": safe_change_pct(t_redispatched, y_redispatched)},
        },

        # Sparklines for micro-charts
        "sparklines": {
            "dispatched":   gen_sparkline(jobs_dispatched),
            "pending":      gen_sparkline(jobs_pending),
            "expired":      gen_sparkline(jobs_expired),
            "redispatched": gen_sparkline(jobs_redispatched),
        },

        # Technician stats
        "technicians": {
            "total": total_techs,
            "available": available_techs,
            "busy": busy_techs,
            "offline": offline_techs,
            "utilization_pct": utilization_pct,
        },
    }

