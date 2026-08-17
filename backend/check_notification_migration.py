from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()
engine = create_engine(os.environ["DATABASE_URL"])

with engine.connect() as conn:
    print("=== NOTIFICATIONS TENANT_ID ===")
    row = conn.execute(text("""
        SELECT column_name, is_nullable, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'notifications'
          AND column_name = 'tenant_id'
    """)).fetchone()
    print(row)

    print("\n=== INDEX ===")
    rows = conn.execute(text("""
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE schemaname = 'public'
          AND tablename = 'notifications'
          AND indexname = 'ix_notifications_tenant_id'
    """)).fetchall()
    for row in rows:
        print(row)

    print("\n=== FOREIGN KEY ===")
    rows = conn.execute(text("""
        SELECT
            tc.constraint_name,
            kcu.column_name,
            ccu.table_name AS foreign_table,
            ccu.column_name AS foreign_column
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage ccu
          ON tc.constraint_name = ccu.constraint_name
         AND tc.table_schema = ccu.table_schema
        WHERE tc.table_schema = 'public'
          AND tc.table_name = 'notifications'
          AND tc.constraint_type = 'FOREIGN KEY'
          AND tc.constraint_name = 'fk_notifications_organization'
    """)).fetchall()
    for row in rows:
        print(row)

    print("\n=== NULL tenant_id COUNT ===")
    row = conn.execute(text("""
        SELECT COUNT(*)
        FROM notifications
        WHERE tenant_id IS NULL
    """)).fetchone()
    print(row[0])
