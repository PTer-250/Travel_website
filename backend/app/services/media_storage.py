"""面向日记上传的媒体存储抽象 (默认落地到本地文件系统)。"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings


@dataclass(frozen=True)
class StoredMedia:
    """保存媒体后返回的元数据，向上层标识文件位置与大小。"""

    relative_path: str
    size: int
    backend: str


class MediaStorageService:
    """基于文件系统实现的媒体存储服务，负责统一的读写删除。"""

    def __init__(self, root: Path, backend: str = "local") -> None:
        self.root = root
        self.backend = backend
        self.root.mkdir(parents=True, exist_ok=True)  # 确保存储根目录存在

    async def save(self, diary_id: int, filename: str, payload: bytes) -> StoredMedia:
        """将文件写入对应日记目录，并返回存储路径等信息。"""
        extension = Path(filename).suffix.lower()
        unique_name = f"{uuid.uuid4().hex}{extension}"
        relative_path = Path(str(diary_id)) / unique_name
        full_path = self._full_path(relative_path)
        full_path.parent.mkdir(parents=True, exist_ok=True)  # 分日记创建子目录
        await asyncio.to_thread(full_path.write_bytes, payload)  # 在线程中写文件，避免阻塞事件循环
        return StoredMedia(relative_path=relative_path.as_posix(), size=len(payload), backend=self.backend)

    async def read(self, relative_path: str) -> bytes:
        """根据相对路径读取文件内容。"""
        full_path = self._full_path(Path(relative_path))
        return await asyncio.to_thread(full_path.read_bytes)

    async def delete(self, relative_path: str) -> None:
        """如果文件存在则删除，并尝试清理空目录。"""
        full_path = self._full_path(Path(relative_path))
        try:
            await asyncio.to_thread(full_path.unlink)
        except FileNotFoundError:
            return
        self._cleanup_empty_parents(full_path.parent)

    def _cleanup_empty_parents(self, start: Path) -> None:
        """自底向上清理空目录，防止磁盘堆积无用层级。"""
        current = start
        while current != self.root and not any(current.iterdir()):
            current.rmdir()
            current = current.parent

    def _full_path(self, relative: Path) -> Path:
        """在存储根目录内解析完整路径，阻止目录穿越。"""
        candidate = (self.root / relative).resolve()
        if not str(candidate).startswith(str(self.root)):
            raise ValueError("Attempted to access media outside storage root")
        return candidate


_media_storage_service: MediaStorageService | None = None


def get_media_storage_service() -> MediaStorageService:
    """返回单例的媒体存储服务，集中复用文件句柄与配置。"""

    global _media_storage_service
    if _media_storage_service is None:
        root = Path(settings.media_storage_root).resolve()
        _media_storage_service = MediaStorageService(root=root, backend=settings.media_storage_backend)
    return _media_storage_service


def build_public_media_url(storage_path: str) -> str:
    """根据存储路径拼接出可通过 HTTP 访问的地址。"""

    base = settings.public_api_url.rstrip("/")
    prefix = settings.media_storage_url_prefix.strip("/")
    relative = storage_path.lstrip("/")
    if prefix:
        return f"{base}/{prefix}/{relative}"
    return f"{base}/{relative}"
