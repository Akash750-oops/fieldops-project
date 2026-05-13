import sys
import os
from sqlalchemy import text

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import engine

def verify_jobs_table():
    query = text("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'jobs'
        ORDER BY ordinal_position;
    """)
    
    with engine.connect() as connection:
        result = connection.execute(query)
        print("Jobs Table Structure:")
        print("-" * 50)
        found = False
        for row in result:
            found = True
            print(f"Column: {row[0]:<20} | Type: {row[1]:<15} | Nullable: {row[2]}")
        
        if not found:
            print("Table 'jobs' NOT FOUND!")
        print("-" * 50)

if __name__ == "__main__":
    verify_jobs_table()
