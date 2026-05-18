import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the project root to sys.path to allow imports from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from app.models import Technician
from app.validation import get_workload_validation_status

load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'backend', '.env'))
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def get_db_data():
    db = SessionLocal()
    try:
        techs = db.query(Technician).all()
        if not techs:
            print("No technicians found in database.")
            return

        for tech in techs:
            status = get_workload_validation_status(tech)
            import json
            print(json.dumps(status, indent=2))
            print("-" * 30)
    finally:
        db.close()

if __name__ == "__main__":
    get_db_data()
