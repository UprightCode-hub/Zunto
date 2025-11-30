"""
assistant.processors package exports.

This file exposes the main classes so callers can do:
  from assistant.processors import QueryProcessor, RAGRetriever, RuleEngine, LocalModelAdapter
"""

# Standard exports (import modules directly so names exist on package)
from .local_model import LocalModelAdapter, NoModelAvailable
from .rag_retriever import RAGRetriever, FAQ_MATCH_THRESHOLD
from .rule_engine import RuleEngine, BLOCK_THRESHOLD, RULE_MATCH_THRESHOLD
from .query_processor import QueryProcessor

__all__ = [
    "LocalModelAdapter",
    "NoModelAvailable",
    "RAGRetriever",
    "FAQ_MATCH_THRESHOLD",
    "RuleEngine",
    "BLOCK_THRESHOLD",
    "RULE_MATCH_THRESHOLD",
    "QueryProcessor",
]
