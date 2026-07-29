"""解析器和分块器单元测试。"""

from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

from packages.parsers.block import BlockType, ParsedBlock
from packages.parsers.chunker import StructureAwareChunker, chunk_document, estimate_tokens
from packages.parsers.data.data_parsers import CsvParser, JsonParser
from packages.parsers.markup.text_parsers import MarkdownParser, TextParser
from packages.parsers.office.docx_parser import DocxParser
from packages.parsers.office.pptx_parser import PptxParser
from packages.parsers.office.xlsx_parser import XlsxParser
from packages.parsers.registry import ParserRegistry, detect_format


class TestFormatDetection:
    def test_pdf_magic(self):
        assert detect_format("doc.pdf", b"%PDF-1.4") == "pdf"

    def test_txt_by_extension(self):
        assert detect_format("readme.txt", b"hello") == "txt"

    def test_markdown_by_extension(self):
        assert detect_format("readme.md", b"# Title") == "markdown"

    def test_html_detection(self):
        assert detect_format("page.html", b"<html><body>Hi</body></html>") == "html"

    def test_json_detection(self):
        assert detect_format("data.json", b'{"key": "value"}') == "json"

    def test_csv_detection(self):
        assert detect_format("data.csv", b"a,b,c\n1,2,3") == "csv"

    def test_png_magic(self):
        assert detect_format("image.png", b"\x89PNG\r\n\x1a\n") == "png"

    def test_jpg_magic(self):
        assert detect_format("photo.jpg", b"\xff\xd8\xff\xe0") == "jpg"


class TestParserRegistry:
    def test_register_and_get(self):
        registry = ParserRegistry()
        parser = TextParser()
        registry.register(parser)
        assert registry.get_parser("txt") is parser
        assert "txt" in registry.supported_formats()

    def test_can_parse(self):
        registry = ParserRegistry()
        registry.register(TextParser())
        assert registry.can_parse("notes.txt")
        assert not registry.can_parse("notes.xyz")

    def test_duplicate_format_raises(self):
        registry = ParserRegistry()
        registry.register(TextParser())
        with pytest.raises(ValueError, match="already registered"):
            registry.register(TextParser())


class TestMarkdownParser:
    @pytest.mark.asyncio
    async def test_parse_headings(self):
        parser = MarkdownParser()
        with NamedTemporaryFile(suffix=".md", mode="w", delete=False) as f:
            f.write("# Title\n\nSome text.\n\n## Subtitle\n\nMore text.")
            f.flush()
            blocks = await parser.parse(f.name)

        Path(f.name).unlink()

        assert len(blocks) >= 2
        headings = [b for b in blocks if b.block_type == BlockType.HEADING]
        assert len(headings) >= 1
        assert "Title" in headings[0].text

    @pytest.mark.asyncio
    async def test_parse_table(self):
        parser = MarkdownParser()
        content = "| A | B |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |"
        with NamedTemporaryFile(suffix=".md", mode="w", delete=False) as f:
            f.write(content)
            f.flush()
            blocks = await parser.parse(f.name)

        Path(f.name).unlink()

        tables = [b for b in blocks if b.block_type == BlockType.TABLE]
        assert len(tables) >= 1
        assert tables[0].table_data is not None
        assert tables[0].table_data["headers"] == ["A", "B"]


class TestChunker:
    def test_estimate_tokens(self):
        assert estimate_tokens("hello") >= 1
        assert estimate_tokens("你好世界") == 3
        assert estimate_tokens("a" * 100) == 56

    def test_empty_blocks(self):
        result = chunk_document([], )
        assert result == []

    def test_simple_blocks(self):
        blocks = [
            ParsedBlock(
                  
                block_type=BlockType.PARAGRAPH,
                text="Hello World",
                text_length=11,
                order_index=0, depth=0, block_metadata={},
            ),
            ParsedBlock(
                  
                block_type=BlockType.PARAGRAPH,
                text="Second paragraph",
                text_length=16,
                order_index=1, depth=0, block_metadata={},
            ),
        ]
        result = chunk_document(blocks, chunk_size=1000)
        assert len(result) >= 1
        assert result[0].text == "Hello World\n\nSecond paragraph"

    def test_heading_blocks(self):
        blocks = [
            ParsedBlock(
                  
                block_type=BlockType.HEADING,
                heading_path="Intro", heading_level=1,
                text="Introduction", text_length=12,
                order_index=0, depth=1, block_metadata={},
            ),
            ParsedBlock(
                  
                block_type=BlockType.PARAGRAPH,
                text="This is the intro paragraph.",
                text_length=27,
                order_index=1, depth=0, block_metadata={},
            ),
        ]
        result = chunk_document(blocks, chunk_size=1000)
        assert len(result) >= 2
        assert result[0].heading_path == "Intro"

    def test_content_hash(self):
        """验证相同内容产生相同 hash。"""
        blocks = [
            ParsedBlock(
                  
                block_type=BlockType.PARAGRAPH,
                text="Same content", text_length=12,
                order_index=0, depth=0, block_metadata={},
            ),
        ]
        r1 = chunk_document(blocks)
        r2 = chunk_document(blocks)
        assert r1[0].content_hash == r2[0].content_hash

    def test_long_text_split(self):
        """验证超长文本被拆分。"""
        long_text = "句子。" * 500
        blocks = [
            ParsedBlock(
                  
                block_type=BlockType.PARAGRAPH,
                text=long_text, text_length=len(long_text),
                order_index=0, depth=0, block_metadata={},
            ),
        ]
        result = chunk_document(blocks, chunk_size=200)
        assert len(result) >= 1
        for c in result:
            assert estimate_tokens(c.text) <= 250  # 允许少量边界波动


class TestCsvParser:
    @pytest.mark.asyncio
    async def test_parse_csv(self):
        parser = CsvParser()
        content = "name,age,city\nAlice,30,Beijing\nBob,25,Shanghai"
        with NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as f:
            f.write(content)
            f.flush()
            blocks = await parser.parse(f.name)

        Path(f.name).unlink()

        assert len(blocks) == 1
        assert blocks[0].block_type == BlockType.TABLE
        assert blocks[0].table_data is not None
        assert blocks[0].table_data["headers"] == ["name", "age", "city"]
        assert len(blocks[0].table_data["rows"]) == 2


class TestJsonParser:
    @pytest.mark.asyncio
    async def test_parse_json_array(self):
        parser = JsonParser()
        content = '[{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]'
        with NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            f.write(content)
            f.flush()
            blocks = await parser.parse(f.name)

        Path(f.name).unlink()

        assert len(blocks) == 1
        assert blocks[0].block_type == BlockType.TABLE
        assert "Alice" in str(blocks[0].table_data)

    @pytest.mark.asyncio
    async def test_parse_json_object(self):
        parser = JsonParser()
        content = '{"title": "Report", "author": "Alice", "year": 2026}'
        with NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            f.write(content)
            f.flush()
            blocks = await parser.parse(f.name)

        Path(f.name).unlink()

        assert len(blocks) == 1
        assert blocks[0].block_type == BlockType.PARAGRAPH
