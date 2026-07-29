"""Office 文档解析器。"""

from .docx_parser import DocxParser
from .pptx_parser import PptxParser
from .xlsx_parser import XlsxParser

__all__ = ["DocxParser", "PptxParser", "XlsxParser"]
