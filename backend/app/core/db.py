from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
import datetime

DATABASE_URL = "sqlite:///./repomind.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class TriageRun(Base):
    __tablename__ = "triage_runs"

    id = Column(Integer, primary_key=True, index=True)
    repo_url = Column(String, index=True)
    issue_text = Column(Text)
    status = Column(String)
    patch_diff = Column(Text, nullable=True)
    verification_result = Column(Text, nullable=True)
    tokens_used = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

Base.metadata.create_all(bind=engine)
