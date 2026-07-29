"""XLSX 解析器 —— openpyxl。

支持：
- 多工作表
- 表头识别
- 公式结果读取（data_only）
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from ..block import BlockType, ParsedBlock
from ..registry import BaseParser


class XlsxParser(BaseParser):
    @property
    def supported_formats(self) -> list[str]:
        return ["xlsx"]

    async def validate(self, file_path: str | Path) -> bool:
        try:
            load_workbook(str(file_path), read_only=True)
            return True
        except Exception:
            return False

    async def parse(
        self, file_path: str | Path, **kwargs: Any
    ) -> list[Block]:
        # data_only=True 获取公式计算结果
        wb = load_workbook(str(file_path), data_only=True)
        blocks: list[Block] = []

        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]

            # 工作表标题
            blocks.append(ParsedBlock(
                  
                block_type=BlockType.HEADING,
                page_number=None,
                heading_path=f"[工作表] {sheet_name}",
                heading_level=1,
                text=f"工作表: {sheet_name}",
                text_length=len(sheet_name) + 5,
                order_index=len(blocks),
                depth=1,
                block_metadata={"sheet_name": sheet_name, "type": "sheet_header"},
            ))

            # 读取所有行
            rows_data = []
            for row in ws.iter_rows(values_only=True):
                row_values = [
                    str(cell) if cell is not None else ""
                    for cell in row
                ]
                rows_data.append(row_values)

            # 记录基本信息
            max_col = ws.max_column or 0
            max_row = ws.max_row or 0

            if rows_data:
                blocks.append(ParsedBlock(
                      
                    block_type=BlockType.TABLE,
                    page_number=None,
                    text=f"[{sheet_name}: {max_row}行 x {max_col}列]",
                    text_length=0,
                    table_data={
                        "headers": rows_data[0] if len(rows_data) > 1 else [],
                        "rows": rows_data[1:] if len(rows_data) > 1 else rows_data,
                        "num_rows": max_row,
                        "num_cols": max_col,
                    },
                    order_index=len(blocks),
                    depth=0,
                    block_metadata={"sheet_name": sheet_name},
                ))

        wb.close()
        return blocks
