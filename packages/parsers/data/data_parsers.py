"""CSV / JSON 数据格式解析器。"""

from __future__ import annotations

import csv
import json
from io import StringIO
from pathlib import Path
from typing import Any

from ..block import BlockType, ParsedBlock
from ..registry import BaseParser


class CsvParser(BaseParser):
    """CSV 解析器 —— 保留字段结构，不以纯文本切分。"""

    @property
    def supported_formats(self) -> list[str]:
        return ["csv"]

    async def validate(self, file_path: str | Path) -> bool:
        try:
            content = Path(file_path).read_text(encoding="utf-8", errors="replace")
            dialect = csv.Sniffer().sniff(content[:4096])
            return dialect is not None
        except Exception:
            return False

    async def parse(
        self, file_path: str | Path, **kwargs: Any
    ) -> list[Block]:
        import chardet

        content = Path(file_path).read_bytes()
        encoding = chardet.detect(content).get("encoding", "utf-8") or "utf-8"
        text = content.decode(encoding, errors="replace")

        reader = csv.reader(StringIO(text))
        rows_data = list(reader)

        if not rows_data:
            return []

        # 检测分隔符
        try:
            dialect = csv.Sniffer().sniff(text[:4096])
        except Exception:
            pass

        blocks: list[Block] = []

        # 将 CSV 作为表格块
        blocks.append(ParsedBlock(
              
            block_type=BlockType.TABLE,
            page_number=None,
            text=f"[CSV: {len(rows_data)}行 x {len(rows_data[0])}列]",
            text_length=0,
            table_data={
                "headers": rows_data[0] if len(rows_data) > 1 else [],
                "rows": rows_data[1:] if len(rows_data) > 1 else rows_data,
                "num_rows": len(rows_data),
                "num_cols": len(rows_data[0]) if rows_data else 0,
            },
            order_index=0,
            depth=0,
            block_metadata={"format": "csv", "rows": len(rows_data)},
        ))

        return blocks


class JsonParser(BaseParser):
    """JSON 解析器 —— 保留字段结构，支持嵌套展开。"""

    @property
    def supported_formats(self) -> list[str]:
        return ["json"]

    async def validate(self, file_path: str | Path) -> bool:
        try:
            content = Path(file_path).read_text(encoding="utf-8", errors="replace")
            json.loads(content)
            return True
        except Exception:
            return False

    async def parse(
        self, file_path: str | Path, **kwargs: Any
    ) -> list[Block]:
        content = Path(file_path).read_text(encoding="utf-8", errors="replace")
        data = json.loads(content)

        blocks: list[Block] = []

        if isinstance(data, list) and data:
            # JSON 数组 → 表格
            if isinstance(data[0], dict):
                headers = list(data[0].keys())
                rows_data = []
                for item in data:
                    rows_data.append([str(item.get(k, "")) for k in headers])

                blocks.append(ParsedBlock(
                      
                    block_type=BlockType.TABLE,
                    page_number=None,
                    text=f"[JSON: {len(rows_data)}条记录]",
                    text_length=0,
                    table_data={
                        "headers": headers,
                        "rows": rows_data,
                        "num_rows": len(rows_data),
                        "num_cols": len(headers),
                    },
                    order_index=0,
                    depth=0,
                    block_metadata={"format": "json_array"},
                ))
            else:
                # 简单数组
                text = "\n".join(str(item) for item in data)
                blocks.append(ParsedBlock(
                      
                    block_type=BlockType.LIST,
                    page_number=None,
                    text=text,
                    text_length=len(text),
                    order_index=0,
                    depth=0,
                    block_metadata={"format": "json_array"},
                ))

        elif isinstance(data, dict):
            # JSON 对象 → 扁平化键值对
            text = json.dumps(data, ensure_ascii=False, indent=2)
            blocks.append(ParsedBlock(
                  
                block_type=BlockType.PARAGRAPH,
                page_number=None,
                text=text,
                text_length=len(text),
                order_index=0,
                depth=0,
                block_metadata={"format": "json_object"},
            ))

        return blocks
