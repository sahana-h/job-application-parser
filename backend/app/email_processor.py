from typing import List, Dict, Any
from .gmail_service import GmailService
from .ai_service import AIJobApplicationParser
from .models import JobApplication
from sqlalchemy.orm import Session
from datetime import datetime

class EmailProcessor:
    def __init__(self):
        self.gmail_service = GmailService()
        self.ai_parser = AIJobApplicationParser()
    
    def process_new_emails(self, db: Session, days_back: int = 7) -> Dict[str, Any]:
        """
        Main function: fetch emails, parse them, and save to database
        Returns: summary of what was processed
        """
        
        # Step 1: Fetch job-related emails from Gmail
        print("Fetching emails from Gmail...")
        emails = self.gmail_service.search_job_emails(days_back=days_back)
        print(f"Found {len(emails)} job-related emails")
        
        results = {
            'total_emails': len(emails),
            'processed': 0,
            'saved': 0,
            'errors': 0,
            'details': []
        }
        
        for email_data in emails:
            try:
                # Step 2: Parse email with AI
                parsed_data = self.ai_parser.parse_job_email(email_data)
                results['processed'] += 1
                
                # Step 3: Check if we have enough info to save
                if self._should_save_application(parsed_data):
                    # Step 4: Save to database
                    saved_app = self._save_application(db, parsed_data, email_data)
                    if saved_app:
                        results['saved'] += 1
                        results['details'].append({
                            'email_id': email_data['id'],
                            'company': parsed_data.get('company'),
                            'role': parsed_data.get('role'),
                            'confidence': parsed_data.get('confidence'),
                            'status': 'saved'
                        })
                    else:
                        results['errors'] += 1
                        results['details'].append({
                            'email_id': email_data['id'],
                            'error': 'Failed to save to database',
                            'status': 'error'
                        })
                else:
                    # Not enough info - flag for manual review
                    results['details'].append({
                        'email_id': email_data['id'],
                        'company': parsed_data.get('company'),
                        'role': parsed_data.get('role'),
                        'confidence': parsed_data.get('confidence'),
                        'reasoning': parsed_data.get('reasoning'),
                        'status': 'needs_review'
                    })
                
            except Exception as e:
                results['errors'] += 1
                results['details'].append({
                    'email_id': email_data.get('id', 'unknown'),
                    'error': str(e),
                    'status': 'error'
                })
                print(f"Error processing email: {e}")
        
        return results
    
    def _should_save_application(self, parsed_data: Dict[str, Any]) -> bool:
        """
        Determine if we have enough confidence to save automatically
        """
        # Require at least company and role
        has_company = parsed_data.get('company') and parsed_data.get('company') != 'null'
        has_role = parsed_data.get('role') and parsed_data.get('role') != 'null'
        
        # Require reasonable confidence
        confidence = parsed_data.get('confidence', 0.0)
        min_confidence = 0.6
        
        return has_company and has_role and confidence >= min_confidence
    
    def _save_application(self, db: Session, parsed_data: Dict[str, Any], email_data: Dict[str, Any]) -> JobApplication:
        """
        Save parsed application to database
        """
        try:
            # Create new job application
            job_app = JobApplication(
                company=parsed_data.get('company'),
                role=parsed_data.get('role'),
                date_applied=parsed_data.get('date_applied') or datetime.now(),
                source='email',
                status=parsed_data.get('status', 'applied'),
                confidence=parsed_data.get('confidence', 0.0),
                email_snippet=email_data.get('body', '')[:500]  # Store first 500 chars
            )
            
            db.add(job_app)
            db.commit()
            db.refresh(job_app)
            
            print(f"Saved application: {job_app.company} - {job_app.role}")
            return job_app
            
        except Exception as e:
            db.rollback()
            print(f"Failed to save application: {e}")
            return None

# Test the email processor
if __name__ == "__main__":
    from .database import SessionLocal
    
    processor = EmailProcessor()
    db = SessionLocal()
    
    try:
        results = processor.process_new_emails(db, days_back=7)
        print("\nProcessing Results:")
        print(f"Total emails: {results['total_emails']}")
        print(f"Processed: {results['processed']}")
        print(f"Saved: {results['saved']}")
        print(f"Errors: {results['errors']}")
        
        print("\nDetails:")
        for detail in results['details']:
            print(f"- {detail}")
            
    finally:
        db.close()