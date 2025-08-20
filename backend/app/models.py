from sqlalchemy import Column, Integer, String, DateTime, Float, Text
from sqlalchemy.sql import func
from .database import Base

class JobApplication(Base):
    __tablename__ = "job_applications"

    id = Column(Integer, primary_key=True, index=True)
    company = Column(String, nullable=False)
    role = Column(String, nullable=False)
    date_applied = Column(DateTime, nullable=False)
    source = Column(String)  # "email", "linkedin", "company_website"
    status = Column(String, default="applied")  # "applied", "interviewing", "rejected", "accepted"
    confidence = Column(Float, default=0.0)  # 0.0 to 1.0
    email_snippet = Column(Text)  # Small part of email for reference
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())