# db.py
import os, urllib.parse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

db_user = os.getenv("DB_USER", "sample_user")
db_pass = urllib.parse.quote_plus(os.getenv("DB_PASSWORD", "sample_password"))
db_host = os.getenv("DB_HOST", "edge2-mysql")
db_port = os.getenv("DB_PORT", "3306")
db_name = os.getenv("DB_NAME", "sample_db")

SQLALCHEMY_DATABASE_URI = f"mysql+mysqlconnector://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

engine = create_engine(SQLALCHEMY_DATABASE_URI, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
