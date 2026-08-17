"""
PostgreSQL + SQLAlchemy + Alembic
READ-ONLY model/schema comparison.

This script NEVER:
- creates tables
- alters tables
- inserts/updates/deletes data
- runs Alembic migrations
- creates Alembic revisions

It only reads:
    SQLAlchemy Base.metadata
    PostgreSQL information_schema / catalog metadata
"""

import os

from sqlalchemy import create_engine, inspect
from sqlalchemy.sql.sqltypes import (
    DateTime,
    Float,
    Integer,
    BigInteger,
    SmallInteger,
    Boolean,
    String,
    Text,
    Numeric,
)

# ---------------------------------------------------------------------
# PROJECT IMPORTS
# ---------------------------------------------------------------------

# Adjust this only if your project's Base lives somewhere else.
from app.database import Base

# IMPORTANT:
# Import models so every model is registered in Base.metadata.
import app.models


# ---------------------------------------------------------------------
# DATABASE CONNECTION
# ---------------------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is not set."
    )

engine = create_engine(DATABASE_URL)


# ---------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------

# Alembic's own tracking table.
IGNORED_TABLES = {
    "alembic_version",
}


# ---------------------------------------------------------------------
# TYPE NORMALIZATION
# ---------------------------------------------------------------------

def normalize_type(model_type, db_type):
    """
    Determine whether SQLAlchemy model type and PostgreSQL type
    are semantically compatible.
    """

    model_name = type(model_type).__name__.lower()
    db_name = str(db_type).lower()

    # -------------------------------------------------------------
    # DateTime
    # -------------------------------------------------------------

    if isinstance(model_type, DateTime):
        if "timestamp" in db_name:
            return True

    # -------------------------------------------------------------
    # Float
    # -------------------------------------------------------------

    if isinstance(model_type, Float):
        if (
            "double precision" in db_name
            or db_name == "float"
            or "real" in db_name
        ):
            return True

    # -------------------------------------------------------------
    # Integer
    # -------------------------------------------------------------

    if isinstance(model_type, Integer):
        if db_name in {"integer", "int", "int4"}:
            return True

    # -------------------------------------------------------------
    # BigInteger
    # -------------------------------------------------------------

    if isinstance(model_type, BigInteger):
        if db_name in {"bigint", "int8"}:
            return True

    # -------------------------------------------------------------
    # SmallInteger
    # -------------------------------------------------------------

    if isinstance(model_type, SmallInteger):
        if db_name in {"smallint", "int2"}:
            return True

    # -------------------------------------------------------------
    # Boolean
    # -------------------------------------------------------------

    if isinstance(model_type, Boolean):
        if db_name in {"boolean", "bool"}:
            return True

    # -------------------------------------------------------------
    # Text
    # -------------------------------------------------------------

    if isinstance(model_type, Text):
        if db_name == "text":
            return True

    # -------------------------------------------------------------
    # String
    # -------------------------------------------------------------

    if isinstance(model_type, String):
        if (
            "character varying" in db_name
            or "varchar" in db_name
            or db_name == "text"
        ):
            return True

    # -------------------------------------------------------------
    # Numeric
    # -------------------------------------------------------------

    if isinstance(model_type, Numeric):
        if (
            "numeric" in db_name
            or "decimal" in db_name
        ):
            return True

    # -------------------------------------------------------------
    # Exact fallback
    # -------------------------------------------------------------

    if model_name in db_name:
        return True

    return False


# ---------------------------------------------------------------------
# TABLE COMPARISON
# ---------------------------------------------------------------------

def compare_tables(inspector, metadata):

    model_tables = set(metadata.tables.keys())

    database_tables = set(
        inspector.get_table_names()
    )

    # Remove Alembic's own table.
    model_tables -= IGNORED_TABLES
    database_tables -= IGNORED_TABLES

    only_model = sorted(
        model_tables - database_tables
    )

    only_database = sorted(
        database_tables - model_tables
    )

    common = sorted(
        model_tables & database_tables
    )

    print("\n" + "=" * 80)
    print("TABLE COMPARISON")
    print("=" * 80)

    if not only_model and not only_database:
        print("✅ Model tables and database tables match.")

    if only_model:
        print("\n❌ MODEL ONLY:")
        for table in only_model:
            print(f"   - {table}")

    if only_database:
        print("\n⚠️ DATABASE ONLY:")
        for table in only_database:
            print(f"   - {table}")

    return common, only_model, only_database


# ---------------------------------------------------------------------
# COLUMN COMPARISON
# ---------------------------------------------------------------------

def compare_columns(inspector, metadata, table_name):

    model_table = metadata.tables[table_name]

    model_columns = {
        column.name: column
        for column in model_table.columns
    }

    database_columns = {
        column["name"]: column
        for column in inspector.get_columns(table_name)
    }

    differences = []

    # -------------------------------------------------------------
    # Missing columns
    # -------------------------------------------------------------

    for column in sorted(
        set(model_columns) - set(database_columns)
    ):
        differences.append(
            f"❌ MODEL ONLY COLUMN: {column}"
        )

    for column in sorted(
        set(database_columns) - set(model_columns)
    ):
        differences.append(
            f"❌ DATABASE ONLY COLUMN: {column}"
        )

    # -------------------------------------------------------------
    # Compare common columns
    # -------------------------------------------------------------

    common_columns = (
        set(model_columns)
        & set(database_columns)
    )

    for column_name in sorted(common_columns):

        model_column = model_columns[column_name]

        database_column = database_columns[column_name]

        model_type = model_column.type

        database_type = database_column["type"]

        # ---------------------------------------------------------
        # TYPE
        # ---------------------------------------------------------

        if not normalize_type(
            model_type,
            database_type,
        ):
            differences.append(
                f"❌ {column_name}: TYPE mismatch | "
                f"model={model_type} | "
                f"database={database_type}"
            )

        # ---------------------------------------------------------
        # NULLABLE
        # ---------------------------------------------------------

        if model_column.nullable != database_column["nullable"]:

            differences.append(
                f"❌ {column_name}: NULLABLE mismatch | "
                f"model={model_column.nullable} | "
                f"database={database_column['nullable']}"
            )

    return differences


# ---------------------------------------------------------------------
# PRIMARY KEY
# ---------------------------------------------------------------------

def compare_primary_key(
    inspector,
    metadata,
    table_name,
):

    model_table = metadata.tables[table_name]

    model_pk = {
        column.name
        for column in model_table.primary_key.columns
    }

    database_pk_info = (
        inspector.get_pk_constraint(table_name)
    )

    database_pk = set(
        database_pk_info.get(
            "constrained_columns"
        ) or []
    )

    if model_pk != database_pk:

        return [
            "❌ PRIMARY KEY mismatch | "
            f"model={sorted(model_pk)} | "
            f"database={sorted(database_pk)}"
        ]

    return []


# ---------------------------------------------------------------------
# FOREIGN KEYS
# ---------------------------------------------------------------------

def compare_foreign_keys(
    inspector,
    metadata,
    table_name,
):

    model_table = metadata.tables[table_name]

    model_fks = set()

    for fk in model_table.foreign_keys:

        model_fks.add(
            (
                fk.parent.name,
                fk.column.table.name,
                fk.column.name,
            )
        )

    database_fks = set()

    for fk in inspector.get_foreign_keys(table_name):

        local_columns = (
            fk.get("constrained_columns")
            or []
        )

        remote_table = fk.get(
            "referred_table"
        )

        remote_columns = (
            fk.get("referred_columns")
            or []
        )

        for local, remote in zip(
            local_columns,
            remote_columns,
        ):

            database_fks.add(
                (
                    local,
                    remote_table,
                    remote,
                )
            )

    if model_fks != database_fks:

        return [
            "❌ FOREIGN KEY mismatch\n"
            f"   Model:    {sorted(model_fks)}\n"
            f"   Database: {sorted(database_fks)}"
        ]

    return []


# ---------------------------------------------------------------------
# UNIQUE CONSTRAINTS
# ---------------------------------------------------------------------

def compare_unique_constraints(
    inspector,
    metadata,
    table_name,
):

    model_table = metadata.tables[table_name]

    model_unique = set()

    for constraint in model_table.constraints:

        if constraint.__class__.__name__ == "UniqueConstraint":

            columns = tuple(
                sorted(
                    column.name
                    for column in constraint.columns
                )
            )

            model_unique.add(columns)

    database_unique = set()

    for constraint in (
        inspector.get_unique_constraints(
            table_name
        )
    ):

        columns = tuple(
            sorted(
                constraint.get(
                    "column_names"
                ) or []
            )
        )

        database_unique.add(columns)

    if model_unique != database_unique:

        return [
            "⚠️ UNIQUE CONSTRAINT difference\n"
            f"   Model:    {sorted(model_unique)}\n"
            f"   Database: {sorted(database_unique)}"
        ]

    return []


# ---------------------------------------------------------------------
# INDEXES
# ---------------------------------------------------------------------

def compare_indexes(
    inspector,
    metadata,
    table_name,
):

    model_table = metadata.tables[table_name]

    model_indexes = set()

    for index in model_table.indexes:

        columns = tuple(
            index_column.name
            for index_column in index.columns
        )

        model_indexes.add(
            (
                index.name,
                columns,
                index.unique,
            )
        )

    database_indexes = set()

    for index in inspector.get_indexes(
        table_name
    ):

        columns = tuple(
            index.get(
                "column_names"
            ) or []
        )

        database_indexes.add(
            (
                index.get("name"),
                columns,
                index.get(
                    "unique",
                    False,
                ),
            )
        )

    # -------------------------------------------------------------
    # Ignore unique indexes that represent unique constraints.
    # PostgreSQL may expose a UNIQUE CONSTRAINT as a unique index.
    # -------------------------------------------------------------

    database_unique_constraints = set()

    for constraint in (
        inspector.get_unique_constraints(
            table_name
        )
    ):

        columns = tuple(
            constraint.get(
                "column_names"
            ) or []
        )

        database_unique_constraints.add(columns)

    filtered_database_indexes = set()

    for index in database_indexes:

        name, columns, unique = index

        if (
            unique
            and columns
            in database_unique_constraints
        ):
            continue

        filtered_database_indexes.add(index)

    filtered_model_indexes = set()

    for index in model_indexes:

        name, columns, unique = index

        if (
            unique
            and columns
            in database_unique_constraints
        ):
            continue

        filtered_model_indexes.add(index)

    if (
        filtered_model_indexes
        != filtered_database_indexes
    ):

        return [
            "⚠️ INDEX difference\n"
            f"   Model:    {sorted(filtered_model_indexes)}\n"
            f"   Database: {sorted(filtered_database_indexes)}"
        ]

    return []


# ---------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------

def main():

    print("\n" + "=" * 80)
    print("POSTGRESQL ↔ SQLALCHEMY MODEL CHECK")
    print("=" * 80)

    print(
        "\n⚠️ READ-ONLY CHECK"
        "\nNo migrations."
        "\nNo schema modifications."
        "\nNo data modifications."
    )

    # -------------------------------------------------------------
    # Load SQLAlchemy metadata
    # -------------------------------------------------------------

    metadata = Base.metadata

    # -------------------------------------------------------------
    # Connect to PostgreSQL
    # -------------------------------------------------------------

    with engine.connect() as connection:

        inspector = inspect(connection)

        # ---------------------------------------------------------
        # Compare tables
        # ---------------------------------------------------------

        (
            common_tables,
            model_only,
            database_only,
        ) = compare_tables(
            inspector,
            metadata,
        )

        # IMPORTANT:
        # Count model-only and database-only tables as differences.
        total_differences = (
            len(model_only)
            + len(database_only)
        )

        # ---------------------------------------------------------
        # TABLE DETAILS
        # ---------------------------------------------------------

        for table_name in common_tables:

            print("\n" + "-" * 80)
            print(f"TABLE: {table_name}")
            print("-" * 80)

            differences = []

            # -----------------------------------------------------
            # Columns
            # -----------------------------------------------------

            differences.extend(
                compare_columns(
                    inspector,
                    metadata,
                    table_name,
                )
            )

            # -----------------------------------------------------
            # Primary key
            # -----------------------------------------------------

            differences.extend(
                compare_primary_key(
                    inspector,
                    metadata,
                    table_name,
                )
            )

            # -----------------------------------------------------
            # Foreign keys
            # -----------------------------------------------------

            differences.extend(
                compare_foreign_keys(
                    inspector,
                    metadata,
                    table_name,
                )
            )

            # -----------------------------------------------------
            # Unique constraints
            # -----------------------------------------------------

            differences.extend(
                compare_unique_constraints(
                    inspector,
                    metadata,
                    table_name,
                )
            )

            # -----------------------------------------------------
            # Indexes
            # -----------------------------------------------------

            differences.extend(
                compare_indexes(
                    inspector,
                    metadata,
                    table_name,
                )
            )

            # -----------------------------------------------------
            # Results
            # -----------------------------------------------------

            if differences:

                total_differences += len(
                    differences
                )

                for difference in differences:
                    print(difference)

            else:

                print(
                    "✅ Model and database match."
                )

        # ---------------------------------------------------------
        # FINAL RESULT
        # ---------------------------------------------------------

        print("\n" + "=" * 80)
        print("FINAL RESULT")
        print("=" * 80)

        # Model-only tables
        if model_only:

            print(
                f"\n❌ {len(model_only)} "
                "model-only table(s):"
            )

            for table in model_only:
                print(
                    f"   - {table}"
                )

        # Database-only tables
        if database_only:

            print(
                f"\n⚠️ {len(database_only)} "
                "database-only table(s):"
            )

            for table in database_only:
                print(
                    f"   - {table}"
                )

        # Final status
        if total_differences == 0:

            print(
                "\n✅ NO MODEL/SCHEMA DIFFERENCES "
                "DETECTED."
            )

        else:

            print(
                f"\n⚠️ {total_differences} "
                "potential difference(s) detected."
            )

        print(
            "\nThese are READ-ONLY findings."
            "\nNo database changes were made."
        )

    print("\nCheck completed.")


# ---------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------

if __name__ == "__main__":
    main()