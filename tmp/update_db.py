
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

def update_db():
    with engine.connect() as conn:
        print("Connected to database.")
        
        # 1. Update existing data to uppercase if it exists
        print("Updating existing priority values to uppercase...")
        conn.execute(text("UPDATE jobs SET priority = 'HIGH' WHERE priority = 'High'"))
        conn.execute(text("UPDATE jobs SET priority = 'MEDIUM' WHERE priority = 'Medium'"))
        conn.execute(text("UPDATE jobs SET priority = 'LOW' WHERE priority = 'Low'"))
        
        # 2. Drop old constraint
        print("Dropping old constraint...")
        conn.execute(text("ALTER TABLE jobs DROP CONSTRAINT IF EXISTS check_priority_valid"))
        
        # 3. Add new constraint
        print("Adding new constraint...")
        conn.execute(text("ALTER TABLE jobs ADD CONSTRAINT check_priority_valid CHECK (priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL'))"))
        
        conn.commit()
        print("Database updated successfully.")

if __name__ == "__main__":
    try:
        update_db()
    except Exception as e:
        print(f"Error updating database: {e}")
