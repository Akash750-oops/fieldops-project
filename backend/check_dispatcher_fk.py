from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()
engine = create_engine(os.environ["DATABASE_URL"])

with engine.connect() as conn:
    print("=== DISPATCHER NOTIFICATIONS FK ===")

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
          AND tc.table_name = 'dispatcher_notifications'
          AND tc.constraint_type = 'FOREIGN KEY'
    """)).fetchall()

    for row in rows:
        print(row)

    print("\n=== TENANT_ID COLUMN ===")

    row = conn.execute(text("""
        SELECT column_name, is_nullable, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'dispatcher_notifications'
          AND column_name = 'tenant_id'
    """)).fetchone()

    print(row)
