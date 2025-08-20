from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..models import JobApplication
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

# Pydantic model for API requests/responses
class JobApplicationCreate(BaseModel):
    company: str
    role: str
    date_applied: datetime
    source: str = "email"
    status: str = "applied"
    confidence: float = 0.0
    email_snippet: str = ""

class JobApplicationResponse(BaseModel):
    id: int
    company: str
    role: str
    date_applied: datetime
    source: str
    status: str
    confidence: float
    email_snippet: str
    created_at: datetime
    updated_at: Optional[datetime] = None  # Make this optional

    class Config:
        from_attributes = True

@router.post("/applications/", response_model=JobApplicationResponse)
async def create_application(application: JobApplicationCreate, db: Session = Depends(get_db)):
    try:
        db_application = JobApplication(**application.dict())
        db.add(db_application)
        db.commit()
        db.refresh(db_application)
        return db_application
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/applications/", response_model=List[JobApplicationResponse])
async def get_applications(db: Session = Depends(get_db)):
    return db.query(JobApplication).all()

@router.get("/applications/{application_id}", response_model=JobApplicationResponse)
async def get_application(application_id: int, db: Session = Depends(get_db)):
    application = db.query(JobApplication).filter(JobApplication.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    return application

# Add this new endpoint to your existing file
@router.post("/process-emails/")
async def process_emails(days_back: int = 7, db: Session = Depends(get_db)):
    """Process new emails and extract job applications"""
    from ..email_processor import EmailProcessor
    
    processor = EmailProcessor()
    results = processor.process_new_emails(db, days_back=days_back)
    
    return {
        "message": "Email processing completed",
        "results": results
    }