from __future__ import annotations

from mde.exceptions import MDEError


class AIError(MDEError):
    """Base exception for AI provider failures."""


class AIConfigurationError(AIError):
    """Raised when an AI provider is missing required configuration."""


class AITransportError(AIError):
    """Raised when an AI provider request cannot be completed."""


class AIResponseValidationError(AIError):
    """Raised when an AI provider returns an invalid response."""
