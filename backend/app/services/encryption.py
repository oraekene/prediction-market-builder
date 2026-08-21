import base64
import logging
import os

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.config import settings

logger = logging.getLogger(__name__)

_KDF_ITERATIONS = 600_000
_VERSION_PREFIX = "v1"


class EncryptionService:
    """Encrypts secrets at rest.

    Key derivation: PBKDF2-HMAC-SHA256 over ENCRYPTION_KEY with a random
    16-byte salt per ciphertext, stored alongside the Fernet token as
    ``v1:<salt_b64>:<token>``.
    """

    def __init__(self, key: str | None = None):
        secret = (key if key is not None else settings.encryption_key)
        if not secret:
            raise ValueError("EncryptionService requires a non-empty key (ENCRYPTION_KEY)")
        self._secret = secret.encode()

    def _fernet_for(self, salt: bytes) -> Fernet:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=_KDF_ITERATIONS,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self._secret))
        return Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        salt = os.urandom(16)
        token = self._fernet_for(salt).encrypt(plaintext.encode())
        return f"{_VERSION_PREFIX}:{base64.urlsafe_b64encode(salt).decode()}:{token.decode()}"

    def decrypt(self, ciphertext: str) -> str:
        try:
            version, salt_b64, token = ciphertext.split(":", 2)
        except ValueError as exc:
            raise ValueError("Invalid ciphertext format") from exc
        if version != _VERSION_PREFIX:
            raise ValueError(f"Unsupported ciphertext version: {version!r}")
        salt = base64.urlsafe_b64decode(salt_b64.encode())
        try:
            return self._fernet_for(salt).decrypt(token.encode()).decode()
        except InvalidToken as exc:
            raise ValueError("Invalid ciphertext or wrong key") from exc


encryption_service = EncryptionService()
