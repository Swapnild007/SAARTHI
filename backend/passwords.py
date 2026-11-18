"""Versioned owner password hashes shared by setup and sign-in."""
import hashlib
import hmac
import re
import secrets

PATTERN = r"scrypt-v1\$[a-f0-9]{32}\$[a-f0-9]{64}"


def hash_password(password: str) -> str:
    if not 24 <= len(password) <= 512:
        raise ValueError("Choose a password between 24 and 512 characters.")
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1, dklen=32)
    return f"scrypt-v1${salt}${digest.hex()}"


def valid_hash(value: str) -> bool:
    return re.fullmatch(PATTERN, value) is not None


def verify_password(password: str, encoded: str) -> bool:
    if not valid_hash(encoded) or len(password) > 512:
        return False
    _, salt, expected = encoded.split("$")
    actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1, dklen=32)
    return hmac.compare_digest(actual.hex(), expected)
