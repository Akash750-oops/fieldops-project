from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()
engine = create_engine(os.environ["DATABASE_URL"])

tables = [
    "jobs",
    "technicians",
    "notifications",
    "notification_deliveries",
    "job_assignments",
    "customer_profiles",
    "service_requests",
    "dispatcher_notifications",
    "agent_state_records",
    "audit_events",
]

with engine.connect() as conn:
    for table in tables:
        print(f"\n=== {table} ===")

        rows = conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = :table
                  AND column_name = 'organization_id'
            """),
            {"table": table},
        ).fetchall()

        print("organization_id:", "YES" if rows else "NO")
