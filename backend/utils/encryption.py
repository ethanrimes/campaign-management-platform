# backend/utils/encryption.py

import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Optional

class TokenEncryption:
    """Utility class for encrypting/decrypting sensitive tokens"""
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize encryption with a key from environment or parameter
        
        Args:
            encryption_key: Optional encryption key, defaults to env var
        """
        key = encryption_key or os.getenv("ENCRYPTION_KEY")
        
        if not key:
            raise ValueError(
                "No encryption key found. Please set ENCRYPTION_KEY in your .env file. "
                "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        
        # If key is a simple string, derive a proper key from it
        if len(key) < 44:  # Fernet keys are 44 chars when base64 encoded
            # Use PBKDF2HMAC to derive a key from the password
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'stable_salt_v1',  # Using stable salt for consistency
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(key.encode()))
        else:
            key = key.encode() if isinstance(key, str) else key
        
        self.cipher = Fernet(key)
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string
        
        Args:
            plaintext: The string to encrypt
            
        Returns:
            Base64-encoded encrypted string
        """
        if not plaintext:
            return ""
        
        encrypted = self.cipher.encrypt(plaintext.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt an encrypted string
        
        Args:
            ciphertext: Base64-encoded encrypted string
            
        Returns:
            Decrypted plaintext string
        """
        if not ciphertext:
            return ""
        
        try:
            encrypted = base64.urlsafe_b64decode(ciphertext.encode())
            decrypted = self.cipher.decrypt(encrypted)
            return decrypted.decode()
        except Exception as e:
            raise ValueError(f"Failed to decrypt token: {e}")
    
    @staticmethod
    def generate_key() -> str:
        """Generate a new Fernet encryption key"""
        return Fernet.generate_key().decode()


# Singleton instance for easy import
_encryption_instance = None

def get_encryption() -> TokenEncryption:
    """Get or create the singleton encryption instance"""
    global _encryption_instance
    if _encryption_instance is None:
        _encryption_instance = TokenEncryption()
    return _encryption_instance