from __future__ import annotations
import base64
from cryptography.fernet import Fernet
import hashlib


def _get_fernet(secret_key: str) -> Fernet:
    """Derive a Fernet key from the app secret key."""
    key_bytes = hashlib.sha256(secret_key.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def encrypt_url(url: str, secret_key: str) -> str:
    """Encrypt a database URL (or any string) for at-rest storage."""
    f = _get_fernet(secret_key)
    return f.encrypt(url.encode()).decode()


def decrypt_url(encrypted: str, secret_key: str) -> str:
    """Decrypt a previously encrypted URL."""
    f = _get_fernet(secret_key)
    return f.decrypt(encrypted.encode()).decode()
