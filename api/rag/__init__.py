"""CivicPilot RAG Module for PM-KISAN Scheme.
Provides chunking, SQLite FTS5 search, Gemini embeddings, /ask and /explain-notice endpoint logic.
"""

from .chunker import Chunk, Chunker
from .db import RAGDatabase
from .gemini import GeminiClient
from .notice import NoticeExplainer, ExplainNoticeResponse, NoticeCitation
from .service import RAGService, AskRequest, AskResponse, Citation

__all__ = [
    "Chunk",
    "Chunker",
    "RAGDatabase",
    "GeminiClient",
    "NoticeExplainer",
    "ExplainNoticeResponse",
    "NoticeCitation",
    "RAGService",
    "AskRequest",
    "AskResponse",
    "Citation",
]
