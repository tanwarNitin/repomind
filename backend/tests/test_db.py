import pytest
from app.core.db import SessionLocal, TriageRun

def test_db_triage_run():
    session = SessionLocal()
    
    new_run = TriageRun(
        repo_url="https://github.com/example/repo",
        issue_text="Test issue",
        status="pending"
    )
    
    session.add(new_run)
    session.commit()
    
    fetched_run = session.query(TriageRun).filter(TriageRun.repo_url == "https://github.com/example/repo").first()
    
    assert fetched_run is not None
    assert fetched_run.issue_text == "Test issue"
    assert fetched_run.status == "pending"
    
    session.delete(fetched_run)
    session.commit()
    session.close()
