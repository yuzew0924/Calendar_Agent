"""AI integration boundary for preference parsing."""

from .client import AIClient, AIClientSettings, get_ai_client
from .context import AICourseCatalogContext, build_ai_course_context

__all__ = [
    "AIClient",
    "AIClientSettings",
    "AICourseCatalogContext",
    "build_ai_course_context",
    "get_ai_client",
]
