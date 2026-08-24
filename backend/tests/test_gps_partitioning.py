import uuid

import pytest

from datetime import datetime

from sqlalchemy import (
    create_engine,
    text,
    inspect,
    event,
)

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker


# ============================================================
# CONSTANTS
# ============================================================

TENANT_ID = "d7b38d38-2d88-468f-9a1b-3f4119d8544e"

TECH_ID = "tech-dummy-part"

JOB_ID = 99991


# ============================================================
# SQLITE DATABASE
# ============================================================

# ============================================================
# SQLITE ENGINE
# ============================================================

@pytest.fixture(scope="function")
def sqlite_engine():
    """
    Fresh SQLite database for EVERY test.

    SQLite does not support PostgreSQL table partitioning,
    so this creates the logical gps_pings table and indexes
    required for SQLite-side testing.

    No Alembic is executed.
    No PostgreSQL is required.
    """

    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
    )

    # Enable SQLite foreign-key enforcement.
    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()

    with engine.begin() as conn:

        # ----------------------------------------------------
        # TECHNICIANS
        # ----------------------------------------------------

        conn.execute(text("""
            CREATE TABLE technicians (
                tech_id TEXT NOT NULL PRIMARY KEY,
                technician_name TEXT NOT NULL,
                technician_skill TEXT,
                technician_location TEXT
            )
        """))

        # ----------------------------------------------------
        # JOBS
        # ----------------------------------------------------

        conn.execute(text("""
            CREATE TABLE jobs (
                id INTEGER NOT NULL PRIMARY KEY,
                customer_name TEXT,
                location TEXT,
                issue_description TEXT,
                priority TEXT,
                service_type TEXT,
                contact_number TEXT,
                preferred_service_date DATE,
                status TEXT
            )
        """))

        # ----------------------------------------------------
        # TENANTS
        # ----------------------------------------------------

        conn.execute(text("""
            CREATE TABLE tenants (
                id TEXT NOT NULL PRIMARY KEY
            )
        """))

        # ----------------------------------------------------
        # GPS PINGS
        #
        # SQLite has no PostgreSQL-style partitioning.
        #
        # This table represents the logical GPS schema.
        # ----------------------------------------------------

        conn.execute(text("""
            CREATE TABLE gps_pings (
                id TEXT NOT NULL PRIMARY KEY DEFAULT (
                    lower(
                        hex(randomblob(4)) || '-' ||
                        hex(randomblob(2)) || '-' ||
                        hex(randomblob(2)) || '-' ||
                        hex(randomblob(2)) || '-' ||
                        hex(randomblob(6))
                    )
                ),

                technician_id TEXT NOT NULL,

                job_id INTEGER NOT NULL,

                latitude REAL NOT NULL,

                longitude REAL NOT NULL,

                timestamp DATETIME NOT NULL,

                tenant_id TEXT NOT NULL,

                created_at DATETIME NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                CONSTRAINT gps_latitude_range
                    CHECK (
                        latitude >= -90
                        AND latitude <= 90
                    ),

                CONSTRAINT gps_longitude_range
                    CHECK (
                        longitude >= -180
                        AND longitude <= 180
                    ),

                CONSTRAINT fk_gps_technician
                    FOREIGN KEY (technician_id)
                    REFERENCES technicians(tech_id),

                CONSTRAINT fk_gps_job
                    FOREIGN KEY (job_id)
                    REFERENCES jobs(id),

                CONSTRAINT fk_gps_tenant
                    FOREIGN KEY (tenant_id)
                    REFERENCES tenants(id)
            )
        """))

        # ----------------------------------------------------
        # INDEXES
        # ----------------------------------------------------

        conn.execute(text("""
            CREATE INDEX idx_gps_pings_tenant_tech_time
            ON gps_pings (
                tenant_id,
                technician_id,
                timestamp
            )
        """))

        conn.execute(text("""
            CREATE INDEX idx_gps_pings_job_time
            ON gps_pings (
                job_id,
                timestamp
            )
        """))

        # ----------------------------------------------------
        # TEST TENANT
        # ----------------------------------------------------

        conn.execute(text("""
            INSERT INTO tenants (id)
            VALUES (
                'd7b38d38-2d88-468f-9a1b-3f4119d8544e'
            )
        """))

        # ----------------------------------------------------
        # TEST TECHNICIAN
        # ----------------------------------------------------

        conn.execute(text("""
            INSERT INTO technicians (
                tech_id,
                technician_name,
                technician_skill,
                technician_location
            )
            VALUES (
                'tech-dummy-part',
                'Part Tech',
                'HVAC',
                '0,0'
            )
        """))

        # ----------------------------------------------------
        # TEST JOB
        # ----------------------------------------------------

        conn.execute(text("""
            INSERT INTO jobs (
                id,
                customer_name,
                location,
                issue_description,
                priority,
                service_type,
                contact_number,
                preferred_service_date,
                status
            )
            VALUES (
                99991,
                'Cust',
                '0,0',
                'Desc',
                'HIGH',
                'HVAC',
                '1234567890',
                CURRENT_DATE,
                'active'
            )
        """))

    yield engine

    engine.dispose()


# ============================================================
# SQLITE SESSION
# ============================================================

@pytest.fixture
def sqlite_session(sqlite_engine):

    Session = sessionmaker(
        bind=sqlite_engine,
        future=True,
    )

    session = Session()

    try:
        yield session
    finally:
        session.rollback()
        session.close()

# ============================================================
# BASIC GPS TABLE TESTS
# ============================================================

def test_sqlite_gps_table_exists(sqlite_engine):

    inspector = inspect(sqlite_engine)

    tables = inspector.get_table_names()

    assert "gps_pings" in tables


def test_sqlite_gps_columns(sqlite_engine):

    inspector = inspect(sqlite_engine)

    columns = inspector.get_columns(
        "gps_pings"
    )

    column_names = {
        column["name"]
        for column in columns
    }

    expected_columns = {
        "id",
        "technician_id",
        "job_id",
        "latitude",
        "longitude",
        "timestamp",
        "tenant_id",
        "created_at",
    }

    assert expected_columns.issubset(
        column_names
    )


# ============================================================
# DEFAULT VALUES
# ============================================================

def test_sqlite_default_values(sqlite_session):

    sqlite_session.execute(
        text("""
            INSERT INTO gps_pings (
                technician_id,
                job_id,
                latitude,
                longitude,
                timestamp,
                tenant_id
            )
            VALUES (
                :tech_id,
                :job_id,
                13.0827,
                80.2707,
                '2026-06-15 12:00:00',
                :tenant_id
            )
        """),
        {
            "tech_id": TECH_ID,
            "job_id": JOB_ID,
            "tenant_id": TENANT_ID,
        },
    )

    sqlite_session.commit()

    row = sqlite_session.execute(
        text("""
            SELECT
                id,
                created_at,
                latitude,
                longitude
            FROM gps_pings
            LIMIT 1
        """)
    ).first()

    assert row is not None

    assert row.id is not None

    assert row.created_at is not None

    assert float(row.latitude) == pytest.approx(
        13.0827
    )

    assert float(row.longitude) == pytest.approx(
        80.2707
    )


# ============================================================
# LATITUDE CONSTRAINT
# ============================================================

def test_sqlite_latitude_constraint(
    sqlite_session,
):

    with pytest.raises(IntegrityError):

        sqlite_session.execute(
            text("""
                INSERT INTO gps_pings (
                    technician_id,
                    job_id,
                    latitude,
                    longitude,
                    timestamp,
                    tenant_id
                )
                VALUES (
                    :tech_id,
                    :job_id,
                    90.1,
                    80.2707,
                    '2026-06-15 12:00:00',
                    :tenant_id
                )
            """),
            {
                "tech_id": TECH_ID,
                "job_id": JOB_ID,
                "tenant_id": TENANT_ID,
            },
        )

        sqlite_session.commit()

    sqlite_session.rollback()


# ============================================================
# LONGITUDE CONSTRAINT
# ============================================================

def test_sqlite_longitude_constraint(
    sqlite_session,
):

    with pytest.raises(IntegrityError):

        sqlite_session.execute(
            text("""
                INSERT INTO gps_pings (
                    technician_id,
                    job_id,
                    latitude,
                    longitude,
                    timestamp,
                    tenant_id
                )
                VALUES (
                    :tech_id,
                    :job_id,
                    13.0827,
                    -180.1,
                    '2026-06-15 12:00:00',
                    :tenant_id
                )
            """),
            {
                "tech_id": TECH_ID,
                "job_id": JOB_ID,
                "tenant_id": TENANT_ID,
            },
        )

        sqlite_session.commit()

    sqlite_session.rollback()


# ============================================================
# VALID BOUNDARIES
# ============================================================

def test_sqlite_valid_coordinate_boundaries(
    sqlite_session,
):

    test_values = [
        (-90, -180),
        (90, 180),
        (0, 0),
    ]

    for latitude, longitude in test_values:

        sqlite_session.execute(
            text("""
                INSERT INTO gps_pings (
                    technician_id,
                    job_id,
                    latitude,
                    longitude,
                    timestamp,
                    tenant_id
                )
                VALUES (
                    :tech_id,
                    :job_id,
                    :latitude,
                    :longitude,
                    '2026-06-15 12:00:00',
                    :tenant_id
                )
            """),
            {
                "tech_id": TECH_ID,
                "job_id": JOB_ID,
                "latitude": latitude,
                "longitude": longitude,
                "tenant_id": TENANT_ID,
            },
        )

    sqlite_session.commit()

    count = sqlite_session.execute(
        text("""
            SELECT COUNT(*)
            FROM gps_pings
        """)
    ).scalar()

    assert count == 3


# ============================================================
# INVALID TECHNICIAN
# ============================================================

def test_sqlite_invalid_technician(
    sqlite_session,
):

    with pytest.raises(IntegrityError):

        sqlite_session.execute(
            text("""
                INSERT INTO gps_pings (
                    technician_id,
                    job_id,
                    latitude,
                    longitude,
                    timestamp,
                    tenant_id
                )
                VALUES (
                    'does-not-exist',
                    :job_id,
                    13.0827,
                    80.2707,
                    '2026-06-15 12:00:00',
                    :tenant_id
                )
            """),
            {
                "job_id": JOB_ID,
                "tenant_id": TENANT_ID,
            },
        )

        sqlite_session.commit()

    sqlite_session.rollback()


# ============================================================
# INVALID JOB
# ============================================================

def test_sqlite_invalid_job(
    sqlite_session,
):

    with pytest.raises(IntegrityError):

        sqlite_session.execute(
            text("""
                INSERT INTO gps_pings (
                    technician_id,
                    job_id,
                    latitude,
                    longitude,
                    timestamp,
                    tenant_id
                )
                VALUES (
                    :tech_id,
                    999999,
                    13.0827,
                    80.2707,
                    '2026-06-15 12:00:00',
                    :tenant_id
                )
            """),
            {
                "tech_id": TECH_ID,
                "tenant_id": TENANT_ID,
            },
        )

        sqlite_session.commit()

    sqlite_session.rollback()


# ============================================================
# INVALID TENANT
# ============================================================

def test_sqlite_invalid_tenant(
    sqlite_session,
):

    with pytest.raises(IntegrityError):

        sqlite_session.execute(
            text("""
                INSERT INTO gps_pings (
                    technician_id,
                    job_id,
                    latitude,
                    longitude,
                    timestamp,
                    tenant_id
                )
                VALUES (
                    :tech_id,
                    :job_id,
                    13.0827,
                    80.2707,
                    '2026-06-15 12:00:00',
                    'invalid-tenant'
                )
            """),
            {
                "tech_id": TECH_ID,
                "job_id": JOB_ID,
            },
        )

        sqlite_session.commit()

    sqlite_session.rollback()


# ============================================================
# INDEX TESTS
# ============================================================

def test_sqlite_indexes(sqlite_engine):

    inspector = inspect(sqlite_engine)

    indexes = inspector.get_indexes(
        "gps_pings"
    )

    index_names = {
        index["name"]
        for index in indexes
    }

    assert (
        "idx_gps_pings_tenant_tech_time"
        in index_names
    )

    assert (
        "idx_gps_pings_job_time"
        in index_names
    )


# ============================================================
# TIMESTAMP STORAGE
# ============================================================

def test_sqlite_timestamp_storage(
    sqlite_session,
):

    sqlite_session.execute(
        text("""
            INSERT INTO gps_pings (
                technician_id,
                job_id,
                latitude,
                longitude,
                timestamp,
                tenant_id
            )
            VALUES (
                :tech_id,
                :job_id,
                13.0827,
                80.2707,
                :timestamp,
                :tenant_id
            )
        """),
        {
            "tech_id": TECH_ID,
            "job_id": JOB_ID,
            "timestamp": "2026-06-15 12:00:00",
            "tenant_id": TENANT_ID,
        },
    )

    sqlite_session.commit()

    result = sqlite_session.execute(
        text("""
            SELECT timestamp
            FROM gps_pings
            ORDER BY rowid DESC
            LIMIT 1
        """)
    ).scalar()

    assert result is not None


# ============================================================
# MULTIPLE GPS PINGS
# ============================================================

def test_sqlite_multiple_gps_pings(
    sqlite_session,
):

    timestamps = [
        "2026-06-10 10:00:00",
        "2026-06-15 12:00:00",
        "2026-06-20 15:00:00",
        "2026-07-10 10:00:00",
    ]

    for index, timestamp in enumerate(
        timestamps
    ):

        sqlite_session.execute(
            text("""
                INSERT INTO gps_pings (
                    technician_id,
                    job_id,
                    latitude,
                    longitude,
                    timestamp,
                    tenant_id
                )
                VALUES (
                    :tech_id,
                    :job_id,
                    :latitude,
                    :longitude,
                    :timestamp,
                    :tenant_id
                )
            """),
            {
                "tech_id": TECH_ID,
                "job_id": JOB_ID,
                "latitude": 13.0 + index,
                "longitude": 80.0 + index,
                "timestamp": timestamp,
                "tenant_id": TENANT_ID,
            },
        )

    sqlite_session.commit()

    count = sqlite_session.execute(
        text("""
            SELECT COUNT(*)
            FROM gps_pings
        """)
    ).scalar()

    assert count == 4


# ============================================================
# DATE RANGE QUERY
# ============================================================

def test_sqlite_timestamp_range_query(
    sqlite_session,
):

    sqlite_session.execute(
        text("""
            INSERT INTO gps_pings (
                technician_id,
                job_id,
                latitude,
                longitude,
                timestamp,
                tenant_id
            )
            VALUES (
                :tech_id,
                :job_id,
                13.0827,
                80.2707,
                '2026-06-15 12:00:00',
                :tenant_id
            )
        """),
        {
            "tech_id": TECH_ID,
            "job_id": JOB_ID,
            "tenant_id": TENANT_ID,
        },
    )

    sqlite_session.execute(
        text("""
            INSERT INTO gps_pings (
                technician_id,
                job_id,
                latitude,
                longitude,
                timestamp,
                tenant_id
            )
            VALUES (
                :tech_id,
                :job_id,
                14.0827,
                81.2707,
                '2026-07-15 12:00:00',
                :tenant_id
            )
        """),
        {
            "tech_id": TECH_ID,
            "job_id": JOB_ID,
            "tenant_id": TENANT_ID,
        },
    )

    sqlite_session.commit()

    count = sqlite_session.execute(
        text("""
            SELECT COUNT(*)
            FROM gps_pings
            WHERE timestamp >= '2026-06-01 00:00:00'
              AND timestamp <  '2026-07-01 00:00:00'
        """)
    ).scalar()

    assert count == 1


# ============================================================
# GPS TABLE STRUCTURE
# ============================================================

def test_sqlite_gps_schema(sqlite_engine):

    inspector = inspect(sqlite_engine)

    columns = inspector.get_columns(
        "gps_pings"
    )

    column_map = {
        column["name"]: column
        for column in columns
    }

    assert column_map["id"]["nullable"] is False

    assert (
        column_map["technician_id"]["nullable"]
        is False
    )

    assert (
        column_map["job_id"]["nullable"]
        is False
    )

    assert (
        column_map["latitude"]["nullable"]
        is False
    )

    assert (
        column_map["longitude"]["nullable"]
        is False
    )

    assert (
        column_map["timestamp"]["nullable"]
        is False
    )

    assert (
        column_map["tenant_id"]["nullable"]
        is False
    )

    assert (
        column_map["created_at"]["nullable"]
        is False
    )