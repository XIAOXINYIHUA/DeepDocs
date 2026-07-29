"""引用校验 —— 确保每个引用的内容真实存在于原文档。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass
class Citation:
    document_id: str
    file_name: str
    page_number: int | None = None
    heading_path: str | None = None
    excerpt: str = ""
    relevance_score: float = 0.0
    answer_start: int | None = None
    answer_end: int | None = None


@dataclass
class CitationResult:
    citations: list[Citation] = field(default_factory=list)
    unsupported_claims: list[str] = field(default_factory=list)
    total_citations: int = 0
    valid_citations: int = 0


class CitationVerifier:
    """验证 LLM 生成回答中的引用是否真实。"""

    def verify(
        self,
        answer: str,
        evidence_chunks: list[dict[str, Any]],
    ) -> CitationResult:
        """验证引用准确性。

        Args:
            answer: LLM 生成的回答文本
            evidence_chunks: 提供给 LLM 的证据块列表

        Returns:
            CitationResult: 包含验证过的引用和未被支持的声明
        """
        result = CitationResult()

        # 1. 从回答中提取引用标记
        citations_found = self._extract_citations(answer, evidence_chunks)
        result.citations = citations_found
        result.total_citations = len(citations_found)

        # 2. 验证每个引用
        for citation in citations_found:
            if self._verify_single_citation(citation, evidence_chunks):
                result.valid_citations += 1
            else:
                result.unsupported_claims.append(citation.excerpt)

        return result

    def _extract_citations(
        self,
        answer: str,
        chunks: list[dict[str, Any]],
    ) -> list[Citation]:
        """从回答中提取引用。

        支持格式：
        - [来源: filename 第N页]
        - [filename, p.N]
        """
        import re

        citations: list[Citation] = []

        # 匹配 [来源: ...] 格式
        pattern = r"\[来源:\s*([^\]]+)\]"
        for match in re.finditer(pattern, answer):
            ref_text = match.group(1)
            pos = match.start()

            # 解析引用文本
            citation = self._parse_reference(ref_text, chunks)
            if citation:
                citation.answer_start = pos
                citation.answer_end = match.end()
                citations.append(citation)

        return citations

    def _parse_reference(
        self, ref_text: str, chunks: list[dict[str, Any]]
    ) -> Citation | None:
        """从引用文本中解析文件、页码等。"""
        import re

        file_name = ref_text.split("第")[0].strip()
        page_match = re.search(r"第(\d+)页", ref_text)
        page_number = int(page_match.group(1)) if page_match else None

        # 在证据块中匹配
        for chunk in chunks:
            chunk_file = chunk.get("file_name", "")
            if file_name in chunk_file or chunk_file in file_name:
                return Citation(
                    document_id=chunk.get("document_id", ""),
                    file_name=chunk_file,
                    page_number=page_number or chunk.get("page_number"),
                    heading_path=chunk.get("heading_path"),
                    excerpt=chunk.get("text", "")[:200],
                    relevance_score=chunk.get("score", 0.0),
                )

        return None

    def _verify_single_citation(
        self, citation: Citation, chunks: list[dict[str, Any]]
    ) -> bool:
        """验证单个引用是否与证据块匹配。"""
        for chunk in chunks:
            if chunk.get("document_id") != citation.document_id:
                continue
            if citation.page_number and chunk.get("page_number") != citation.page_number:
                continue

            # 检查原文是否包含引用的关键内容
            chunk_text = chunk.get("text", "")
            citation_text = citation.excerpt[:100]
            if citation_text in chunk_text or chunk_text[:100] in citation_text:
                return True

        return False
