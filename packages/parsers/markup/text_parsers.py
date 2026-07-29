"""HTML / Markdown / TXT 解析器。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..block import BlockType, ParsedBlock
from ..registry import BaseParser


class HtmlParser(BaseParser):
    """基于 trafilatura + BeautifulSoup 的 HTML 解析器。"""

    @property
    def supported_formats(self) -> list[str]:
        return ["html"]

    async def validate(self, file_path: str | Path) -> bool:
        content = Path(file_path).read_bytes()
        return b"<html" in content.lower() or b"<!DOCTYPE html" in content

    async def parse(
        self, file_path: str | Path, **kwargs: Any
    ) -> list[Block]:
        import trafilatura

        content = Path(file_path).read_text(encoding="utf-8", errors="replace")

        # trafilatura 提取正文
        extracted = trafilatura.extract(
            content,
            output_format="txt",
            include_tables=True,
            include_images=False,
            include_links=False,
            favor_precision=True,
        )

        blocks: list[Block] = []

        if extracted:
            # 按段落切分
            for para in extracted.split("\n\n"):
                text = para.strip()
                if not text:
                    continue
                blocks.append(ParsedBlock(
                      
                    block_type=BlockType.PARAGRAPH,
                    page_number=None,
                    text=text,
                    text_length=len(text),
                    order_index=len(blocks),
                    depth=0,
                    block_metadata={},
                ))
        else:
            # 回退：用 BeautifulSoup 提取文本
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, "lxml")

            for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
                text = heading.get_text(strip=True)
                if not text:
                    continue
                level = int(heading.name[1])
                blocks.append(ParsedBlock(
                      
                    block_type=BlockType.HEADING,
                    page_number=None,
                    heading_path=text,
                    heading_level=level,
                    text=text,
                    text_length=len(text),
                    order_index=len(blocks),
                    depth=level,
                    block_metadata={},
                ))

            for tag in soup.find_all(["p", "li"]):
                text = tag.get_text(strip=True)
                if not text:
                    continue
                bt = BlockType.LIST_ITEM if tag.name == "li" else BlockType.PARAGRAPH
                blocks.append(ParsedBlock(
                      
                    block_type=bt,
                    page_number=None,
                    text=text,
                    text_length=len(text),
                    order_index=len(blocks),
                    depth=0,
                    block_metadata={},
                ))

            for table in soup.find_all("table"):
                rows_data = []
                for row in table.find_all("tr"):
                    cells = [cell.get_text(strip=True) for cell in row.find_all(["td", "th"])]
                    if cells:
                        rows_data.append(cells)
                if rows_data:
                    blocks.append(ParsedBlock(
                          
                        block_type=BlockType.TABLE,
                        page_number=None,
                        text=f"[表格: {len(rows_data)}行]",
                        text_length=0,
                        table_data={
                            "headers": rows_data[0] if len(rows_data) > 1 else [],
                            "rows": rows_data[1:] if len(rows_data) > 1 else rows_data,
                            "num_rows": len(rows_data),
                            "num_cols": len(rows_data[0]) if rows_data else 0,
                        },
                        order_index=len(blocks),
                        depth=0,
                        block_metadata={},
                    ))

        return blocks


class MarkdownParser(BaseParser):
    """Markdown 解析器 —— 保留标题层级结构。"""

    @property
    def supported_formats(self) -> list[str]:
        return ["markdown"]

    async def validate(self, file_path: str | Path) -> bool:
        return True  # .md 后缀

    async def parse(
        self, file_path: str | Path, **kwargs: Any
    ) -> list[Block]:
        import re

        content = Path(file_path).read_text(encoding="utf-8", errors="replace")
        lines = content.split("\n")
        blocks: list[Block] = []
        heading_stack: list[str] = []

        i = 0
        while i < len(lines):
            line = lines[i]

            # 标题
            heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
            if heading_match:
                level = len(heading_match.group(1))
                text = heading_match.group(2).strip()

                while heading_stack and len(heading_stack) >= level:
                    heading_stack.pop()
                heading_stack.append(text)

                blocks.append(ParsedBlock(
                      
                    block_type=BlockType.HEADING,
                    page_number=None,
                    heading_path=" > ".join(heading_stack),
                    heading_level=level,
                    text=text,
                    text_length=len(text),
                    order_index=len(blocks),
                    depth=level,
                    block_metadata={},
                ))
                i += 1
                continue

            # 表格
            if "|" in line and i + 1 < len(lines) and "---" in lines[i + 1]:
                table_lines = []
                while i < len(lines) and "|" in lines[i]:
                    table_lines.append(lines[i].strip())
                    i += 1
                rows_data = []
                for tl in table_lines:
                    cells = [c.strip() for c in tl.split("|") if c.strip()]
                    if cells:
                        rows_data.append(cells)
                if len(rows_data) > 1:
                    blocks.append(ParsedBlock(
                          
                        block_type=BlockType.TABLE,
                        page_number=None,
                        text=f"[表格: {len(rows_data)-1}行]",
                        text_length=0,
                        table_data={
                            "headers": rows_data[0],
                            "rows": rows_data[2:],  # 跳过分隔行
                            "num_rows": len(rows_data) - 1,
                            "num_cols": len(rows_data[0]),
                        },
                        order_index=len(blocks),
                        depth=0,
                        block_metadata={},
                    ))
                continue

            # 列表项
            list_match = re.match(r"^(\s*)[-*+]\s+(.+)$", line)
            if list_match:
                text = list_match.group(2).strip()
                blocks.append(ParsedBlock(
                      
                    block_type=BlockType.LIST_ITEM,
                    page_number=None,
                    text=text,
                    text_length=len(text),
                    order_index=len(blocks),
                    depth=0,
                    block_metadata={},
                ))
                i += 1
                continue

            # 段落
            text = line.strip()
            if text:
                blocks.append(ParsedBlock(
                      
                    block_type=BlockType.PARAGRAPH,
                    page_number=None,
                    heading_path=" > ".join(heading_stack) if heading_stack else None,
                    text=text,
                    text_length=len(text),
                    order_index=len(blocks),
                    depth=len(heading_stack),
                    block_metadata={},
                ))

            i += 1

        return blocks


class TextParser(BaseParser):
    """纯文本解析器 —— 编码检测 + 段落分割。"""

    @property
    def supported_formats(self) -> list[str]:
        return ["txt"]

    async def validate(self, file_path: str | Path) -> bool:
        return True

    def _detect_encoding(self, content: bytes) -> str:
        """自动检测文本编码。"""
        import chardet
        result = chardet.detect(content)
        return result.get("encoding", "utf-8") or "utf-8"

    async def parse(
        self, file_path: str | Path, **kwargs: Any
    ) -> list[Block]:
        content = Path(file_path).read_bytes()
        encoding = self._detect_encoding(content)
        text = content.decode(encoding, errors="replace")

        blocks: list[Block] = []
        for para in text.split("\n\n"):
            text_stripped = para.strip()
            if not text_stripped:
                continue
            blocks.append(Block(
                  
                block_type=BlockType.PARAGRAPH,
                page_number=None,
                text=text_stripped,
                text_length=len(text_stripped),
                order_index=len(blocks),
                depth=0,
                block_metadata={},
            ))

        return blocks
