import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Load environment variables
load_dotenv(dotenv_path="backend/.env")
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

from backend.app.models_legacy import Job

db = SessionLocal()

# Fix Job 14
job14 = db.query(Job).filter(Job.id == 14).first()
if job14:
    job14.status = "ASSIGNED"
    db.commit()
    print("Fixed Job 14 status to ASSIGNED")
else:
    print("Job 14 not found")
