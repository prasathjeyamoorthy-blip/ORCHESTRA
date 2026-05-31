# agent/document_access.py
"""
Document access module with OTP verification for agent.
Handles secure document retrieval with user consent via OTP.
"""

import os
import requests
from typing import Dict, List, Optional

# Backend API base URL
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:4000")


class DocumentAccessManager:
    """Manages OTP-protected document access for the agent."""
    
    def __init__(self, user_token: str):
        """
        Initialize document access manager.
        
        Args:
            user_token: JWT token for the user
        """
        self.user_token = user_token
        self.headers = {
            "Authorization": f"Bearer {user_token}",
            "Content-Type": "application/json"
        }
        self.otp_requested = False
        self.otp_verified = False
        self.documents = []
    
    def request_otp(self) -> Dict:
        """
        Request OTP to be sent to user's phone for document access.
        
        Returns:
            dict: Response with OTP request status
        """
        try:
            response = requests.post(
                f"{BACKEND_URL}/api/uploads/agent/request-access",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.otp_requested = True
                return {
                    "success": True,
                    "message": data.get("message", "OTP sent successfully"),
                    "phone_last_4": data.get("phone_last_4"),
                    "expires_in_minutes": data.get("expires_in_minutes", 10),
                    "file_count": data.get("file_count", 0)
                }
            elif response.status_code == 400:
                error_data = response.json()
                if error_data.get("requires_phone"):
                    return {
                        "success": False,
                        "error": "no_phone",
                        "message": "User has no phone number registered. Please add a phone number first."
                    }
                return {
                    "success": False,
                    "error": "bad_request",
                    "message": error_data.get("error", "Invalid request")
                }
            elif response.status_code == 404:
                return {
                    "success": False,
                    "error": "no_documents",
                    "message": "No documents found for this user."
                }
            else:
                return {
                    "success": False,
                    "error": "request_failed",
                    "message": f"Failed to request OTP: {response.status_code}"
                }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": "network_error",
                "message": f"Network error: {str(e)}"
            }
    
    def verify_otp(self, otp: str) -> Dict:
        """
        Verify OTP and get access to user documents.
        
        Args:
            otp: 6-digit OTP code from user
        
        Returns:
            dict: Response with verification status and document list
        """
        try:
            response = requests.post(
                f"{BACKEND_URL}/api/uploads/agent/verify-and-access",
                headers=self.headers,
                json={"otp": otp},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.otp_verified = True
                self.documents = data.get("documents", [])
                return {
                    "success": True,
                    "verified": True,
                    "message": data.get("message", "OTP verified successfully"),
                    "documents": self.documents,
                    "access_granted_at": data.get("access_granted_at"),
                    "access_expires_at": data.get("access_expires_at")
                }
            elif response.status_code == 401:
                error_data = response.json()
                return {
                    "success": False,
                    "error": "invalid_otp",
                    "message": error_data.get("error", "Invalid OTP"),
                    "remaining_attempts": error_data.get("remaining_attempts")
                }
            elif response.status_code == 429:
                return {
                    "success": False,
                    "error": "too_many_attempts",
                    "message": "Too many failed attempts. Please request a new OTP."
                }
            else:
                return {
                    "success": False,
                    "error": "verification_failed",
                    "message": f"Verification failed: {response.status_code}"
                }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": "network_error",
                "message": f"Network error: {str(e)}"
            }
    
    def get_document(self, document_id: str) -> Optional[bytes]:
        """
        Get document content after OTP verification.
        
        Args:
            document_id: ID of the document to retrieve
        
        Returns:
            bytes: Document content, or None if failed
        """
        if not self.otp_verified:
            print("[ERROR] Cannot access document: OTP not verified")
            return None
        
        try:
            response = requests.get(
                f"{BACKEND_URL}/api/uploads/agent/document/{document_id}",
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.content
            elif response.status_code == 403:
                error_data = response.json()
                if error_data.get("requires_otp"):
                    print("[ERROR] OTP verification expired. Please verify OTP again.")
                else:
                    print(f"[ERROR] Access denied: {error_data.get('error')}")
                return None
            else:
                print(f"[ERROR] Failed to get document: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Network error: {e}")
            return None
    
    def get_document_list(self) -> List[Dict]:
        """
        Get list of documents available after OTP verification.
        
        Returns:
            list: List of document metadata
        """
        return self.documents if self.otp_verified else []
    
    def is_access_granted(self) -> bool:
        """Check if agent has access to documents (OTP verified)."""
        return self.otp_verified
    
    def reset(self):
        """Reset OTP verification state."""
        self.otp_requested = False
        self.otp_verified = False
        self.documents = []


# ── Helper functions for agent integration ────────────────────────────────────

def request_document_access(user_token: str) -> Dict:
    """
    Request OTP for document access.
    
    Args:
        user_token: JWT token for the user
    
    Returns:
        dict: Response with OTP request status
    """
    manager = DocumentAccessManager(user_token)
    return manager.request_otp()


def verify_document_access(user_token: str, otp: str) -> Dict:
    """
    Verify OTP and get document access.
    
    Args:
        user_token: JWT token for the user
        otp: 6-digit OTP code
    
    Returns:
        dict: Response with verification status and documents
    """
    manager = DocumentAccessManager(user_token)
    return manager.verify_otp(otp)


def get_user_documents(user_token: str, document_id: Optional[str] = None) -> Optional[bytes]:
    """
    Get document content (requires prior OTP verification).
    
    Args:
        user_token: JWT token for the user
        document_id: ID of document to retrieve
    
    Returns:
        bytes: Document content, or None if failed
    """
    manager = DocumentAccessManager(user_token)
    if document_id:
        return manager.get_document(document_id)
    return None
