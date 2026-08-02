"""Knowledge Plugin exceptions."""

from mde.exceptions import MDEError


class KnowledgeError(MDEError):
    """Base error shown at the CLI boundary without a traceback."""


class SourceValidationError(KnowledgeError, ValueError):
    """Raised when a source definition is invalid or unsafe."""


class SourceNotFoundError(KnowledgeError, LookupError):
    """Raised when a requested source does not exist."""


class SensitiveAccessError(KnowledgeError, PermissionError):
    """Raised when sensitive agent access lacks explicit confirmation."""


class KnowledgeDatabaseError(KnowledgeError):
    """Raised when the local SQLite index cannot be opened or migrated."""


class KnowledgeContractError(KnowledgeError):
    """Machine-readable integration contract error."""

    def __init__(self, code: str, message: str, **details: str) -> None:
        super().__init__(message)
        self.code = code
        self.details = details
