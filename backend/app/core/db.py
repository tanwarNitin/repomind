from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
import datetime
from datetime import timezone

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
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(timezone.utc))

class Repo(Base):
    __tablename__ = "repos"
    
    repo_id = Column(String, primary_key=True, index=True)
    source = Column(String)
    path = Column(String)
    files_indexed = Column(Integer, default=0)
    symbols_indexed = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(timezone.utc))

class Digest(Base):
    __tablename__ = "digests"
    
    id = Column(Integer, primary_key=True, index=True)
    repo_id = Column(String, index=True)
    markdown_report = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(timezone.utc))

Base.metadata.create_all(bind=engine)
