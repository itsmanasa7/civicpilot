import os
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field

from .chunker import Chunker
from .db import RAGDatabase
from .gemini import GeminiClient


class AskRequest(BaseModel):
    question: str = Field(..., description="The citizen's query about PM-KISAN")
    lang: str = Field(default="en", description="Language code: 'en' for English, 'hi' for Hindi")


class Citation(BaseModel):
    id: str = Field(..., description="Stable clause/section ID, e.g. PMK-G-4.2")
    text: str = Field(..., description="The clause excerpt or text cited")


class AskResponse(BaseModel):
    answer: str = Field(..., description="Grounded answer citing clause IDs")
    citations: List[Citation] = Field(default_factory=list, description="List of cited clauses")
    confidence: float = Field(..., description="Confidence score from 0.0 to 1.0")
    needs_escalation: bool = Field(..., description="True if query cannot be answered from corpus")


class RAGService:
    """Orchestrates indexing of /corpus/pmkisan and grounded QA via FTS5 and embeddings."""

    def __init__(self, db_path: Optional[str] = None, gemini_client: Optional[GeminiClient] = None):
        self.db = RAGDatabase(db_path=db_path)
        self.gemini = gemini_client or GeminiClient()

    def resolve_corpus_dir(self, explicit_path: Optional[str] = None) -> Optional[Path]:
        """Resolves corpus directory from explicit path, env var, or conventional locations."""
        candidates = []
        if explicit_path:
            candidates.append(Path(explicit_path))
        if os.getenv("CORPUS_DIR"):
            candidates.append(Path(os.getenv("CORPUS_DIR")))

        # Workspace relative paths
        here = Path(__file__).resolve().parent
        candidates.extend([
            here.parent.parent / "corpus" / "pmkisan",
            here.parent / "corpus" / "pmkisan",
            Path.cwd() / "corpus" / "pmkisan",
            Path.cwd().parent / "corpus" / "pmkisan",
            Path("corpus/pmkisan"),
            Path("../corpus/pmkisan"),
            Path("c:/civicpilot/corpus/pmkisan"),
        ])

        for c in candidates:
            if c.exists() and c.is_dir():
                return c
        return None

    def index_corpus(self, corpus_dir: Optional[str] = None, clean: bool = True) -> int:
        """Chunks all markdown/text files in corpus dir and stores in SQLite FTS5 + embeddings."""
        resolved = self.resolve_corpus_dir(corpus_dir)
        if not resolved:
            return 0

        if clean:
            self.db.clear()

        chunks = Chunker.chunk_directory(resolved)
        count = 0
        for chunk in chunks:
            embedding = self.gemini.get_embedding(chunk.text)
            self.db.save_chunk(chunk, embedding)
            count += 1

        return count

    def ask(self, question: str, lang: str = "en") -> AskResponse:
        """Performs hybrid retrieval and grounded QA strictly constrained to PM-KISAN clauses."""
        q_clean = question.strip()
        if not q_clean:
            return AskResponse(
                answer="Question cannot be empty.",
                citations=[],
                confidence=0.0,
                needs_escalation=True,
            )

        # 1. Compute question embedding
        query_emb = self.gemini.get_embedding(q_clean)

        # 2. Hybrid search across FTS5 and embeddings
        search_results = self.db.search_hybrid(q_clean, query_emb, limit=3)

        if not search_results:
            return AskResponse(
                answer=(
                    "पीएम-किसान डेटाबेस में इस प्रश्न से संबंधित कोई नियम नहीं मिला। इसे नोडल अधिकारी को अग्रेषित किया जाना आवश्यक है।"
                    if lang == "hi"
                    else "No relevant clauses were found in the PM-KISAN corpus to answer this query. This matter requires escalation."
                ),
                citations=[],
                confidence=0.0,
                needs_escalation=True,
            )

        # 3. Format retrieved clauses for LLM / grounded engine
        retrieved_clauses = [
            {"id": chunk.id, "title": chunk.title, "text": chunk.text, "score": score}
            for chunk, score in search_results
        ]

        # 4. Generate answer constrained to retrieved clauses
        result = self.gemini.generate_answer(q_clean, retrieved_clauses, lang=lang)

        # 5. Format citations
        raw_citations = result.get("citations", [])
        citations: List[Citation] = []
        for c in raw_citations:
            cid = c.get("id") if isinstance(c, dict) else str(c)
            ctext = c.get("text", "") if isinstance(c, dict) else ""
            if not ctext:
                # lookup chunk text if not provided
                found = self.db.get_chunk(cid)
                if found:
                    ctext = found.text
            if cid:
                citations.append(Citation(id=cid, text=ctext))

        needs_escalation = bool(result.get("needs_escalation", False))
        confidence = float(result.get("confidence", 0.0))

        # Enforce rule: if confidence is 0 or needs_escalation is True, no false answers
        if needs_escalation:
            citations = []

        return AskResponse(
            answer=result.get("answer", ""),
            citations=citations,
            confidence=confidence,
            needs_escalation=needs_escalation,
        )
