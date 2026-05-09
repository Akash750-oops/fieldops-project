import sys
import os

# Add the project root to sys.path to allow imports from 'app'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import engine, Base
from app.models import Technician

def recreate_technicians_table():
    print("Dropping 'technicians' table...")
    Technician.__table__.drop(engine, checkfirst=True)
    
    print("Creating 'technicians' table...")
    Technician.__table__.create(engine)
    
    print("Table 'technicians' recreated successfully.")

if __name__ == "__main__":
    recreate_technicians_table()
