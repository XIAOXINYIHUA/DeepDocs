"""解析器注册表与格式检测。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from ..block import ParsedBlock

# ─── MIME 魔数签名 ───
MAGIC_SIGNATURES: dict[str, tuple[bytes, int]] = {
    "pdf": (b"%PDF", 0),
    "zip": (b"PK\x03\x04", 0),  # DOCX / PPTX / XLSX 都是 ZIP 封装
    "xlsx": (b"PK\x03\x04", 0),
    "docx": (b"PK\x03\x04", 0),
    "pptx": (b"PK\x03\x04", 0),
    "png": (b"\x89PNG\r\n\x1a\n", 0),
    "jpg": (b"\xff\xd8\xff", 0),
    "tiff": (b"II\x2a\x00", 0),
    "tiff_le": (b"MM\x00\x2a", 0),
    "html": (b"<!DOCTYPE html", 0),
    "xml": (b"<?xml", 0),
    "json": (b"{", 0),
}

# ─── 扩展名映射 ───
EXTENSION_MAP: dict[str, str] = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".pptx": "pptx",
    ".xlsx": "xlsx",
    ".txt": "txt",
    ".md": "markdown",
    ".markdown": "markdown",
    ".html": "html",
    ".htm": "html",
    ".csv": "csv",
    ".json": "json",
    ".xml": "xml",
    ".png": "png",
    ".jpg": "jpg",
    ".jpeg": "jpeg",
    ".tiff": "tiff",
    ".tif": "tiff",
    ".rtf": "rtf",
    ".epub": "epub",
    ".eml": "eml",
    ".msg": "msg",
}


def detect_format(filename: str, content: bytes) -> str:
    """通过扩展名 + 魔数双重检测文档格式。"""
    # 扩展名检测
    ext = Path(filename).suffix.lower()
    fmt = EXTENSION_MAP.get(ext, "unknown")

    # 魔数验证
    for magic_fmt, (magic, offset) in MAGIC_SIGNATURES.items():
        if content[offset:offset + len(magic)] == magic:
            # ZIP 文件需要进一步区分 Office 格式
            if magic_fmt == "zip":
                return _detect_office_format(filename, content)
            return magic_fmt

    return fmt


def _detect_office_format(filename: str, content: bytes) -> str:
    """从 ZIP 文件中检测 Office 格式。"""
    ext = Path(filename).suffix.lower()
    if ext in (".docx", ".pptx", ".xlsx"):
        return ext.lstrip(".")
    return "zip"  # 普通压缩包


class BaseParser(ABC):
    """解析器基类。"""

    @property
    @abstractmethod
    def supported_formats(self) -> list[str]:
        """返回支持的格式列表。"""
        ...

    @abstractmethod
    async def parse(self, file_path: str | Path, **kwargs: Any) -> list[ParsedBlock]:
        """解析文件，返回 Block 列表。

        Args:
            file_path: 文件本地路径
            **kwargs: 解析参数（语言、OCR 开关等）

        Returns:
            list[ParsedBlock]: 有序的结构化块列表
        """
        ...

    @abstractmethod
    async def validate(self, file_path: str | Path) -> bool:
        """验证文件是否可被本解析器处理。"""
        ...


class ParserRegistry:
    """解析器注册表 —— 根据格式自动选择解析器。"""

    def __init__(self) -> None:
        self._parsers: dict[str, BaseParser] = {}

    def register(self, parser: BaseParser) -> None:
        """注册解析器。"""
        for fmt in parser.supported_formats:
            if fmt in self._parsers:
                raise ValueError(
                    f"Format '{fmt}' already registered to {type(self._parsers[fmt]).__name__}"
                )
            self._parsers[fmt] = parser

    def get_parser(self, fmt: str) -> BaseParser | None:
        """获取格式对应的解析器。"""
        return self._parsers.get(fmt)

    def supported_formats(self) -> list[str]:
        return list(self._parsers.keys())

    async def parse(
        self, file_path: str | Path, filename: str | None = None, **kwargs: Any
    ) -> list[ParsedBlock]:
        """自动检测格式并解析。"""
        with open(file_path, "rb") as f:
            content = f.read(2048)

        fmt = detect_format(filename or str(file_path), content)
        parser = self.get_parser(fmt)

        if parser is None:
            raise ValueError(f"Unsupported format: {fmt} (file: {filename})")

        return await parser.parse(file_path, **kwargs)

    def can_parse(self, filename: str) -> bool:
        """检查文件是否可以被解析。"""
        ext = Path(filename).suffix.lower()
        fmt = EXTENSION_MAP.get(ext)
        return fmt in self._parsers
