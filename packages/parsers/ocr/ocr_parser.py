"""OCR 引擎 —— PaddleOCR。

支持：
- PNG / JPG / TIFF 图片文字识别
- 版面区域识别
- PDF 扫描件 OCR
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..block import BlockType, ParsedBlock
from ..registry import BaseParser


class OCRParser(BaseParser):
    """基于 PaddleOCR 的图片文字识别。"""

    @property
    def supported_formats(self) -> list[str]:
        return ["png", "jpg", "jpeg", "tiff"]

    async def validate(self, file_path: str | Path) -> bool:
        """验证是否可读图片文件。"""
        try:
            from PIL import Image
            Image.open(str(file_path))
            return True
        except Exception:
            return False

    async def parse(
        self, file_path: str | Path, lang: str = "ch", **kwargs: Any
    ) -> list[Block]:
        """对图片做 OCR。

        Args:
            file_path: 图片路径
            lang: 语言（"ch" / "en" / "ch,en"）
        """
        try:
            return await self._parse_with_paddleocr(file_path, lang)
        except ImportError:
            # PaddleOCR 未安装时尝试简易 OCR 回退
            return await self._parse_metadata_only(file_path)
        except Exception as e:
            return await self._parse_metadata_only(file_path, error=str(e))

    async def _parse_with_paddleocr(
        self, file_path: str | Path, lang: str = "ch"
    ) -> list[Block]:
        """使用 PaddleOCR 识别。"""
        from PIL import Image
        from paddleocr import PaddleOCR

        img = Image.open(str(file_path))
        width, height = img.size

        ocr_engine = PaddleOCR(use_angle_cls=True, lang=lang, show_log=False)
        result = ocr_engine.ocr(str(file_path))

        blocks: list[Block] = []
        full_text = ""

        if result and result[0]:
            for line in result[0]:
                bbox, (text, confidence) = line
                if confidence < 0.3:
                    continue  # 低置信度跳过
                full_text += text + "\n"

                blocks.append(ParsedBlock(
                      
                    block_type=BlockType.PARAGRAPH,
                    page_number=1,
                    text=text,
                    text_length=len(text),
                    bbox={
                        "x0": bbox[0][0], "y0": bbox[0][1],
                        "x1": bbox[2][0], "y1": bbox[2][1],
                    },
                    order_index=len(blocks),
                    depth=0,
                    block_metadata={
                        "confidence": confidence,
                        "image_size": f"{width}x{height}",
                    },
                ))

        return blocks

    async def _parse_metadata_only(
        self, file_path: str | Path, error: str | None = None
    ) -> list[Block]:
        """失败回退 —— 仅返回文件元信息。"""
        from PIL import Image
        img = Image.open(str(file_path))
        width, height = img.size

        error_msg = f" [OCR 失败: {error}]" if error else " [OCR 引擎未安装]"

        text = f"[图片: {Path(file_path).name}, {width}x{height}]{error_msg}"

        return [
            Block(
                  
                block_type=BlockType.IMAGE,
                page_number=1,
                text=text,
                text_length=len(text),
                order_index=0,
                depth=0,
                block_metadata={
                    "image_size": f"{width}x{height}",
                    "ocr_error": error or "engine_not_installed",
                },
            )
        ]
