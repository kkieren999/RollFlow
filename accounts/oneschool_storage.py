"""Local-only encrypted import archive. Do not put exports in Git, static or DB.

The archived source can be downloaded later by an authenticated administrator,
or re-read for a reviewed student import. File contents never appear in audit
events, database JSON summaries, web logs, or public URLs.
"""
import os
from pathlib import Path
from uuid import uuid4

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def private_path(path, directory):
    if path.is_symlink():
        raise ValueError("Import archive cannot use a symbolic link.")
    if directory:
        path.mkdir(mode=0o700, parents=False, exist_ok=True)
    if os.name == "nt":
        from deployment.native import harden_windows_acl
        harden_windows_acl(path, directory=directory)
    else:
        path.chmod(0o700 if directory else 0o600)


def locations():
    """Archive is outside web/static roots, protected by instance NTFS/Unix ACLs."""
    state = Path(settings.ROLLFLOW_ARCHIVE_STATE_DIR)
    if not state.is_absolute() or not state.is_dir() or state.is_symlink():
        raise ValueError("An existing private instance data directory is required.")
    dest = state / "oneschool-imports"
    if dest == Path(settings.STATIC_ROOT) or Path(settings.STATIC_ROOT) == dest.parent:
        raise ValueError("Import archive must never be in the static directory.")
    private_path(dest, directory=True)
    return state, dest


def archive_cipher(state, *, create=False):
    key_path = state / "oneschool-import.key"
    if key_path.is_symlink():
        raise ValueError("Archive key cannot be a symbolic link.")
    # Never generate a new key when retrieving old sources: restore the
    # original key from a protected backup or the archive is unreadable.
    if create:
        try:
            fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            pass
        else:
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(Fernet.generate_key())
                    stream.flush()
                    os.fsync(stream.fileno())
                private_path(key_path, directory=False)
            except BaseException:
                key_path.unlink(missing_ok=True)
                raise
    if not key_path.is_file():
        raise ValueError("Archive encryption key is missing.")
    if os.name == "nt":
        private_path(key_path, directory=False)
    try:
        key = key_path.read_bytes()
        return Fernet(key)
    except (ValueError, OSError):
        raise ValueError("Unable to open the protected import archive key.") from None


def save_encrypted(raw):
    state, directory = locations()
    cipher = archive_cipher(state, create=True)
    token = uuid4().hex
    file = directory / (token + ".rfenc")
    encrypted = cipher.encrypt(raw)
    fd = os.open(file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(encrypted)
            stream.flush()
            os.fsync(stream.fileno())
        private_path(file, directory=False)
    except BaseException:
        file.unlink(missing_ok=True)
        raise
    return token


def read_encrypted(token):
    if len(token) != 32 or any(ch not in "0123456789abcdef" for ch in token):
        raise ValueError("Invalid import archive identifier.")
    state, directory = locations()
    source = directory / (token + ".rfenc")
    if source.is_symlink():
        raise ValueError("Invalid import archive entry.")
    try:
        ciphertext = source.read_bytes()
        raw = archive_cipher(state).decrypt(ciphertext)
    except (InvalidToken, FileNotFoundError, OSError):
        raise ValueError("Archived import is unavailable or failed integrity validation.") from None
    return raw


def forget_encrypted(tokens):
    """Only call after a confirmed, audited administrator deletion."""
    _, directory = locations()
    for token in tokens:
        if len(token) == 32 and all(ch in "0123456789abcdef" for ch in token):
            target = directory / (token + ".rfenc")
            if not target.is_symlink():
                target.unlink(missing_ok=True)
