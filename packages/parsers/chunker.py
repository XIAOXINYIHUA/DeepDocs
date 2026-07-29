"""结构化分块引擎 —— 基于文档结构的智能分块。

策略：
- 以标题为分界点（每个标题及其后续同/子级内容为一个 parent chunk）
- 大段落按 token 预算拆分（保留 heading_path）
- 父子 Chunk 层级（parent 包含完整章节，child 是检索粒度）
- 内容去重 SHA-256 哈希
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from typing import Any

from .block import BlockType, ParsedBlock


@dataclass
class Chunk:
    """分块结果。"""
    document_id: str = ""
    version_id: str = ""
    kb_id: str = ""
    block_type: BlockType = BlockType.PARAGRAPH
    page_number: int | None = None
    heading_path: str | None = None
    text: str = ""
    token_count: int = 0
    parent_chunk_id: str | None = None
    chunk_level: int = 0
    content_hash: str = ""
    block_metadata: dict[str, Any] | None = None


def estimate_tokens(text: str) -> int:
    """快速 token 估算。"""
    import math
    return max(1, math.ceil(len(text) / 1.8))


def compute_hash(text: str, metadata: dict | None = None) -> str:
    """计算内容哈希（用于去重）。"""
    content = text
    if metadata:
        content += str(sorted(metadata.items()))
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class StructureAwareChunker:
    """结构感知分块器。"""

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_blocks(
        self,
        blocks: list[ParsedBlock],
        document_id: str = "",
        version_id: str = "",
        kb_id: str = "",
    ) -> list[Chunk]:
        """将 ParsedBlock 列表分块。

        Args:
            blocks: 有序的 ParsedBlock 列表
            document_id: 文档 ID
            version_id: 版本 ID
            kb_id: 知识库 ID

        Returns:
            list[Chunk]: 分块结果
        """
        chunks: list[Chunk] = []

        if not blocks:
            return chunks

        # Phase 1: 按标题分组
        groups = self._group_by_heading(blocks)

        # Phase 2: 每组生成 chunks
        for heading_path, group_blocks in groups:
            group_chunks = self._chunk_group(
                group_blocks, heading_path,
                document_id, version_id, kb_id,
            )
            chunks.extend(group_chunks)

        # Phase 3: 关联父子 chunk
        # 连续的 heading 层级中，低 level chunk 是同级 chunks 的 parent
        chunks = self._assign_parent_child(chunks)

        return chunks

    def _group_by_heading(
        self, blocks: list[ParsedBlock]
    ) -> list[tuple[str | None, list[ParsedBlock]]]:
        """按标题层级分组。"""
        groups: list[tuple[str | None, list[ParsedBlock]]] = []
        current_heading_path: str | None = None
        current_group: list[ParsedBlock] = []

        for block in blocks:
            if block.block_type in (BlockType.HEADING, BlockType.TITLE):
                # 保存前一个组
                if current_group:
                    groups.append((current_heading_path, current_group))
                current_group = []
                current_heading_path = block.heading_path or block.text
                current_group.append(block)
            else:
                current_group.append(block)

        # 最后一组
        if current_group:
            groups.append((current_heading_path, current_group))

        return groups

    def _chunk_group(
        self,
        blocks: list[ParsedBlock],
        heading_path: str | None,
        document_id: str,
        version_id: str,
        kb_id: str,
    ) -> list[Chunk]:
        """将一组 blocks（同一标题下）分块。"""
        chunks: list[Chunk] = []

        # 先从 group 中分离标题 block
        heading_block = None
        if blocks and blocks[0].block_type in (BlockType.HEADING, BlockType.TITLE):
            heading_block = blocks[0]
            blocks = blocks[1:]

        # 标题单独作为 parent chunk
        if heading_block:
            chunks.append(Chunk(
                document_id=document_id,
                version_id=version_id,
                kb_id=kb_id,
                block_type=heading_block.block_type,
                page_number=heading_block.page_number,
                heading_path=heading_block.heading_path or heading_block.text,
                text=heading_block.text,
                token_count=estimate_tokens(heading_block.text),
                chunk_level=heading_block.depth,
                content_hash=compute_hash(heading_block.text),
            ))

        # 内容块合并分块
        current_text = ""
        current_page = None
        current_blocks: list[str] = []

        for block in blocks:
            block_text = block.text or ""
            if not block_text:
                continue

            # 检查是否需要拆分（按 token 预算）
            merged = (current_text + "\n\n" + block_text).strip()
            if merged and estimate_tokens(merged) > self.chunk_size:
                if current_text:
                    chunks.append(self._make_chunk(
                        text=current_text,
                        block_types=[BlockType.PARAGRAPH],
                        page_number=current_page,
                        heading_path=heading_path,
                        document_id=document_id,
                        version_id=version_id,
                        kb_id=kb_id,
                    ))

                # 如果单块就超预算，截断
                if estimate_tokens(block_text) > self.chunk_size:
                    chunks.extend(self._split_long_chunk(
                        text=block_text,
                        page_number=block.page_number,
                        heading_path=heading_path,
                        block_type=block.block_type,
                        document_id=document_id,
                        version_id=version_id,
                        kb_id=kb_id,
                    ))
                    current_text = ""
                    current_page = None
                    continue

                current_text = block_text
                current_page = block.page_number
            else:
                current_text = merged
                current_page = current_page or block.page_number

        # 最后一组
        if current_text:
            chunks.append(self._make_chunk(
                text=current_text,
                block_types=[BlockType.PARAGRAPH],
                page_number=current_page,
                heading_path=heading_path,
                document_id=document_id,
                version_id=version_id,
                kb_id=kb_id,
            ))

        return chunks

    def _make_chunk(
        self,
        text: str,
        block_types: list[BlockType],
        page_number: int | None,
        heading_path: str | None,
        document_id: str,
        version_id: str,
        kb_id: str,
    ) -> Chunk:
        """创建单个 Chunk。"""
        text = text.strip()
        return Chunk(
            document_id=document_id,
            version_id=version_id,
            kb_id=kb_id,
            block_type=block_types[0] if block_types else BlockType.PARAGRAPH,
            page_number=page_number,
            heading_path=heading_path,
            text=text,
            token_count=estimate_tokens(text),
            chunk_level=0,
            content_hash=compute_hash(text),
        )

    def _split_long_chunk(
        self,
        text: str,
        page_number: int | None,
        heading_path: str | None,
        block_type: BlockType,
        document_id: str,
        version_id: str,
        kb_id: str,
    ) -> list[Chunk]:
        """拆分超长 chunk（按句子边界）。"""
        import re

        sentences = re.split(r"(?<=[。！？.!?])\s*", text)
        chunks: list[Chunk] = []
        current = ""
        size = int(self.chunk_size * 0.8)

        for sent in sentences:
            if not sent.strip():
                continue
            if estimate_tokens(current + sent) > size and current:
                chunks.append(self._make_chunk(
                    text=current, block_types=[block_type],
                    page_number=page_number, heading_path=heading_path,
                    document_id=document_id, version_id=version_id, kb_id=kb_id,
                ))
                current = sent
            else:
                current += sent

        if current:
            chunks.append(self._make_chunk(
                text=current, block_types=[block_type],
                page_number=page_number, heading_path=heading_path,
                document_id=document_id, version_id=version_id, kb_id=kb_id,
            ))

        return chunks

    def _assign_parent_child(
        self, chunks: list[Chunk]
    ) -> list[Chunk]:
        """分配父子关系。"""
        # 相邻 chunks，同一 heading_path 的后续 chunks 是第一个的 child
        # 目前简单实现：所有 chunk 为同级
        for i, chunk in enumerate(chunks):
            if chunk.block_type in (BlockType.HEADING, BlockType.TITLE):
                # 标题是它后面同级别 chunks 的 parent
                for j in range(i + 1, len(chunks)):
                    next_chunk = chunks[j]
                    if next_chunk.block_type in (BlockType.HEADING, BlockType.TITLE):
                        break
                    if not next_chunk.parent_chunk_id:
                        next_chunk.parent_chunk_id = chunk.content_hash
                        next_chunk.chunk_level = 1

        return chunks


def chunk_document(
    blocks: list[ParsedBlock],
    document_id: str = "",
    version_id: str = "",
    kb_id: str = "",
    chunk_size: int = 512,
    chunk_overlap: int = 64,
) -> list[Chunk]:
    """快捷分块函数。"""
    chunker = StructureAwareChunker(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    return chunker.chunk_blocks(blocks, document_id, version_id, kb_id)
