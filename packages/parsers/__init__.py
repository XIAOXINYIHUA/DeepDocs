"""解析器注册初始化 —— 注册所有内置解析器。"""

from __future__ import annotations

from .registry import ParserRegistry

# 全局注册表单例
registry = ParserRegistry()


def register_builtin_parsers() -> None:
    """注册所有内置解析器。"""
    from .data.data_parsers import CsvParser, JsonParser
    from .markup.text_parsers import HtmlParser, MarkdownParser, TextParser
    from .office.docx_parser import DocxParser
    from .office.pptx_parser import PptxParser
    from .office.xlsx_parser import XlsxParser
    from .pdf.parser import DoclingPDFParser

    registry.register(DoclingPDFParser())
    registry.register(DocxParser())
    registry.register(PptxParser())
    registry.register(XlsxParser())
    registry.register(HtmlParser())
    registry.register(MarkdownParser())
    registry.register(TextParser())
    registry.register(CsvParser())
    registry.register(JsonParser())


# 自动注册
register_builtin_parsers()
