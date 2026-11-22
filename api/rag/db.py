import json
import math
import os
import re
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .chunker import Chunk


def sanitize_fts_query(query: str) -> str:
    """Sanitizes user input into a safe FTS5 query, avoiding syntax errors with dashes or punctuation."""
    words = re.findall(r"[A-Za-z0-9\.]+", query)
    # Remove single characters except numbers/digits
    filtered = [w for w in words if len(w) > 1 or w.isdigit()]
    if not filtered:
        return ""
    # Join with OR and quoted tokens
    return " OR ".join(f'"{w}"' for w in filtered)


class RAGDatabase:
    """SQLite FTS5 + Vector storage engine for PM-KISAN RAG clauses."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            base_dir = Path(__file__).resolve().parent.parent
            self.db_path = str(base_dir / "civicpilot_rag.db")
        else:
            self.db_path = str(db_path)

        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con

    def init_db(self):
        with self.get_connection() as con:
            # Metadata and chunk content table
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS rag_chunks (
                    id TEXT PRIMARY KEY,
                    doc_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    clause_num TEXT,
                    text TEXT NOT NULL,
                    embedding TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            # FTS5 Virtual Table
            con.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS rag_chunks_fts USING fts5(
                    id UNINDEXED,
                    title,
                    text,
                    tokenize='porter unicode61'
                );
                """
            )
            con.commit()

    def clear(self):
        with self.get_connection() as con:
            con.execute("DELETE FROM rag_chunks;")
            con.execute("DELETE FROM rag_chunks_fts;")
            con.commit()

    def save_chunk(self, chunk: Chunk, embedding: Optional[List[float]] = None):
        with self.get_connection() as con:
            emb_json = json.dumps(embedding) if embedding else None
            # Insert or replace in base table
            con.execute(
                """
                INSERT OR REPLACE INTO rag_chunks (id, doc_id, title, clause_num, text, embedding)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (chunk.id, chunk.doc_id, chunk.title, chunk.clause_num, chunk.text, emb_json),
            )
            # Maintain FTS table
            con.execute("DELETE FROM rag_chunks_fts WHERE id = ?;", (chunk.id,))
            con.execute(
                """
                INSERT INTO rag_chunks_fts (id, title, text)
                VALUES (?, ?, ?);
                """,
                (chunk.id, chunk.title, chunk.text),
            )
            con.commit()

    def count(self) -> int:
        with self.get_connection() as con:
            cursor = con.execute("SELECT COUNT(*) FROM rag_chunks;")
            return cursor.fetchone()[0]

    def get_chunk(self, chunk_id: str) -> Optional[Chunk]:
        with self.get_connection() as con:
            row = con.execute("SELECT * FROM rag_chunks WHERE id = ?;", (chunk_id,)).fetchone()
            if not row:
                return None
            return Chunk(
                id=row["id"],
                doc_id=row["doc_id"],
                title=row["title"],
                clause_num=row["clause_num"],
                text=row["text"],
            )

    def search_fts(self, query: str, limit: int = 5) -> List[Tuple[Chunk, float]]:
        """Searches using SQLite FTS5 BM25."""
        clean_q = sanitize_fts_query(query)
        if not clean_q:
            return []

        results: List[Tuple[Chunk, float]] = []
        with self.get_connection() as con:
            try:
                rows = con.execute(
                    """
                    SELECT c.id, c.doc_id, c.title, c.clause_num, c.text, bm25(rag_chunks_fts) as rank
                    FROM rag_chunks c
                    JOIN rag_chunks_fts ON c.id = rag_chunks_fts.id
                    WHERE rag_chunks_fts MATCH ?
                    ORDER BY rank ASC
                    LIMIT ?;
                    """,
                    (clean_q, limit),
                ).fetchall()

                for row in rows:
                    chunk = Chunk(
                        id=row["id"],
                        doc_id=row["doc_id"],
                        title=row["title"],
                        clause_num=row["clause_num"],
                        text=row["text"],
                    )
                    # Normalize BM25 score (rank is negative)
                    raw_rank = float(row["rank"])
                    score = 1.0 / (1.0 + abs(raw_rank))
                    results.append((chunk, score))
            except sqlite3.OperationalError:
                return []

        return results

    def search_vector(
        self, query_embedding: List[float], limit: int = 5
    ) -> List[Tuple[Chunk, float]]:
        """Calculates cosine similarity across all stored chunk embeddings."""
        if not query_embedding:
            return []

        q_norm = math.sqrt(sum(v * v for v in query_embedding))
        if q_norm < 1e-9:
            return []

        scored_chunks: List[Tuple[Chunk, float]] = []
        with self.get_connection() as con:
            rows = con.execute("SELECT id, doc_id, title, clause_num, text, embedding FROM rag_chunks WHERE embedding IS NOT NULL;").fetchall()

            for row in rows:
                if not row["embedding"]:
                    continue
                emb = json.loads(row["embedding"])
                if len(emb) != len(query_embedding):
                    continue

                dot = sum(a * b for a, b in zip(query_embedding, emb))
                d_norm = math.sqrt(sum(v * v for v in emb))
                if d_norm < 1e-9:
                    continue

                cos_sim = dot / (q_norm * d_norm)
                chunk = Chunk(
                    id=row["id"],
                    doc_id=row["doc_id"],
                    title=row["title"],
                    clause_num=row["clause_num"],
                    text=row["text"],
                )
                scored_chunks.append((chunk, float(cos_sim)))

        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        return scored_chunks[:limit]

    def search_hybrid(
        self, query: str, query_embedding: Optional[List[float]] = None, limit: int = 5
    ) -> List[Tuple[Chunk, float]]:
        """Combines FTS5 BM25 and Vector search using Reciprocal Rank Fusion (RRF)."""
        fts_hits = self.search_fts(query, limit=limit * 2)
        vec_hits = self.search_vector(query_embedding, limit=limit * 2) if query_embedding else []

        rrf_scores: Dict[str, float] = {}
        chunk_map: Dict[str, Chunk] = {}

        # RRF k parameter
        k = 60

        for rank, (chunk, score) in enumerate(fts_hits):
            chunk_map[chunk.id] = chunk
            rrf_scores[chunk.id] = rrf_scores.get(chunk.id, 0.0) + (1.0 / (k + rank + 1))

        for rank, (chunk, score) in enumerate(vec_hits):
            chunk_map[chunk.id] = chunk
            rrf_scores[chunk.id] = rrf_scores.get(chunk.id, 0.0) + (1.0 / (k + rank + 1))

        # Sort by combined RRF score
        sorted_ids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)

        combined: List[Tuple[Chunk, float]] = []
        for cid in sorted_ids[:limit]:
            combined.append((chunk_map[cid], rrf_scores[cid]))

        return combined
