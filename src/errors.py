"""
Custom exception hierarchy for AEIA system.
Provides clear error categorization for upstream LLM, Vector DB, and corpus issues.
"""

from typing import Optional


class AEIAError(Exception):
    """Base exception for all AEIA domain errors."""

    def __init__(self, message: str, status_code: int = 500, error_code: str = "INTERNAL_ERROR"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code


class LLMQuotaExceededError(AEIAError):
    """Raised when Gemini or external LLM API rate limit or quota is exhausted (HTTP 429)."""

    def __init__(self, message: str = "LLM API quota exceeded. Please retry in a few moments.", retry_after: Optional[int] = None):
        super().__init__(message, status_code=429, error_code="LLM_QUOTA_EXHAUSTED")
        self.retry_after = retry_after


class LLMServiceUnavailableError(AEIAError):
    """Raised when the LLM service is unreachable or returns 503."""

    def __init__(self, message: str = "LLM service is currently unavailable."):
        super().__init__(message, status_code=503, error_code="LLM_UNAVAILABLE")


class VectorDBUnavailableError(AEIAError):
    """Raised when Qdrant vector database is unreachable."""

    def __init__(self, message: str = "Vector database (Qdrant) connection failed. Ensure Qdrant is running at http://localhost:6333."):
        super().__init__(message, status_code=503, error_code="VECTOR_DB_UNAVAILABLE")


class CorpusUnavailableError(AEIAError):
    """Raised when the target corpus or git repository cannot be accessed."""

    def __init__(self, message: str = "Target codebase corpus not found or inaccessible."):
        super().__init__(message, status_code=500, error_code="CORPUS_UNAVAILABLE")

