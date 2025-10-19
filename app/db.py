# app/db.py

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from dotenv import load_dotenv

# Load environment variables (optional for local dev)
load_dotenv()

# This will now correctly load the URL from your .env file
DATABASE_URL = os.getenv("DATABASE_URL")

# A small check to ensure it's not None
if DATABASE_URL is None:
    raise ValueError("DATABASE_URL environment variable not set. Please create a .env file.")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    # The check for 'sqlite' is no longer the primary path but is good practice
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()