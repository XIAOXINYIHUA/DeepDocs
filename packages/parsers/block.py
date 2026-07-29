"""解析结果数据传输对象 —— 非 ORM，仅用于解析流水线。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class BlockType(StrEnum):
    TITLE = "title"
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST = "list"
    LIST_ITEM = "list_item"
    TABLE = "table"
    TABLE_ROW = "table_row"
    IMAGE = "image"
    CAPTION = "caption"
    HEADER = "header"
    FOOTER = "footer"
    FORMULA = "formula"
    CODE = "code"
    QUOTE = "quote"
    SEPARATOR = "separator"
    OTHER = "other"


@dataclass
class ParsedBlock:
    """解析后的结构化块 —— 传递对象，非 ORM。"""
    block_type: BlockType = BlockType.PARAGRAPH
    page_number: int | None = None
    heading_path: str | None = None
    heading_level: int | None = None
    text: str = ""
    text_length: int = 0
    table_data: dict[str, Any] | None = None
    image_ref: str | None = None
    bbox: dict[str, Any] | None = None
    order_index: int = 0
    depth: int = 0
    block_metadata: dict[str, Any] = field(default_factory=dict)
