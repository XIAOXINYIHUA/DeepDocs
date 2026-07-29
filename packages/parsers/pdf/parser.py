"""PDF 解析器 —— Docling 主引擎 + PyMuPDF 回退。

支持：
- 文本 / 表格 / 多栏
- 标题层级结构
- OCR 扫描件（Docling 内置）
- 页面坐标定位
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog

from ..block import BlockType, ParsedBlock
from ..registry import BaseParser

logger = structlog.get_logger()


class DoclingPDFParser(BaseParser):
    """基于 Docling 的 PDF 解析器（推荐使用）。"""

    @property
    def supported_formats(self) -> list[str]:
        return ["pdf"]

    async def validate(self, file_path: str | Path) -> bool:
        """验证文件是否可解析。"""
        try:
            from docling.document_converter import DocumentConverter

            converter = DocumentConverter()
            result = converter.convert(str(file_path))
            return result is not None
        except Exception:
            return False

    async def parse(
        self,
        file_path: str | Path,
        ocr: bool = True,
        page_range: tuple[int, int] | None = None,
        **kwargs: Any,
    ) -> list[Block]:
        """使用 Docling 解析 PDF。

        Args:
            file_path: PDF 路径
            ocr: 是否启用扫描件 OCR
            page_range: 页码范围 (start, end)
        """
        try:
            return await self._parse_with_docling(file_path, ocr, page_range)
        except Exception as e:
            logger.warning("Docling parse failed, falling back to PyMuPDF", error=str(e))
            return await self._parse_with_pymupdf(file_path, page_range)

    async def _parse_with_docling(
        self,
        file_path: str | Path,
        ocr: bool = True,
        page_range: tuple[int, int] | None = None,
    ) -> list[Block]:
        """使用 Docling 解析。"""
        from docling.document_converter import DocumentConverter
        from docling.datamodel.pipeline_options import PdfPipelineOptions

        pipeline_opts = PdfPipelineOptions()
        pipeline_opts.do_ocr = ocr
        pipeline_opts.do_table_structure = True

        converter = DocumentConverter()
        result = converter.convert(str(file_path))

        blocks: list[Block] = []
        doc = result.document

        for item_id, item in doc.iterate_items():
            block = self._docling_item_to_block(item, str(file_path))
            if block:
                blocks.append(block)

        # 排序和编号
        for i, block in enumerate(blocks):
            block.order_index = i

        return blocks

    def _docling_item_to_block(
        self, item: Any, file_name: str
    ) -> Block | None:
        """将 Docling item 转换为 Block。"""
        from docling.datamodel.base_models import ItemType

        item_type = item.get_type()
        text = item.get_text() or ""
        if not text and item_type not in (ItemType.PICTURE, ItemType.TABLE):
            return None

        block_type = self._map_docling_type(item_type)
        page_num = self._get_item_page(item)
        heading_path = self._get_heading_path(item)

        bbox = None
        if hasattr(item, "bbox") and item.bbox:
            bbox = {
                "x0": item.bbox.l,
                "y0": item.bbox.t,
                "x1": item.bbox.r,
                "y1": item.bbox.b,
            }

        table_data = None
        if item_type == ItemType.TABLE:
            table_data = self._extract_table(item)

        return ParsedBlock(
            
            
            
            block_type=block_type,
            page_number=page_num,
            heading_path=heading_path,
            heading_level=self._get_heading_level(item),
            text=text,
            text_length=len(text),
            table_data=table_data,
            bbox=bbox,
            order_index=0,
            depth=self._get_heading_level(item) or 0,
            block_metadata={"docling_type": str(item_type)},
        )

    def _map_docling_type(self, item_type: Any) -> BlockType:
        """映射 Docling 类型到 BlockType。"""
        from docling.datamodel.base_models import ItemType

        mapping = {
            ItemType.TITLE: BlockType.TITLE,
            ItemType.HEADING: BlockType.HEADING,
            ItemType.PARAGRAPH: BlockType.PARAGRAPH,
            ItemType.TABLE: BlockType.TABLE,
            ItemType.PICTURE: BlockType.IMAGE,
            ItemType.LIST: BlockType.LIST,
            ItemType.FORMULA: BlockType.FORMULA,
            ItemType.CODE: BlockType.CODE,
            ItemType.QUOTE: BlockType.QUOTE,
            ItemType.CAPTION: BlockType.CAPTION,
            ItemType.FOOTER: BlockType.FOOTER,
            ItemType.HEADER: BlockType.HEADER,
        }
        return mapping.get(item_type, BlockType.OTHER)

    def _get_item_page(self, item: Any) -> int | None:
        """获取 item 所在页码。"""
        try:
            if hasattr(item, "prov") and item.prov:
                return item.prov[0].page_no
        except (IndexError, AttributeError):
            pass
        return None

    def _get_heading_path(self, item: Any) -> str | None:
        """获取标题路径。"""
        try:
            if hasattr(item, "heading") and item.heading:
                return item.heading
        except AttributeError:
            pass
        return None

    def _get_heading_level(self, item: Any) -> int | None:
        """获取标题层级。"""
        try:
            if hasattr(item, "level") and item.level is not None:
                return item.level
        except AttributeError:
            pass
        return None

    def _extract_table(self, item: Any) -> dict | None:
        """提取表格数据。"""
        try:
            import pandas as pd
            from docling.datamodel.base_models import ItemType

            if item.get_type() != ItemType.TABLE:
                return None

            df: pd.DataFrame = item.get_data()
            if df is None or df.empty:
                return None

            return {
                "headers": list(df.columns),
                "rows": df.values.tolist(),
                "num_rows": len(df),
                "num_cols": len(df.columns),
            }
        except Exception as e:
            logger.debug("Table extraction failed", error=str(e))
            return None

    # ─── PyMuPDF 回退 ───

    async def _parse_with_pymupdf(
        self,
        file_path: str | Path,
        page_range: tuple[int, int] | None = None,
    ) -> list[Block]:
        """PyMuPDF 回退解析（纯文本+基本结构）。"""
        import fitz

        blocks: list[Block] = []
        doc = fitz.open(str(file_path))

        start_page, end_page = page_range or (0, len(doc) - 1)

        for page_num in range(start_page, end_page + 1):
            page = doc[page_num]
            page_blocks = page.get_text("dict")["blocks"]

            for block_dict in page_blocks:
                block = self._pymupdf_block_to_block(block_dict, file_name=str(file_path), page_num=page_num)
                if block:
                    blocks.append(block)

        doc.close()

        for i, block in enumerate(blocks):
            block.order_index = i

        return blocks

    def _pymupdf_block_to_block(
        self, block_dict: dict, file_name: str, page_num: int
    ) -> Block | None:
        """将 PyMuPDF block dict 转换为 Block。"""
        block_type = block_dict.get("type", 0)
        bbox = block_dict.get("bbox")

        bbox_dict = None
        if bbox:
            bbox_dict = {"x0": bbox[0], "y0": bbox[1], "x1": bbox[2], "y1": bbox[3]}

        if block_type == 0:  # 文本
            text = ""
            for line in block_dict.get("lines", []):
                for span in line.get("spans", []):
                    text += span.get("text", "") + " "
                text += "\n"
            text = text.strip()
            if not text:
                return None

            # 尝试判断标题（字体大小）
            heading_level = None
            heading_path = None
            if block_dict.get("lines"):
                first_span = block_dict["lines"][0].get("spans", [{}])[0]
                font_size = first_span.get("size", 12)
                if font_size >= 18:
                    heading_level = 1
                    heading_path = text[:100]
                elif font_size >= 14:
                    heading_level = 2
                    heading_path = text[:100]

            bt = BlockType.HEADING if heading_level else BlockType.PARAGRAPH

            return ParsedBlock(
                
                
                
                block_type=bt,
                page_number=page_num + 1,
                heading_path=heading_path,
                heading_level=heading_level,
                text=text,
                text_length=len(text),
                bbox=bbox_dict,
                order_index=0,
                depth=heading_level or 0,
                block_metadata={"font_size": str(first_span.get("size", ""))},
            )

        elif block_type == 1:  # 图片
            return ParsedBlock(
                
                
                
                block_type=BlockType.IMAGE,
                page_number=page_num + 1,
                text="[图片]",
                text_length=5,
                bbox=bbox_dict,
                order_index=0,
                depth=0,
                block_metadata={"image_number": block_dict.get("number", 0)},
            )

        return None
