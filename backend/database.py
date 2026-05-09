from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os

# Using a default local sqlite address to ensure it works without external dependencies.
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./smartshell.db")

# Allow fallback to sqlite for testing if DATABASE_URL is set to sqlite
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
