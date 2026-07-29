"""领域异常定义。"""

from __future__ import annotations


class DeepDocsError(Exception):
    """所有领域异常的基类。"""

    def __init__(self, message: str, code: str | None = None) -> None:
        self.message = message
        self.code = code
        super().__init__(message)


class ConfigurationError(DeepDocsError):
    """配置错误（API Key 缺失、模型配置不完整等）。"""


class AuthenticationError(DeepDocsError):
    """认证失败。"""


class PermissionDenied(DeepDocsError):
    """权限不足。"""


class ResourceNotFound(DeepDocsError):
    """资源不存在。"""


class ResourceConflict(DeepDocsError):
    """资源冲突（重复上传等）。"""


class ParsingError(DeepDocsError):
    """文档解析失败。"""


class UnsupportedFormat(ParsingError):
    """不支持的文档格式。"""


class EmbeddingMismatch(DeepDocsError):
    """Embedding 签名不匹配，无法写入索引。"""


class ProviderError(DeepDocsError):
    """Provider 调用失败。"""


class ProviderRateLimit(ProviderError):
    """调用频率限制。"""


class ProviderTimeout(ProviderError):
    """Provider 超时。"""


class ContextOverflow(DeepDocsError):
    """上下文过长，无法生成。"""


class QuotaExceeded(DeepDocsError):
    """配额超限。"""
