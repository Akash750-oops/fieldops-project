import sys
import os
from sqlalchemy import text

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import engine

def verify_table_structure():
    query = text("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'technicians'
        ORDER BY ordinal_position;
    """)
    
    with engine.connect() as connection:
        result = connection.execute(query)
        print("Technicians Table Structure:")
        print("-" * 50)
        for row in result:
            print(f"Column: {row[0]:<20} | Type: {row[1]:<15} | Nullable: {row[2]}")
        print("-" * 50)

if __name__ == "__main__":
    verify_table_structure()
