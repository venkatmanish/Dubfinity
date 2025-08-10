from __future__ import annotations
import os
from pathlib import Path
from typing import Optional

class LocalStore:
    """
    Store and retrieve files from a local directory.
    """

    def __init__(self, base_dir: str = "storage"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, file_bytes: bytes, filename: str, subdir: Optional[str] = None) -> str:
        """Save bytes under base_dir/[subdir]/filename and return the path."""
        if subdir:
            dir_path = self.base_dir / subdir
            dir_path.mkdir(parents=True, exist_ok=True)
        else:
            dir_path = self.base_dir

        file_path = dir_path / filename
        with open(file_path, "wb") as f:
            f.write(file_bytes)
        return str(file_path.resolve())

    def load(self, filename: str, subdir: Optional[str] = None) -> bytes:
        """Read bytes from base_dir/[subdir]/filename."""
        if subdir:
            file_path = self.base_dir / subdir / filename
        else:
            file_path = self.base_dir / filename

        with open(file_path, "rb") as f:
            return f.read()

    def delete(self, filename: str, subdir: Optional[str] = None) -> bool:
        """Delete file if exists; return True if deleted."""
        if subdir:
            file_path = self.base_dir / subdir / filename
        else:
            file_path = self.base_dir / filename

        if file_path.exists():
            file_path.unlink()
            return True
        return False
