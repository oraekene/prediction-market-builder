import pytest
from app.services.encryption import EncryptionService


class TestEncryptionService:
    def test_encrypt_decrypt_roundtrip(self):
        svc = EncryptionService(key="test-secret-key-32-bytes-long!!")
        plaintext = "my-super-secret-api-key"
        ciphertext = svc.encrypt(plaintext)
        assert ciphertext != plaintext
        assert ciphertext.startswith("v1:")
        assert svc.decrypt(ciphertext) == plaintext

    def test_encrypt_is_nondeterministic(self):
        svc = EncryptionService(key="test-secret-key-32-bytes-long!!")
        assert svc.encrypt("secret") != svc.encrypt("secret")

    def test_different_keys_fail(self):
        svc1 = EncryptionService(key="first-key-here-32-bytes-long!!!")
        svc2 = EncryptionService(key="second-key-here-32-bytes-long!!")
        ciphertext = svc1.encrypt("secret")
        with pytest.raises(ValueError, match="Invalid ciphertext"):
            svc2.decrypt(ciphertext)

    def test_empty_string(self):
        svc = EncryptionService(key="test-secret-key-32-bytes-long!!")
        assert svc.decrypt(svc.encrypt("")) == ""

    def test_no_key_raises(self):
        with pytest.raises(ValueError, match="non-empty key"):
            EncryptionService(key="")

    def test_legacy_unversioned_ciphertext_rejected(self):
        svc = EncryptionService(key="test-secret-key-32-bytes-long!!")
        with pytest.raises(ValueError, match="Invalid ciphertext format"):
            svc.decrypt("unversioned-token")
