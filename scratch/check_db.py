import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

print(f"Connecting to: {DATABASE_URL}")
engine = create_engine(DATABASE_URL)

try:
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"Tables found: {tables}")
    
    if not tables:
        print("No tables found. Attempting to create them...")
        from app.database import Base
        from app.models import Job, Technician
        Base.metadata.create_all(bind=engine)
        tables = inspector.get_table_names()
        print(f"Tables after create_all: {tables}")
except Exception as e:
    print(f"Error: {e}")
