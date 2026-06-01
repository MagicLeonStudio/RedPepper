"""RedPepper security module.

Implements password hashing (PBKDF2-HMAC-SHA256), password-strength
validation, and AES-256-GCM encrypted database export / import.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import struct
import secrets
import string
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAGIC = b"REPPER"
VERSION = struct.pack("<I", 1)

_SALT_LENGTH = 32
_HASH_ITERATIONS = 600_000
_KEY_LENGTH = 32  # AES-256
_NONCE_LENGTH = 12
_TAG_LENGTH = 16


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------


def create_password(plain_password: str) -> dict:
    """Hash a plain-text password using PBKDF2-HMAC-SHA256.

    Returns a dict with:
        - ``password_hash`` (hex): 128-char hex string (64 bytes).
        - ``salt`` (hex): 64-char hex string (32 bytes).
    """
    salt = secrets.token_bytes(_SALT_LENGTH)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        plain_password.encode("utf-8"),
        salt,
        _HASH_ITERATIONS,
        dklen=64,
    )
    return {
        "password_hash": password_hash.hex(),
        "salt": salt.hex(),
    }


def verify_password(plain_password: str, stored_hash: str, salt: str) -> bool:
    """Verify a plain-text password against a stored PBKDF2 hash.

    Parameters
    ----------
    plain_password:
        The password supplied by the user.
    stored_hash:
        The previously stored hash (hex string, 128 chars).
    salt:
        The previously stored salt (hex string, 64 chars).

    Returns
    -------
    bool
        ``True`` if the password matches.
    """
    salt_bytes = bytes.fromhex(salt)
    expected_hash = hashlib.pbkdf2_hmac(
        "sha256",
        plain_password.encode("utf-8"),
        salt_bytes,
        _HASH_ITERATIONS,
        dklen=64,
    )
    return hmac.compare_digest(expected_hash.hex(), stored_hash)


# ---------------------------------------------------------------------------
# Password-strength checker
# ---------------------------------------------------------------------------


def check_password_strength(password: str) -> dict:
    """Evaluate the strength of a password.

    Returns a dict with:
        - ``valid`` (bool): Whether the password meets minimum requirements.
        - ``score`` (int): 0–4 rating (0 = very weak, 4 = very strong).
        - ``message`` (str): Human-readable feedback.
    """
    score = 0
    messages: list[str] = []

    if len(password) >= 8:
        score += 1
    else:
        messages.append("Password must be at least 8 characters long.")

    if len(password) >= 12:
        score += 1

    if re.search(r"[A-Z]", password):
        score += 1
    else:
        messages.append("Add uppercase letters.")

    if re.search(r"[a-z]", password):
        score += 1
    else:
        messages.append("Add lowercase letters.")

    if re.search(r"\d", password):
        score += 1
    else:
        messages.append("Add digits.")

    if re.search(rf"[{re.escape(string.punctuation)}]", password):
        score += 1
    else:
        messages.append("Add special characters.")

    # Clamp score to 0–4
    score = max(0, min(4, score - 1))

    if score >= 3:
        msg = "Password strength: strong."
    elif score == 2:
        msg = "Password strength: moderate. " + " ".join(messages)
    elif score == 1:
        msg = "Password strength: weak. " + " ".join(messages)
    else:
        msg = "Password strength: very weak. " + " ".join(messages)

    return {
        "valid": score >= 2,
        "score": score,
        "message": msg,
    }


# ---------------------------------------------------------------------------
# AES-256-GCM key derivation
# ---------------------------------------------------------------------------


def _derive_key(password: str, salt: bytes) -> bytes:
    """Derive a 32-byte AES key from *password* and *salt* using PBKDF2."""
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        _HASH_ITERATIONS,
        dklen=_KEY_LENGTH,
    )


# ---------------------------------------------------------------------------
# Encrypted database export / import
# ---------------------------------------------------------------------------


def export_database(db_path: str, password: str, output_path: str) -> None:
    """Encrypt a SQLite database file to a ``.redpepper`` archive.

    The file format is::

        MAGIC (6 bytes) + VERSION (4 bytes) + salt (32 bytes) + nonce (12 bytes)
        + ciphertext + tag (16 bytes, appended by AESGCM)

    Parameters
    ----------
    db_path:
        Path to the source SQLite file.
    password:
        Password used to derive the encryption key.
    output_path:
        Destination path for the ``.redpepper`` file.
    """
    db_path_obj = Path(db_path)
    if not db_path_obj.exists():
        raise FileNotFoundError(f"Database file not found: {db_path}")

    plaintext = db_path_obj.read_bytes()

    salt = secrets.token_bytes(_SALT_LENGTH)
    nonce = secrets.token_bytes(_NONCE_LENGTH)
    key = _derive_key(password, salt)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)

    out = Path(output_path)
    out.write_bytes(
        MAGIC + VERSION + salt + nonce + ciphertext
    )


def import_database(redpepper_path: str, password: str, output_db_path: str) -> None:
    """Decrypt a ``.redpepper`` archive back to a SQLite database file.

    Parameters
    ----------
    redpepper_path:
        Path to the ``.redpepper`` file.
    password:
        Password used to derive the decryption key.
    output_db_path:
        Destination path for the restored SQLite file.
    """
    rp = Path(redpepper_path)
    if not rp.exists():
        raise FileNotFoundError(f"RedPepper file not found: {redpepper_path}")

    data = rp.read_bytes()

    # Unpack header
    magic = data[: len(MAGIC)]
    if magic != MAGIC:
        raise ValueError("Invalid RedPepper file (wrong magic bytes).")

    version = data[len(MAGIC) : len(MAGIC) + 4]
    if version != VERSION:
        raise ValueError("Unsupported RedPepper file version.")

    offset = len(MAGIC) + 4
    salt = data[offset : offset + _SALT_LENGTH]
    offset += _SALT_LENGTH
    nonce = data[offset : offset + _NONCE_LENGTH]
    offset += _NONCE_LENGTH
    ciphertext = data[offset:]

    key = _derive_key(password, salt)
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)

    out = Path(output_db_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(plaintext)
