import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

url = os.getenv("DATABASE_URL").replace("+asyncpg", "")
eng = create_engine(url)

with eng.connect() as conn:
    rows = conn.execute(
        text(
            "SELECT table_schema, table_name FROM information_schema.tables "
            "WHERE table_name = 'alembic_version'"
        )
    ).fetchall()
    print("alembic_version found in:", rows)

    search_path = conn.execute(text("SHOW search_path")).fetchone()
    print("search_path:", search_path)

    current_schema = conn.execute(text("SELECT current_schema()")).fetchone()
    print("current_schema():", current_schema)