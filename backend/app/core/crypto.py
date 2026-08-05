from __future__ import annotations

import os
import pathlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

_KEY_FILE_NAME = "secret.key"
_fernet: Fernet | None = None


def _data_dir() -> pathlib.Path:
    url = settings.database_url
    if url.startswith("sqlite"):
        path_part = url.split("///", 1)[-1]
        db_path = pathlib.Path(path_part)
        return db_path.parent if db_path.parent != pathlib.Path("") else pathlib.Path(".")
    return pathlib.Path("./data")


def _load_or_create_key() -> bytes:
    if settings.secret_key:
        return settings.secret_key.encode("utf-8")

    data_dir = _data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    key_path = data_dir / _KEY_FILE_NAME
    if key_path.exists():
        return key_path.read_bytes().strip()

    key = Fernet.generate_key()
    key_path.write_bytes(key)
    try:
        os.chmod(key_path, 0o600)
    except OSError:
        pass
    return key


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(_load_or_create_key())
    return _fernet


def is_already_encrypted(value: str | None) -> bool:
    if not value:
        return True
    try:
        _get_fernet().decrypt(value.encode("ascii"))
        return True
    except (InvalidToken, ValueError):
        return False


def encrypt_secret(plaintext: str | None) -> str | None:
    if not plaintext:
        return plaintext
    return _get_fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt_secret(ciphertext: str | None) -> str | None:
    if not ciphertext:
        return ciphertext
    try:
        return _get_fernet().decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError):
        return ciphertext


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2 or sys.argv[1] != "generate-key":
        print("usage: python -m app.core.crypto generate-key", file=sys.stderr)
        raise SystemExit(1)
    print(Fernet.generate_key().decode("ascii"))
