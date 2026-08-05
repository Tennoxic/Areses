import pytest
from cryptography.fernet import Fernet

import app.core.crypto as crypto_module
from app.core.config import settings


@pytest.fixture
def isolated_crypto(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "database_url", f"sqlite+aiosqlite:///{tmp_path}/areses.db")
    monkeypatch.setattr(settings, "secret_key", None)
    monkeypatch.setattr(crypto_module, "_fernet", None)
    yield crypto_module
    monkeypatch.setattr(crypto_module, "_fernet", None)


def test_encrypt_then_decrypt_roundtrips(isolated_crypto):
    ciphertext = isolated_crypto.encrypt_secret("my-smtp-password")
    assert ciphertext != "my-smtp-password"
    assert isolated_crypto.decrypt_secret(ciphertext) == "my-smtp-password"


def test_encrypt_secret_passes_through_none_and_empty(isolated_crypto):
    assert isolated_crypto.encrypt_secret(None) is None
    assert isolated_crypto.encrypt_secret("") == ""


def test_decrypt_secret_passes_through_none_and_empty(isolated_crypto):
    assert isolated_crypto.decrypt_secret(None) is None
    assert isolated_crypto.decrypt_secret("") == ""


def test_encrypt_secret_is_nondeterministic(isolated_crypto):
    first = isolated_crypto.encrypt_secret("same-value")
    second = isolated_crypto.encrypt_secret("same-value")
    assert first != second
    assert isolated_crypto.decrypt_secret(first) == "same-value"
    assert isolated_crypto.decrypt_secret(second) == "same-value"


def test_decrypt_secret_returns_legacy_plaintext_unchanged(isolated_crypto):
    legacy_plaintext_value = "password-written-before-encryption-existed"
    assert isolated_crypto.decrypt_secret(legacy_plaintext_value) == legacy_plaintext_value


def test_is_already_encrypted_true_for_ciphertext_and_empty(isolated_crypto):
    ciphertext = isolated_crypto.encrypt_secret("a-secret")
    assert isolated_crypto.is_already_encrypted(ciphertext) is True
    assert isolated_crypto.is_already_encrypted(None) is True
    assert isolated_crypto.is_already_encrypted("") is True


def test_is_already_encrypted_false_for_plaintext(isolated_crypto):
    assert isolated_crypto.is_already_encrypted("plain-password") is False


def test_key_file_is_created_with_restricted_permissions(isolated_crypto, tmp_path):
    isolated_crypto.encrypt_secret("trigger-key-creation")
    key_path = tmp_path / "secret.key"
    assert key_path.exists()
    assert oct(key_path.stat().st_mode)[-3:] == "600"


def test_key_file_is_reused_across_fernet_instances(isolated_crypto, tmp_path):
    first_ciphertext = isolated_crypto.encrypt_secret("persisted-across-restarts")
    isolated_crypto._fernet = None
    assert isolated_crypto.decrypt_secret(first_ciphertext) == "persisted-across-restarts"


def test_explicit_secret_key_env_overrides_key_file(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "database_url", f"sqlite+aiosqlite:///{tmp_path}/areses.db")
    monkeypatch.setattr(settings, "secret_key", Fernet.generate_key().decode("ascii"))
    monkeypatch.setattr(crypto_module, "_fernet", None)
    crypto_module.encrypt_secret("uses-explicit-key")
    assert not (tmp_path / "secret.key").exists()
    monkeypatch.setattr(crypto_module, "_fernet", None)
