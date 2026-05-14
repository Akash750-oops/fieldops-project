import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in environment variables")

engine = create_engine(DATABASE_URL)

def update_schema():
    queries = [
        "ALTER TABLE technicians ADD COLUMN IF NOT EXISTS current_jobs INTEGER DEFAULT 0;",
        "ALTER TABLE technicians ADD COLUMN IF NOT EXISTS max_jobs INTEGER DEFAULT 5;"
    ]
    
    with engine.connect() as connection:
        for query in queries:
            print(f"Executing: {query}")
            connection.execute(text(query))
            connection.commit()
    print("Database schema updated successfully.")

if __name__ == "__main__":
    update_schema()
