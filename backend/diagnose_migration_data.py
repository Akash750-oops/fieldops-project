from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()
engine = create_engine(os.environ["DATABASE_URL"])

tables = [
    "audit_events",
    "enterprise_audit_logs",
    "notification_templates",
    "assignment_overrides",
    "communication_channel_configurations",
    "communication_configuration_audits",
    "dispatcher_alerts",
    "job_assignments",
    "job_closures",
    "notification_deliveries",
    "preference_audit_logs",
    "scoring_configurations",
    "sla_escalations",
]

with engine.connect() as conn:

    print("=== ORGANIZATION IDS ===")
    rows = conn.execute(text("""
        SELECT id, name
        FROM organizations
        ORDER BY id
    """)).fetchall()

    for row in rows:
        print(row)

    print("\n=== TENANT IDS ===")
    rows = conn.execute(text("""
        SELECT id, name
        FROM tenants
        ORDER BY id
    """)).fetchall()

    for row in rows:
        print(row)

    print("\n=== TENANT-1 EXISTENCE ===")

    row = conn.execute(text("""
        SELECT
            EXISTS (
                SELECT 1
                FROM organizations
                WHERE id = 'tenant-1'
            ) AS organization_tenant_1,
            EXISTS (
                SELECT 1
                FROM tenants
                WHERE id = 'tenant-1'
            ) AS tenant_tenant_1
    """)).fetchone()

    print("organizations.id = tenant-1:", row[0])
    print("tenants.id = tenant-1:", row[1])

    print("\n=== TABLE ROW COUNTS ===")

    for table in tables:
        try:
            count = conn.execute(
                text(f'SELECT COUNT(*) FROM "{table}"')
            ).scalar()

            print(f"{table}: {count}")

        except Exception as e:
            print(f"{table}: ERROR: {e}")

    print("\n=== IMPORTANT TENANT VALUES ===")

    for table in [
        "audit_events",
        "enterprise_audit_logs",
        "notification_templates",
        "sla_escalations",
    ]:
        try:
            rows = conn.execute(text(f"""
                SELECT tenant_id, COUNT(*)
                FROM "{table}"
                GROUP BY tenant_id
                ORDER BY tenant_id
            """)).fetchall()

            print(f"\n{table}:")
            for row in rows:
                print("  ", row)

        except Exception as e:
            print(f"{table}: ERROR: {e}")

