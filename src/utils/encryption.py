import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class TokenEncryption:
    """Handles encryption and decryption of GitHub access tokens."""
    
    def __init__(self, encryption_key: str):
        """Initialize with encryption key from environment or parameter store."""
        self._fernet = Fernet(self._derive_key(encryption_key))
    
    def _derive_key(self, password: str) -> bytes:
        """Derive encryption key from password using PBKDF2."""
        # Use a fixed salt for consistency (in production, consider per-user salts)
        salt = b'myfav-coworker-salt'
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def encrypt_token(self, token: str) -> str:
        """Encrypt a GitHub access token."""
        encrypted_token = self._fernet.encrypt(token.encode())
        return base64.urlsafe_b64encode(encrypted_token).decode()
    
    def decrypt_token(self, encrypted_token: str) -> str:
        """Decrypt a GitHub access token."""
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_token.encode())
        decrypted_token = self._fernet.decrypt(encrypted_bytes)
        return decrypted_token.decode()


def get_encryption_key() -> str:
    """Get encryption key from environment variable or AWS Parameter Store."""
    # First try environment variable (for local development)
    key = os.getenv('GITHUB_TOKEN_ENCRYPTION_KEY')
    if key:
        return key
    
    # In production, get from AWS Parameter Store
    import boto3
    ssm = boto3.client('ssm')
    try:
        response = ssm.get_parameter(
            Name='/myfav-coworker/github-token-encryption-key',
            WithDecryption=True
        )
        return response['Parameter']['Value']
    except Exception as e:
        raise RuntimeError(f"Failed to retrieve encryption key: {e}")


def create_token_encryptor() -> TokenEncryption:
    """Create a TokenEncryption instance with the appropriate key."""
    encryption_key = get_encryption_key()
    return TokenEncryption(encryption_key)
