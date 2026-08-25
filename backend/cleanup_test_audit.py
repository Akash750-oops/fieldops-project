from sqlalchemy import text
from app.database import SessionLocal

db = SessionLocal()

try:
    result = db.execute(
        text(
            """
            DELETE FROM sentiment_audit_records
            WHERE id IN (1, 2, 3)
              AND tenant_id = 'tenant-1'
              AND customer_id = 'test-customer'
            """
        )
    )

    db.commit()

    print(f"Test records removed: {result.rowcount}")

finally:
    db.close()
