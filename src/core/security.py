import os

from cryptography.fernet import Fernet

ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")


def _get_fernet() -> Fernet:
    if not ENCRYPTION_KEY:
        raise RuntimeError("ENCRYPTION_KEY is not set")
    return Fernet(ENCRYPTION_KEY.encode())


def encrypt_token(raw: str) -> bytes:
    return _get_fernet().encrypt(raw.encode())


def decrypt_token(encrypted: bytes) -> str:
    return _get_fernet().decrypt(encrypted).decode()
