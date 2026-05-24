import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

logger = logging.getLogger(__name__)


def _derive_key(secret: str) -> bytes:
    return base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())


class EncryptionService:
    def __init__(self, key: str | None = None):
        raw = key or settings.secret_key
        if not raw:
            logger.warning("EncryptionService: no key provided — operations will fail")
            self._fernet = None
        else:
            self._fernet = Fernet(_derive_key(raw))

    def encrypt(self, plaintext: str) -> str:
        if self._fernet is None:
            raise RuntimeError("EncryptionService not initialized (no key)")
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        if self._fernet is None:
            raise RuntimeError("EncryptionService not initialized (no key)")
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken:
            raise ValueError("Invalid ciphertext or wrong key")


encryption_service = EncryptionService()
