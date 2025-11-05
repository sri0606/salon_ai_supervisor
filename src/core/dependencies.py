from functools import lru_cache
from src.services.knowledge_base import KnowledgeBaseService
from .config import settings

# Singleton instances (initialized once)
_kb_service = None
_help_request_service = None


def get_knowledge_base_service() -> KnowledgeBaseService:
    """
    Dependency for knowledge base service
    Returns singleton instance
    """
    global _kb_service
    if _kb_service is None:
        _kb_service = KnowledgeBaseService(db_path=settings.database_path)
    return _kb_service


def get_help_request_service():
    """
    Dependency for help request service
    Returns singleton instance
    """
    global _help_request_service
    if _help_request_service is None:
        # 🔽 import moved here to break circular dependency
        from src.services.help_request import HelpRequestService
        _help_request_service = HelpRequestService(
            db_path=settings.database_path,
            timeout_hours=settings.help_request_timeout_hours
        )
    return _help_request_service