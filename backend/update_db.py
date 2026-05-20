import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
from pathlib import Path

# Load environment variables relative to this file
env_path = Path(__file__).resolve().parent / '.env'
load_dotenv(dotenv_path=env_path)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in environment variables")

engine = create_engine(
    DATABASE_URL,
    connect_args={"connect_timeout": 5}
)

def update_schema():
    queries = [
        "ALTER TABLE technicians ADD COLUMN IF NOT EXISTS current_jobs INTEGER DEFAULT 0;",
        "ALTER TABLE technicians ADD COLUMN IF NOT EXISTS max_jobs INTEGER DEFAULT 5;",
        "ALTER TABLE technicians ADD COLUMN IF NOT EXISTS tech_id VARCHAR(36) UNIQUE;",
        "ALTER TABLE technicians ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(50);",
        "ALTER TABLE technicians ADD COLUMN IF NOT EXISTS last_ping TIMESTAMP WITH TIME ZONE;",
        "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS required_skill VARCHAR(100);",
        "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS assigned_technician_id INTEGER REFERENCES technicians(technician_id);",
        "ALTER TABLE technicians ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;",
        "ALTER TABLE technicians ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;",
        "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;",
        "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;",
        "CREATE TABLE IF NOT EXISTS audit_events (id SERIAL PRIMARY KEY, tech_id VARCHAR(36) NOT NULL, tenant_id VARCHAR(50) NOT NULL, event_type VARCHAR(50) NOT NULL, old_status VARCHAR(30), new_status VARCHAR(30) NOT NULL, created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP);",
        "CREATE TABLE IF NOT EXISTS dispatcher_notifications (id SERIAL PRIMARY KEY, tech_id VARCHAR(36) NOT NULL, tenant_id VARCHAR(50) NOT NULL, message TEXT NOT NULL, created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP);",
        "CREATE INDEX IF NOT EXISTS idx_audit_events_tech_id ON audit_events(tech_id);",
        "CREATE INDEX IF NOT EXISTS idx_dispatcher_notifications_tech_id ON dispatcher_notifications(tech_id);"
    ]
    
    with engine.connect() as connection:
        for query in queries:
            print(f"Executing: {query}")
            connection.execute(text(query))
            connection.commit()
    print("Database schema updated successfully.")

if __name__ == "__main__":
    update_schema()
