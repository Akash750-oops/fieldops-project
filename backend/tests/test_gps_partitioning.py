import os
import pytest
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone
import uuid
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

from alembic.config import Config
from alembic import command

# Connect to actual PostgreSQL database
DATABASE_URL = os.getenv("DATABASE_URL")

@pytest.fixture(scope="module")
def pg_engine():
    if not DATABASE_URL or not DATABASE_URL.startswith("postgresql"):
        pytest.skip("PostgreSQL is not configured in DATABASE_URL")
    try:
        engine = create_engine(DATABASE_URL)
        # Force immediate connection check
        with engine.connect() as conn:
            pass
    except Exception as e:
        pytest.skip(f"PostgreSQL server connection failed: {e}")
        return

    # Run alembic migrations to prepare partition tables
    try:
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        # Ensure June and July 2026 partitions are created for time-independent testing
        with engine.connect() as conn:
            conn.execute(text("SELECT create_gps_ping_partition('2026-06-15 12:00:00+00');"))
            conn.execute(text("SELECT create_gps_ping_partition('2026-07-15 12:00:00+00');"))
            conn.commit()
    except Exception as e:
        print(f"Failed to run alembic migrations: {e}")

    yield engine
    engine.dispose()

@pytest.fixture(scope="function")
def pg_session(pg_engine):
    Session = sessionmaker(bind=pg_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()

def test_partitioned_table_exists(pg_engine):
    inspector = inspect(pg_engine)
    tables = inspector.get_table_names()
    assert "gps_pings" in tables
    # Check that partitions exist
    # Current month (June 2026) and next month (July 2026) partitions should exist
    assert "gps_pings_2026_06" in tables
    assert "gps_pings_2026_07" in tables

def test_default_values_and_uuid_generation(pg_session):
    # Clear the table first to avoid duplicate keys in other tests
    pg_session.execute(text("TRUNCATE TABLE gps_pings CASCADE;"))
    pg_session.commit()
    
    # Get a technician and job
    tech_id = pg_session.execute(text("SELECT tech_id FROM technicians LIMIT 1;")).scalar()
    job_id = pg_session.execute(text("SELECT id FROM jobs LIMIT 1;")).scalar()
    tenant_id = "d7b38d38-2d88-468f-9a1b-3f4119d8544e" # default tenant
    
    if not tech_id or not job_id:
        # Seed dummy ones
        pg_session.execute(text("INSERT INTO technicians (tech_id, technician_name, technician_skill, technician_location) VALUES ('tech-dummy-part', 'Part Tech', 'HVAC', '0,0') ON CONFLICT DO NOTHING;"))
        pg_session.execute(text("INSERT INTO jobs (id, customer_name, location, issue_description, priority, service_type, contact_number, preferred_service_date, status) VALUES (99991, 'Cust', '0,0', 'Desc', 'HIGH', 'HVAC', '1234567890', NOW()::DATE, 'active') ON CONFLICT DO NOTHING;"))
        pg_session.commit()
        tech_id = 'tech-dummy-part'
        job_id = 99991

    # Insert ping with defaults for id and created_at
    # Note: timestamp is set to June 2026 (partition gps_pings_2026_06)
    pg_session.execute(text("""
        INSERT INTO gps_pings (technician_id, job_id, latitude, longitude, timestamp, tenant_id)
        VALUES (:tech_id, :job_id, 13.0827, 80.2707, '2026-06-15 12:00:00+00', :tenant_id)
    """), {"tech_id": tech_id, "job_id": job_id, "tenant_id": tenant_id})
    pg_session.commit()

    # Query back
    result = pg_session.execute(text("SELECT id, created_at, latitude FROM gps_pings;")).first()
    assert result is not None
    assert isinstance(result[0], uuid.UUID) # id generated as UUID
    assert isinstance(result[1], datetime)  # created_at generated
    assert float(result[2]) == 13.0827

def test_check_constraints_range(pg_session):
    # Retrieve valid tech/job ids
    tech_id = pg_session.execute(text("SELECT tech_id FROM technicians LIMIT 1;")).scalar()
    job_id = pg_session.execute(text("SELECT id FROM jobs LIMIT 1;")).scalar()
    tenant_id = "d7b38d38-2d88-468f-9a1b-3f4119d8544e"

    # Latitude out of range (> 90)
    with pytest.raises(IntegrityError):
        pg_session.execute(text("""
            INSERT INTO gps_pings (technician_id, job_id, latitude, longitude, timestamp, tenant_id)
            VALUES (:tech_id, :job_id, 90.1, 80.2707, '2026-06-15 12:00:00+00', :tenant_id)
        """), {"tech_id": tech_id, "job_id": job_id, "tenant_id": tenant_id})
        pg_session.commit()
    pg_session.rollback()

    # Longitude out of range (< -180)
    with pytest.raises(IntegrityError):
        pg_session.execute(text("""
            INSERT INTO gps_pings (technician_id, job_id, latitude, longitude, timestamp, tenant_id)
            VALUES (:tech_id, :job_id, 13.0827, -180.1, '2026-06-15 12:00:00+00', :tenant_id)
        """), {"tech_id": tech_id, "job_id": job_id, "tenant_id": tenant_id})
        pg_session.commit()
    pg_session.rollback()

def test_foreign_key_constraints(pg_session):
    tenant_id = "d7b38d38-2d88-468f-9a1b-3f4119d8544e"
    
    # Invalid technician_id (not existing in technicians)
    with pytest.raises(IntegrityError):
        pg_session.execute(text("""
            INSERT INTO gps_pings (technician_id, job_id, latitude, longitude, timestamp, tenant_id)
            VALUES ('non-existent-tech-uuid-string', 1, 13.0827, 80.2707, '2026-06-15 12:00:00+00', :tenant_id)
        """), {"tenant_id": tenant_id})
        pg_session.commit()
    pg_session.rollback()

    # Invalid job_id
    tech_id = pg_session.execute(text("SELECT tech_id FROM technicians LIMIT 1;")).scalar()
    with pytest.raises(IntegrityError):
        pg_session.execute(text("""
            INSERT INTO gps_pings (technician_id, job_id, latitude, longitude, timestamp, tenant_id)
            VALUES (:tech_id, 999999, 13.0827, 80.2707, '2026-06-15 12:00:00+00', :tenant_id)
        """), {"tech_id": tech_id, "tenant_id": tenant_id})
        pg_session.commit()
    pg_session.rollback()

def test_partition_pruning_explain(pg_session):
    # Insert data into two separate partitions
    pg_session.execute(text("TRUNCATE TABLE gps_pings CASCADE;"))
    pg_session.commit()
    
    tech_id = pg_session.execute(text("SELECT tech_id FROM technicians LIMIT 1;")).scalar()
    job_id = pg_session.execute(text("SELECT id FROM jobs LIMIT 1;")).scalar()
    tenant_id = "d7b38d38-2d88-468f-9a1b-3f4119d8544e"

    # Insert into June 2026
    pg_session.execute(text("""
        INSERT INTO gps_pings (technician_id, job_id, latitude, longitude, timestamp, tenant_id)
        VALUES (:tech_id, :job_id, 13.0, 80.0, '2026-06-15 12:00:00+00', :tenant_id)
    """), {"tech_id": tech_id, "job_id": job_id, "tenant_id": tenant_id})
    
    # Insert into July 2026
    pg_session.execute(text("""
        INSERT INTO gps_pings (technician_id, job_id, latitude, longitude, timestamp, tenant_id)
        VALUES (:tech_id, :job_id, 14.0, 81.0, '2026-07-15 12:00:00+00', :tenant_id)
    """), {"tech_id": tech_id, "job_id": job_id, "tenant_id": tenant_id})
    pg_session.commit()

    # Query with a date range filtering for June 2026 only (strictly within June UTC and Local to prevent partition overlap)
    # Explain Analyze is used to get the actual plan
    explain_query = """
        EXPLAIN ANALYZE 
        SELECT * FROM gps_pings 
        WHERE timestamp BETWEEN '2026-06-02 00:00:00+00' AND '2026-06-28 00:00:00+00';
    """
    plan = pg_session.execute(text(explain_query)).all()
    plan_text = "\n".join([row[0] for row in plan])
    
    # Verify that the query plan ONLY scanned the June partition (gps_pings_2026_06)
    # and did NOT scan the July partition (gps_pings_2026_07)
    assert "gps_pings_2026_06" in plan_text
    assert "gps_pings_2026_07" not in plan_text

def test_index_usage_explain(pg_session):
    # Verify index usage on tenant_id, technician_id, timestamp
    explain_query = """
        EXPLAIN 
        SELECT * FROM gps_pings 
        WHERE tenant_id = 'd7b38d38-2d88-468f-9a1b-3f4119d8544e' 
          AND technician_id = 'tech-val' 
          AND timestamp BETWEEN '2026-06-02 00:00:00+00' AND '2026-06-28 00:00:00+00';
    """
    
    pg_session.execute(text("SET enable_seqscan = off;"))
    plan = pg_session.execute(text(explain_query)).all()
    plan_text = "\n".join([row[0] for row in plan])
    pg_session.execute(text("SET enable_seqscan = on;")) # restore
    
    # Check for presence of the partition composite index name pattern in the explain plan
    assert "idx_gps_pings_tenant_tech_time" in plan_text or "tenant_id_technician_id_timestamp" in plan_text

    # Verify index usage on job_id, timestamp
    explain_query_job = """
        EXPLAIN 
        SELECT * FROM gps_pings 
        WHERE job_id = 1 
          AND timestamp BETWEEN '2026-06-02 00:00:00+00' AND '2026-06-28 00:00:00+00';
    """
    pg_session.execute(text("SET enable_seqscan = off;"))
    plan_job = pg_session.execute(text(explain_query_job)).all()
    plan_job_text = "\n".join([row[0] for row in plan_job])
    pg_session.execute(text("SET enable_seqscan = on;")) # restore
    
    assert "idx_gps_pings_job_time" in plan_job_text or "job_id_timestamp" in plan_job_text

def test_auto_partition_creation(pg_engine, pg_session):
    inspector = inspect(pg_engine)
    if "gps_pings_2026_08" in inspector.get_table_names():
        pg_session.execute(text("DROP TABLE gps_pings_2026_08;"))
        pg_session.commit()

    # Call function for August 2026
    pg_session.execute(text("SELECT create_gps_ping_partition('2026-08-15 12:00:00+00');"))
    pg_session.commit()

    # Re-inspect tables
    inspector = inspect(pg_engine)
    assert "gps_pings_2026_08" in inspector.get_table_names()

def test_downgrade_and_upgrade_reversibility(pg_engine):
    # Run Alembic downgrade
    alembic_cfg = Config("alembic.ini")
    
    # Downgrade to base
    command.downgrade(alembic_cfg, "base")
    inspector = inspect(pg_engine)
    tables = inspector.get_table_names()
    assert "gps_pings" not in tables
    assert "gps_pings_2026_06" not in tables
    assert "tenants" not in tables

    # Re-upgrade to head to restore db state for application
    command.upgrade(alembic_cfg, "head")
    
    # Re-create June/July 2026 partitions
    with pg_engine.connect() as conn:
        conn.execute(text("SELECT create_gps_ping_partition('2026-06-15 12:00:00+00');"))
        conn.execute(text("SELECT create_gps_ping_partition('2026-07-15 12:00:00+00');"))
        conn.commit()

    inspector = inspect(pg_engine)
    tables = inspector.get_table_names()
    assert "gps_pings" in tables
    assert "gps_pings_2026_06" in tables
    assert "tenants" in tables
