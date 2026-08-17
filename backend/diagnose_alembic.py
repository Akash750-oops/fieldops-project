from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

engine = create_engine(os.environ["DATABASE_URL"])

with engine.connect() as conn:
    print("=== ALEMBIC VERSION ===")
    try:
        result = conn.execute(text("SELECT * FROM alembic_version"))
        print(result.fetchall())
    except Exception as e:
        print("ERROR:", e)

    print()
    print("=== TABLES ===")

    result = conn.execute(
        text("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename
        """)
    )

    for row in result:
        print(row[0])
