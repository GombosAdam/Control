"""
NAV Online Számla 3.0 cryptographic utilities.

- Request signature: SHA3-512(requestId + timestamp + SHA-512(signatureKey))
- Password encryption: AES-128-ECB(password, replacementKey)
"""

import hashlib
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend


def sha512_hex(data: str) -> str:
    """SHA-512 hash of a UTF-8 string, returned as uppercase hex."""
    return hashlib.sha512(data.encode("utf-8")).hexdigest().upper()


def sha3_512_hex(data: str) -> str:
    """SHA3-512 hash of a UTF-8 string, returned as uppercase hex."""
    return hashlib.sha3_512(data.encode("utf-8")).hexdigest().upper()


def compute_request_signature(request_id: str, timestamp: str, signature_key: str) -> str:
    """
    Compute the NAV request signature.
    signature = SHA3-512(requestId + timestamp + SHA-512(signatureKey))
    """
    signature_key_hash = sha512_hex(signature_key)
    raw = request_id + timestamp + signature_key_hash
    return sha3_512_hex(raw)


def encrypt_password_aes128_ecb(password: str, replacement_key: str) -> str:
    """
    Encrypt password with AES-128-ECB using the replacement key.
    The replacement key is expected as a 128-bit (32 hex char) string.
    Returns the encrypted bytes as uppercase hex.
    """
    key_bytes = bytes.fromhex(replacement_key)
    # PKCS5 padding to 16-byte blocks
    password_bytes = password.encode("utf-8")
    pad_len = 16 - (len(password_bytes) % 16)
    padded = password_bytes + bytes([pad_len] * pad_len)

    cipher = Cipher(algorithms.AES(key_bytes), modes.ECB(), backend=default_backend())
    encryptor = cipher.encryptor()
    encrypted = encryptor.update(padded) + encryptor.finalize()
    return encrypted.hex().upper()
