from sqlalchemy import text
from app.database import engine

with engine.connect() as connection:

    # Check GPS table
    result = connection.execute(
        text("SELECT to_regclass('public.gps_pings')")
    )
    print("GPS table:", result.scalar())

    # Check GPS partition function
    result = connection.execute(
        text(
            "SELECT proname "
            "FROM pg_proc "
            "WHERE proname = 'create_gps_ping_partition'"
        )
    )
    print("GPS function:", result.fetchall())

    # Check Alembic version
    result = connection.execute(
        text("SELECT * FROM alembic_version")
    )
    print("Alembic version:", result.fetchall())