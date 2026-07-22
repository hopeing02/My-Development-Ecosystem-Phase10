"""Local, source-scoped Markdown knowledge indexing for MDE."""

from mde.knowledge.models import KnowledgeDocument, KnowledgeSource, SearchResult
from mde.knowledge.service import KnowledgeService

__version__ = "1.2.0"

__all__ = [
    "KnowledgeDocument",
    "KnowledgeService",
    "KnowledgeSource",
    "SearchResult",
    "__version__",
]
