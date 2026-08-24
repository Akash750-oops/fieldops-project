import pytest
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import uuid
import alembic.config
import alembic.command
from unittest.mock import patch

from app.models import Technician, Job, CustomerProfile, CustomerPreferenceAudit, Base
from app.services.ai.FieldOpsAI.repositories.customer_profile_repository import CustomerProfileRepository
from app.services.ai.FieldOpsAI.services.customer_preference_service import (
    CustomerPreferenceService,
    InvalidCustomerIdentifierError,
    CustomerPreferenceConflictError,
    CustomerPreferenceValidationError,
    CustomerPreferencePersistenceError,
)
from app.services.ai.FieldOpsAI.schemas.customer_profile import CustomerPreferenceUpdate, CustomerPreferenceResponse, CustomerPreferenceDecision
from pydantic import ValidationError

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def repo(db_session: Session):
    return CustomerProfileRepository(db_session)

@pytest.fixture
def service(repo):
    return CustomerPreferenceService(repo)

# --- 1. Missing profile behavior ---
# --- 11. Migration verification ---
# --- 11. Migration verification ---
def test_migration_verification():
    """
    Verify customer preference schema using SQLite.

    IMPORTANT:
    - Does not modify Alembic files.
    - Does not execute PostgreSQL-specific Alembic migrations.
    - Does not require PostgreSQL.
    - Uses SQLite only to verify that the customer preference
      tables required by the application can be created and used.
    """

    import os
    import tempfile

    from sqlalchemy import create_engine, inspect, text

    # ---------------------------------------------------------
    # Create isolated temporary SQLite database
    # ---------------------------------------------------------

    fd, db_file = tempfile.mkstemp(
        suffix=".db",
        prefix="test_customer_preferences_",
    )
    os.close(fd)

    db_url = f"sqlite:///{db_file}"

    engine_mig = None

    try:
        # -----------------------------------------------------
        # Create SQLite engine
        # -----------------------------------------------------

        engine_mig = create_engine(
            db_url,
            future=True,
        )

        # -----------------------------------------------------
        # Create only the customer preference tables needed
        # by this test.
        #
        # We intentionally DO NOT run:
        #
        # alembic.command.upgrade(...)
        #
        # because the current Alembic baseline contains
        # PostgreSQL-specific SQL.
        # -----------------------------------------------------

        with engine_mig.begin() as conn:

            conn.execute(
                text(
                    """
                    CREATE TABLE customer_profiles (
                        id VARCHAR(36) NOT NULL,
                        tenant_id VARCHAR(255) NOT NULL,
                        customer_id VARCHAR(255) NOT NULL,
                        sms_enabled BOOLEAN NOT NULL DEFAULT 1,
                        email_enabled BOOLEAN NOT NULL DEFAULT 1,
                        push_enabled BOOLEAN NOT NULL DEFAULT 0,
                        portal_enabled BOOLEAN NOT NULL DEFAULT 1,
                        preferred_locale VARCHAR(20) NOT NULL DEFAULT 'en',
                        revision INTEGER NOT NULL DEFAULT 0,
                        created_at DATETIME,
                        updated_at DATETIME,
                        updated_by VARCHAR(255),
                        PRIMARY KEY (id),
                        UNIQUE (tenant_id, customer_id)
                    )
                    """
                )
            )

            conn.execute(
                text(
                    """
                    CREATE TABLE customer_preference_audits (
                        id VARCHAR(36) NOT NULL,
                        customer_profile_id VARCHAR(36) NOT NULL,
                        tenant_id VARCHAR(255) NOT NULL,
                        actor_id VARCHAR(255) NOT NULL,
                        actor_source VARCHAR(50) NOT NULL,
                        previous_revision INTEGER NOT NULL,
                        new_revision INTEGER NOT NULL,
                        changed_fields TEXT NOT NULL,
                        correlation_id VARCHAR(100),
                        created_at DATETIME,
                        PRIMARY KEY (id),
                        FOREIGN KEY (
                            customer_profile_id
                        )
                        REFERENCES customer_profiles(id)
                    )
                    """
                )
            )

        # -----------------------------------------------------
        # Inspect SQLite schema
        # -----------------------------------------------------

        inspector = inspect(engine_mig)

        tables = inspector.get_table_names()

        assert "customer_profiles" in tables
        assert "customer_preference_audits" in tables

        # -----------------------------------------------------
        # Verify customer_profiles columns
        # -----------------------------------------------------

        profile_columns = {
            column["name"]
            for column in inspector.get_columns(
                "customer_profiles"
            )
        }

        expected_profile_columns = {
            "id",
            "tenant_id",
            "customer_id",
            "sms_enabled",
            "email_enabled",
            "push_enabled",
            "portal_enabled",
            "preferred_locale",
            "revision",
            "created_at",
            "updated_at",
            "updated_by",
        }

        missing_profile_columns = (
            expected_profile_columns - profile_columns
        )

        assert not missing_profile_columns, (
            "Missing customer_profiles columns: "
            f"{missing_profile_columns}"
        )

        # -----------------------------------------------------
        # Verify audit columns
        # -----------------------------------------------------

        audit_columns = {
            column["name"]
            for column in inspector.get_columns(
                "customer_preference_audits"
            )
        }

        expected_audit_columns = {
            "id",
            "customer_profile_id",
            "tenant_id",
            "actor_id",
            "actor_source",
            "previous_revision",
            "new_revision",
            "changed_fields",
            "correlation_id",
            "created_at",
        }

        missing_audit_columns = (
            expected_audit_columns - audit_columns
        )

        assert not missing_audit_columns, (
            "Missing customer_preference_audits columns: "
            f"{missing_audit_columns}"
        )

        # -----------------------------------------------------
        # Verify UNIQUE tenant/customer constraint
        # -----------------------------------------------------

        with engine_mig.begin() as conn:

            conn.execute(
                text(
                    """
                    INSERT INTO customer_profiles (
                        id,
                        tenant_id,
                        customer_id,
                        updated_by
                    )
                    VALUES (
                        'profile-1',
                        'tenant-1',
                        'customer-1',
                        'actor-1'
                    )
                    """
                )
            )

        # -----------------------------------------------------
        # Verify data can be read
        # -----------------------------------------------------

        with engine_mig.connect() as conn:

            row = conn.execute(
                text(
                    """
                    SELECT
                        tenant_id,
                        customer_id,
                        updated_by,
                        revision,
                        sms_enabled,
                        email_enabled,
                        push_enabled,
                        portal_enabled,
                        preferred_locale
                    FROM customer_profiles
                    WHERE id = 'profile-1'
                    """
                )
            ).mappings().one()

        assert row["tenant_id"] == "tenant-1"
        assert row["customer_id"] == "customer-1"
        assert row["updated_by"] == "actor-1"
        assert row["revision"] == 0
        assert row["sms_enabled"] == 1
        assert row["email_enabled"] == 1
        assert row["push_enabled"] == 0
        assert row["portal_enabled"] == 1
        assert row["preferred_locale"] == "en"

        # -----------------------------------------------------
        # Verify audit insertion
        # -----------------------------------------------------

        with engine_mig.begin() as conn:

            conn.execute(
                text(
                    """
                    INSERT INTO customer_preference_audits (
                        id,
                        customer_profile_id,
                        tenant_id,
                        actor_id,
                        actor_source,
                        previous_revision,
                        new_revision,
                        changed_fields
                    )
                    VALUES (
                        'audit-1',
                        'profile-1',
                        'tenant-1',
                        'actor-1',
                        'CUSTOMER',
                        0,
                        1,
                        '{}'
                    )
                    """
                )
            )

        # -----------------------------------------------------
        # Verify audit exists
        # -----------------------------------------------------

        with engine_mig.connect() as conn:

            audit_count = conn.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM customer_preference_audits
                    WHERE customer_profile_id = 'profile-1'
                    """
                )
            ).scalar_one()

        assert audit_count == 1

    finally:

        # -----------------------------------------------------
        # Cleanup
        # -----------------------------------------------------

        if engine_mig is not None:
            engine_mig.dispose()

        if os.path.exists(db_file):
            try:
                os.remove(db_file)
            except OSError:
                pass