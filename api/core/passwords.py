"""
api/core/passwords.py
Enterprise Password Security Module for Administrator Accounts.

Implements OWASP-compliant PBKDF2-HMAC-SHA256 password hashing (600,000 rounds),
cryptographic salt generation, constant-time verification, and password strength validation.
"""

import os
import re
import hmac
import hashlib
from typing import Tuple

PBKDF2_ROUNDS = 600_000
SALT_SIZE_BYTES = 16


def hash_password(raw_password: str) -> str:
    """
    Hashes a plaintext password using PBKDF2-HMAC-SHA256 with a unique 16-byte salt.
    Returns format: '<salt_hex>:<hash_hex>'
    """
    if not raw_password:
        raise ValueError("Password cannot be empty.")
    salt = os.urandom(SALT_SIZE_BYTES)
    derived = hashlib.pbkdf2_hmac(
        hash_name="sha256",
        password=raw_password.encode("utf-8"),
        salt=salt,
        iterations=PBKDF2_ROUNDS,
    )
    return f"{salt.hex()}:{derived.hex()}"


def verify_password(raw_password: str, hashed_value: str) -> bool:
    """
    Verifies a plaintext password against a stored '<salt_hex>:<hash_hex>' string.
    Uses constant-time comparison to prevent timing attacks.
    """
    if not raw_password or not hashed_value or ":" not in hashed_value:
        return False
    try:
        salt_hex, hash_hex = hashed_value.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(hash_hex)
        computed_hash = hashlib.pbkdf2_hmac(
            hash_name="sha256",
            password=raw_password.encode("utf-8"),
            salt=salt,
            iterations=PBKDF2_ROUNDS,
        )
        return hmac.compare_digest(expected_hash, computed_hash)
    except Exception:
        return False


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    Validates enterprise password complexity:
    - At least 8 characters
    - At least one uppercase letter (A-Z)
    - At least one lowercase letter (a-z)
    - At least one digit (0-9)
    - At least one special symbol (!@#$%^&* etc.)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter (A-Z)."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter (a-z)."
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one digit (0-9)."
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", password):
        return False, "Password must contain at least one special symbol (e.g. !@#$%^&*)."
    return True, "Password meets complexity requirements."
