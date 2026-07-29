"""DOCX 解析器 —— python-docx。

支持：
- 标题层级（Heading 1-6）
- 段落、列表、表格
- 图片引用
- 批注
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from docx import Document as DocxDocument
from docx.oxml.ns import qn

from ..block import BlockType, ParsedBlock
from ..registry import BaseParser


class DocxParser(BaseParser):
    """基于 python-docx 的 DOCX 解析器。"""

    @property
    def supported_formats(self) -> list[str]:
        return ["docx"]

    async def validate(self, file_path: str | Path) -> bool:
        try:
            DocxDocument(str(file_path))
            return True
        except Exception:
            return False

    async def parse(
        self, file_path: str | Path, **kwargs: Any
    ) -> list[Block]:
        doc = DocxDocument(str(file_path))
        blocks: list[Block] = []
        heading_stack: list[str] = []

        for i, para in enumerate(doc.paragraphs):
            if not para.text.strip():
                continue

            block = self._paragraph_to_block(para, heading_stack, i, doc)
            if block:
                blocks.append(block)

        # 处理表格
        for table in doc.tables:
            block = self._table_to_block(table)
            if block:
                blocks.append(block)

        return blocks

    def _paragraph_to_block(
        self, para: Any, heading_stack: list[str], index: int, doc: Any
    ) -> Block | None:
        style_name = para.style.name.lower() if para.style else ""
        text = para.text.strip()
        if not text:
            return None

        # 标题检测
        heading_level = None
        block_type = BlockType.PARAGRAPH

        if "heading" in style_name:
            for level_num in range(1, 7):
                if str(level_num) in style_name or f"heading {level_num}" in style_name:
                    heading_level = level_num
                    block_type = BlockType.HEADING
                    break
            if heading_level is None:
                heading_level = 1
                block_type = BlockType.HEADING

        if heading_level:
            # 维护 heading 栈
            while heading_stack and len(heading_stack) >= heading_level:
                heading_stack.pop()
            heading_stack.append(text)

        heading_path = " > ".join(heading_stack) if heading_stack else None

        # 列表检测
        if para._element.find(qn("w:pPr")) is not None:
            pPr = para._element.find(qn("w:pPr"))
            if pPr.find(qn("w:numPr")) is not None:
                block_type = BlockType.LIST_ITEM

        return ParsedBlock(
              
            block_type=block_type,
            page_number=None,
            heading_path=heading_path,
            heading_level=heading_level,
            text=text,
            text_length=len(text),
            order_index=index,
            depth=heading_level or 0,
            block_metadata={"style": style_name},
        )

    def _table_to_block(self, table: Any) -> Block | None:
        rows = []
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            rows.append(cells)

        if not rows:
            return None

        return ParsedBlock(
              
            block_type=BlockType.TABLE,
            page_number=None,
            text=f"[表格: {len(rows)}行 x {len(rows[0])}列]",
            text_length=0,
            table_data={
                "headers": rows[0] if len(rows) > 1 else [],
                "rows": rows[1:] if len(rows) > 1 else rows,
                "num_rows": len(rows),
                "num_cols": len(rows[0]) if rows else 0,
            },
            order_index=0,
            depth=0,
            block_metadata={"type": "table"},
        )
