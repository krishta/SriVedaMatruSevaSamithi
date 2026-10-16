import secrets
from pathlib import Path
from typing import Protocol

from app.core.config import settings


class StorageBackend(Protocol):
    def save(self, subdir: str, filename_hint: str, content: bytes) -> str:
        """Persist bytes, return a stable relative path to read it back later."""
        ...

    def read(self, relative_path: str) -> bytes: ...

    def absolute_path(self, relative_path: str) -> Path: ...


class LocalDiskStorage:
    """MVP storage — outside any web-served root, random filenames (module 07)."""

    def __init__(self, base_dir: str) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, subdir: str, filename_hint: str, content: bytes) -> str:
        ext = Path(filename_hint).suffix.lower() or ".bin"
        random_name = f"{secrets.token_hex(16)}{ext}"
        target_dir = self.base_dir / subdir
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / random_name
        target_path.write_bytes(content)
        return str(Path(subdir) / random_name)

    def read(self, relative_path: str) -> bytes:
        return (self.base_dir / relative_path).read_bytes()

    def absolute_path(self, relative_path: str) -> Path:
        return self.base_dir / relative_path


# Two roots: uploads (screenshots) and receipts (PDFs) — module 04/05.
upload_storage: StorageBackend = LocalDiskStorage(settings.upload_dir)
receipt_storage: StorageBackend = LocalDiskStorage(settings.receipts_dir)

# Swap-in points for later cloud migration (module 08) — not implemented in this iteration:
# upload_storage = AzureBlobStorage(...) / S3Storage(...)