"""
app/services/auth_service.py
============================

Responsibility:  Handles password hashing and basic authentication verification logic.

Pipeline Position: Business Logic Layer
"""

import hashlib
import hmac

def hash_password(password: str) -> str:
    """Hashes a password for basic storage."""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Safely compares passwords to prevent timing attacks."""
    return hmac.compare_digest(hash_password(plain_password), hashed_password)