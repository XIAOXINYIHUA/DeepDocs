"""MinIO 对象存储依赖。"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from minio import Minio
from minio.error import S3Error

from packages.core.config.settings import settings


class FileStorage:
    """对象存储抽象（MinIO / S3 兼容）。"""

    def __init__(self) -> None:
        self.client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self.bucket = settings.minio_bucket

    def ensure_bucket(self) -> bool:
        """确保桶存在。"""
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)
            return True
        return False

    def upload_file(
        self,
        local_path: str | Path,
        object_name: str | None = None,
        content_type: str = "application/octet-stream",
    ) -> str:
        """上传文件到 MinIO。

        Args:
            local_path: 本地文件路径
            object_name: 对象名（默认使用文件名）
            content_type: MIME 类型

        Returns:
            str: 对象名（用于后续引用）
        """
        local_path = Path(local_path)
        if object_name is None:
            object_name = local_path.name

        result = self.client.fput_object(
            bucket_name=self.bucket,
            object_name=object_name,
            file_path=str(local_path),
            content_type=content_type,
        )
        return result.object_name

    def upload_bytes(
        self,
        data: bytes,
        object_name: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """上传字节数据到 MinIO。"""
        result = self.client.put_object(
            bucket_name=self.bucket,
            object_name=object_name,
            data=BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        return result.object_name

    def download_file(self, object_name: str, local_path: str | Path) -> Path:
        """下载文件到本地。"""
        local_path = Path(local_path)
        self.client.fget_object(
            bucket_name=self.bucket,
            object_name=object_name,
            file_path=str(local_path),
        )
        return local_path

    def get_object_url(self, object_name: str) -> str:
        """获取对象 URL。"""
        return f"{settings.minio_endpoint}/{self.bucket}/{object_name}"

    def delete_object(self, object_name: str) -> None:
        """删除对象。"""
        try:
            self.client.remove_object(self.bucket, object_name)
        except S3Error:
            pass

    def list_objects(self, prefix: str = "") -> list[str]:
        """列出桶内对象。"""
        objects = self.client.list_objects(self.bucket, prefix=prefix, recursive=True)
        return [obj.object_name for obj in objects]


# 全局单例
storage = FileStorage()
