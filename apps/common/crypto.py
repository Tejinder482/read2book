from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
import base64
import hashlib


def _fernet() -> Fernet:
    raw = settings.FIELD_ENCRYPTION_KEY.encode("utf-8")
    # Derive a stable 32-byte url-safe key from any string secret.
    digest = hashlib.sha256(raw).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_value(value: str) -> str:
    if not value:
        return ""
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_value(token: str) -> str:
    if not token:
        return ""
    try:
        return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Unable to decrypt value") from exc


def last4(value: str) -> str:
    if not value:
        return ""
    return value[-4:] if len(value) >= 4 else value
