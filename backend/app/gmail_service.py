import os
import base64
import email
from typing import List, Dict, Any
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json
from datetime import datetime, timedelta

class GmailService:
    def __init__(self):
        self.SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
        self.creds = None
        self.service = None
        
    def authenticate(self):
        """Authenticate with Gmail API"""
        # Load existing credentials
        if os.path.exists('token.json'):
            self.creds = Credentials.from_authorized_user_file('token.json', self.SCOPES)
        
        # If no valid credentials, let user log in
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', self.SCOPES)
                self.creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open('token.json', 'w') as token:
                token.write(self.creds.to_json())
        
        self.service = build('gmail', 'v1', credentials=self.creds)
        return self.service
    
    def search_job_emails(self, days_back: int = 7) -> List[Dict[str, Any]]:
        """Search for job-related emails in the last N days"""
        if not self.service:
            self.authenticate()
        
        # Search query for job-related emails
        query = f'after:{(datetime.now() - timedelta(days=days_back)).strftime("%Y/%m/%d")} (subject:"application" OR subject:"apply" OR subject:"thank you for applying" OR subject:"application received")'
        
        try:
            results = self.service.users().messages().list(userId='me', q=query).execute()
            messages = results.get('messages', [])
            
            job_emails = []
            for message in messages[:10]:  # Limit to 10 for testing
                msg = self.service.users().messages().get(userId='me', id=message['id']).execute()
                email_data = self._parse_email(msg)
                if email_data:
                    job_emails.append(email_data)
            
            return job_emails
            
        except HttpError as error:
            print(f'An error occurred: {error}')
            return []
    
    def _parse_email(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Parse email content to extract relevant information"""
        headers = message['payload']['headers']
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
        date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
        
        # Extract email body
        body = self._get_email_body(message['payload'])
        
        return {
            'id': message['id'],
            'subject': subject,
            'sender': sender,
            'date': date,
            'body': body,
            'thread_id': message.get('threadId', '')
        }
    
    def _get_email_body(self, payload: Dict[str, Any]) -> str:
        """Extract email body text"""
        if 'body' in payload and payload['body'].get('data'):
            return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
        elif 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if part['body'].get('data'):
                        return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
        return ""

# Test the service
if __name__ == "__main__":
    gmail = GmailService()
    emails = gmail.search_job_emails(days_back=7)
    print(f"Found {len(emails)} job-related emails")
    for email in emails:
        print(f"Subject: {email['subject']}")
        print(f"From: {email['sender']}")
        print("---")