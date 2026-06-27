"""create_gps_pings_partitioned_table

Revision ID: 9e973eaa3f1c
Revises: 
Create Date: 2026-06-25 11:00:55.048579

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9e973eaa3f1c'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create tenants table if it does not exist
    op.execute("""
    CREATE TABLE IF NOT EXISTS tenants (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name VARCHAR(100) NOT NULL,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    """)

    # 2. Insert default tenant
    op.execute("""
    INSERT INTO tenants (id, name)
    VALUES ('d7b38d38-2d88-468f-9a1b-3f4119d8544e', 'Default Tenant')
    ON CONFLICT (id) DO NOTHING;
    """)

    # 3. Drop existing non-partitioned gps_pings table if it exists
    op.execute("DROP TABLE IF EXISTS gps_pings CASCADE;")

    # 4. Create range partitioned gps_pings table
    op.execute("""
    CREATE TABLE gps_pings (
        id UUID NOT NULL DEFAULT gen_random_uuid(),
        technician_id VARCHAR(36) NOT NULL REFERENCES technicians(tech_id),
        job_id INT NOT NULL REFERENCES jobs(id),
        latitude DECIMAL(10, 8) NOT NULL CHECK (latitude BETWEEN -90 AND 90),
        longitude DECIMAL(11, 8) NOT NULL CHECK (longitude BETWEEN -180 AND 180),
        timestamp TIMESTAMPTZ NOT NULL,
        accuracy DECIMAL(6, 2),
        altitude DECIMAL(8, 2),
        created_at TIMESTAMPTZ DEFAULT NOW(),
        tenant_id UUID NOT NULL REFERENCES tenants(id),
        PRIMARY KEY (id, timestamp)
    ) PARTITION BY RANGE (timestamp);
    """)

    # 5. Create partitioned indexes
    # Add composite index on (tenant_id, technician_id, timestamp)
    op.execute("CREATE INDEX idx_gps_pings_tenant_tech_time ON gps_pings (tenant_id, technician_id, timestamp);")
    # Add composite index on (job_id, timestamp)
    op.execute("CREATE INDEX idx_gps_pings_job_time ON gps_pings (job_id, timestamp);")
    # Add index on id field for quick UUID lookup
    op.execute("CREATE INDEX idx_gps_pings_id ON gps_pings (id);")

    # 6. Create trigger-like helper function to auto-create monthly partitions
    op.execute("""
    CREATE OR REPLACE FUNCTION create_gps_ping_partition(target_date TIMESTAMPTZ)
    RETURNS VOID AS $$
    DECLARE
        partition_start DATE;
        partition_end DATE;
        partition_name TEXT;
        sql TEXT;
    BEGIN
        partition_start := DATE_TRUNC('month', target_date)::DATE;
        partition_end := (partition_start + INTERVAL '1 month')::DATE;
        partition_name := 'gps_pings_' || TO_CHAR(partition_start, 'YYYY_MM');
        
        IF NOT EXISTS (
            SELECT 1 
            FROM pg_class c 
            JOIN pg_namespace n ON n.oid = c.relnamespace 
            WHERE c.relname = partition_name
        ) THEN
            sql := 'CREATE TABLE ' || partition_name || ' PARTITION OF gps_pings ' ||
                   'FOR VALUES FROM (' || quote_literal(partition_start) || ') TO (' || quote_literal(partition_end) || ')';
            EXECUTE sql;
        END IF;
    END;
    $$ LANGUAGE plpgsql;
    """)

    # 7. Pre-create partitions for the current and next month
    op.execute("SELECT create_gps_ping_partition(NOW());")
    op.execute("SELECT create_gps_ping_partition(NOW() + INTERVAL '1 month');")


def downgrade() -> None:
    # 1. Drop gps_pings table (automatically drops all its partitions and indexes)
    op.execute("DROP TABLE IF EXISTS gps_pings CASCADE;")
    
    # 2. Drop the partition creator helper function
    op.execute("DROP FUNCTION IF EXISTS create_gps_ping_partition(TIMESTAMPTZ);")

    # 3. Drop tenants table
    op.execute("DROP TABLE IF EXISTS tenants CASCADE;")

