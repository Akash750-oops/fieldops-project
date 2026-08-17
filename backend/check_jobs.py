from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

engine = create_engine(os.environ["DATABASE_URL"])

with engine.connect() as conn:
    result = conn.execute(
        text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'jobs'
            ORDER BY ordinal_position
        """)
    )

    print("=== JOBS COLUMNS ===")
    for row in result:
        print(f"{row[0]} -> {row[1]}")
