from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from pathlib import Path
import uuid, shutil, logging

from backend.config import settings

logger = logging.getLogger(__name__)
cfg = settings()

# try:
#     import boto3  # optional
# except Exception:
#     boto3 = None  # type: ignore


@dataclass
class StorageService:
    backend: str = (cfg.storage.get("backend") or "local")
    local_tmp: Path = Path(cfg.storage.get("local_tmp") or "./.tmp")
    bucket: Optional[str] = None

    def __post_init__(self):
        self.local_tmp.mkdir(parents=True, exist_ok=True)
        self._s3 = None
        if self.backend == "s3" and boto3:
            self._s3 = boto3.client("s3")

    # ---------- Local temp files ---------- #
    def save_tmp(self, data: bytes, suffix: str = ".bin") -> Path:
        p = self.local_tmp / f"{uuid.uuid4().hex}{suffix}"
        p.write_bytes(data)
        return p

    def copy_to_tmp(self, src_path: Path) -> Path:
        dst = self.local_tmp / f"{uuid.uuid4().hex}{src_path.suffix}"
        shutil.copyfile(src_path, dst)
        return dst

    # # ---------- S3 (optional) ---------- #
    # def s3_put(self, key: str, data: bytes) -> str:
    #     if not self._s3 or not self.bucket:
    #         raise RuntimeError("S3 not configured")
    #     self._s3.put_object(Bucket=self.bucket, Key=key, Body=data)
    #     return f"s3://{self.bucket}/{key}"

    # def s3_get(self, key: str) -> bytes:
    #     if not self._s3 or not self.bucket:
    #         raise RuntimeError("S3 not configured")
    #     obj = self._s3.get_object(Bucket=self.bucket, Key=key)
    #     return obj["Body"].read()
