from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine
from app.routes import jobs

Base.metadata.create_all(bind=engine)

app = FastAPI(title="FieldOps Commander API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router)


@app.get("/")
def root():
    return {"message": "FieldOps Commander backend is running"}