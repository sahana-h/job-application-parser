import requests
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
import re
from dotenv import load_dotenv
import json

load_dotenv()

class AIJobApplicationParser:
    def __init__(self):
        # Hugging Face Inference API - completely free
        self.api_url = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2"
        self.headers = {"Authorization": f"Bearer {os.getenv('HUGGINGFACE_API_KEY', '')}"}
    
    def parse_job_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse a job-related email and extract structured information
        Returns: {company, role, date_applied, source, status, confidence, reasoning}
        """
        
        # First try simple regex patterns for common ATS emails
        structured_result = self._try_structured_parsing(email_data)
        if structured_result and structured_result['confidence'] > 0.8:
            return structured_result
        
        # If regex fails, use free AI reasoning
        return self._ai_reasoning_parse(email_data)
    
    def _try_structured_parsing(self, email_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Try to parse using regex patterns for common ATS systems"""
        
        subject = email_data.get('subject', '').lower()
        body = email_data.get('body', '').lower()
        sender = email_data.get('sender', '')
        
        # Common ATS patterns
        patterns = {
            'lever': {
                'company_pattern': r'at\s+([a-zA-Z\s&]+)',
                'role_pattern': r'position[:\s]+([a-zA-Z\s]+)',
                'confidence': 0.9
            },
            'greenhouse': {
                'company_pattern': r'([a-zA-Z\s&]+)\s+application',
                'role_pattern': r'([a-zA-Z\s]+)\s+position',
                'confidence': 0.9
            },
            'workday': {
                'company_pattern': r'([a-zA-Z\s&]+)\s+careers',
                'role_pattern': r'([a-zA-Z\s]+)\s+job',
                'confidence': 0.85
            }
        }
        
        # Try to identify ATS system
        ats_system = None
        if 'lever' in sender or 'lever' in body:
            ats_system = 'lever'
        elif 'greenhouse' in sender or 'greenhouse' in body:
            ats_system = 'greenhouse'
        elif 'workday' in sender or 'workday' in body:
            ats_system = 'workday'
        
        if ats_system:
            pattern = patterns[ats_system]
            company_match = re.search(pattern['company_pattern'], subject + ' ' + body)
            role_match = re.search(pattern['role_pattern'], subject + ' ' + body)
            
            if company_match and role_match:
                return {
                    'company': company_match.group(1).strip(),
                    'role': role_match.group(1).strip(),
                    'date_applied': datetime.now(),
                    'source': 'email',
                    'status': 'applied',
                    'confidence': pattern['confidence'],
                    'reasoning': f'Parsed using {ats_system} ATS patterns'
                }
        
        return None
    
    def _ai_reasoning_parse(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Use free AI to reason about unclear emails"""
        
        prompt = f"""
        Analyze this job application email and extract structured information.
        
        Email Subject: {email_data.get('subject', '')}
        Email Sender: {email_data.get('sender', '')}
        Email Body: {email_data.get('body', '')[:1000]}
        
        Instructions:
        1. Identify the company name
        2. Identify the job role/position
        3. Determine the application status
        4. Assess your confidence (0.0 to 1.0)
        5. Explain your reasoning
        
        If information is unclear or missing, explain what you need to know.
        
        Respond in this JSON format:
        {{
            "company": "Company Name or null if unclear",
            "role": "Job Role or null if unclear", 
            "date_applied": "YYYY-MM-DD or null if unclear",
            "source": "email",
            "status": "applied, interviewing, rejected, or unclear",
            "confidence": 0.75,
            "reasoning": "Explain your reasoning and what's unclear"
        }}
        """
        
        try:
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 500,
                    "temperature": 0.1,
                    "return_full_text": False
                }
            }
            
            response = requests.post(self.api_url, headers=self.headers, json=payload)
            
            if response.status_code == 200:
                ai_response = response.json()[0]["generated_text"]
                parsed_data = self._parse_ai_response(ai_response)
                parsed_data['reasoning'] = ai_response
                return parsed_data
            else:
                # Fallback to regex if AI fails
                return self._fallback_parsing(email_data)
                
        except Exception as e:
            return self._fallback_parsing(email_data)
    
    def _fallback_parsing(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback parsing when AI fails"""
        subject = email_data.get('subject', '').lower()
        body = email_data.get('body', '').lower()
        
        # Simple fallback patterns
        company_patterns = [
            r'at\s+([a-zA-Z\s&]+)',
            r'([a-zA-Z\s&]+)\s+application',
            r'([a-zA-Z\s&]+)\s+careers'
        ]
        
        role_patterns = [
            r'([a-zA-Z\s]+)\s+position',
            r'([a-zA-Z\s]+)\s+role',
            r'([a-zA-Z\s]+)\s+engineer'
        ]
        
        company = None
        role = None
        
        for pattern in company_patterns:
            match = re.search(pattern, subject + ' ' + body)
            if match:
                company = match.group(1).strip()
                break
        
        for pattern in role_patterns:
            match = re.search(pattern, subject + ' ' + body)
            if match:
                role = match.group(1).strip()
                break
        
        return {
            'company': company,
            'role': role,
            'date_applied': datetime.now(),
            'source': 'email',
            'status': 'applied' if company or role else 'unclear',
            'confidence': 0.3 if company or role else 0.0,
            'reasoning': 'Fallback parsing used - limited confidence'
        }
    
    def _parse_ai_response(self, ai_response: str) -> Dict[str, Any]:
        """Parse the AI's JSON response"""
        try:
            # Extract JSON from AI response
            json_start = ai_response.find('{')
            json_end = ai_response.rfind('}') + 1
            json_str = ai_response[json_start:json_end]
            
            data = json.loads(json_str)
            
            # Ensure all required fields exist
            required_fields = ['company', 'role', 'date_applied', 'source', 'status', 'confidence']
            for field in required_fields:
                if field not in data:
                    data[field] = None
            
            # Parse date if it exists
            if data.get('date_applied') and isinstance(data['date_applied'], str):
                try:
                    data['date_applied'] = datetime.strptime(data['date_applied'], '%Y-%m-%d')
                except:
                    data['date_applied'] = datetime.now()
            
            return data
            
        except Exception as e:
            return {
                'company': None,
                'role': None,
                'date_applied': datetime.now(),
                'source': 'email',
                'status': 'unclear',
                'confidence': 0.0
            }

# Test the AI service
if __name__ == "__main__":
    # Test with sample email data
    test_email = {
        'subject': 'Thank you for applying to Software Engineer position',
        'sender': 'noreply@company.com',
        'body': 'We received your application for the Software Engineer role at TechCorp. We will review and get back to you soon.'
    }
    
    parser = AIJobApplicationParser()
    result = parser.parse_job_email(test_email)
    print("AI Parsing Result:")
    print(result)