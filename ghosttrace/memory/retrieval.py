"""Relevant memory retrieval using FTS5 full-text search with SQLite fallback."""

from __future__ import annotations

import logging
import re
import time

from ghosttrace.memory.database import DatabaseManager
from ghosttrace.memory.schemas import MemoryCategory, MemoryItem, MemorySearchResult, MemorySource

logger = logging.getLogger("ghosttrace.memory.retrieval")


class MemoryRetriever:
    """Retrieves and ranks relevant memories using FTS5 and token matching."""

    def __init__(
        self,
        db: DatabaseManager,
        repository: object = None,
        settings: object = None,
        max_retrieved: int = 5,
        max_context_chars: int = 4000,
    ) -> None:
        self.db = db
        target_settings = None
        if hasattr(repository, "memory_max_retrieved"):
            target_settings = repository
        elif hasattr(settings, "memory_max_retrieved"):
            target_settings = settings

        if target_settings:
            self.max_retrieved = getattr(target_settings, "memory_max_retrieved", max_retrieved)
            self.max_context_chars = getattr(
                target_settings, "memory_max_context_chars", max_context_chars
            )
        elif isinstance(repository, int):
            self.max_retrieved = repository
            self.max_context_chars = (
                int(settings) if isinstance(settings, int) else max_context_chars
            )
        else:
            self.max_retrieved = max_retrieved
            self.max_context_chars = max_context_chars

    def search_memories(self, query: str, limit: int = 10) -> list[MemorySearchResult]:
        """Alias for retrieve."""
        return self.retrieve(query=query, limit=limit)

    def retrieve_relevant(self, query: str, limit: int = 10) -> list[MemoryItem]:
        """Retrieve relevant MemoryItem records directly."""
        results = self.retrieve(query=query, limit=limit)
        return [r.memory for r in results]

    def retrieve(
        self,
        query: str,
        category: MemoryCategory | str | None = None,
        limit: int | None = None,
    ) -> list[MemorySearchResult]:
        """Search and rank relevant stored memories for a query.

        Args:
            query: The user inquiry or topic string.
            category: Optional category filter.
            limit: Maximum items to return (bounded by self.max_retrieved).

        Returns:
            List of ranked MemorySearchResult instances.
        """
        clean_query = query.strip()
        if not clean_query:
            return []

        effective_limit = min(limit or self.max_retrieved, self.max_retrieved)
        tokens = self._extract_keywords(clean_query)
        if not tokens:
            return []

        # 1. Attempt FTS5 search if available
        results: list[MemorySearchResult] = []
        if self.db.is_fts5_available():
            try:
                results = self._search_fts5(tokens, category=category, limit=effective_limit * 2)
            except Exception as exc:
                logger.warning("FTS5 memory search failed (%s); using fallback search", exc)
                results = []

        # 2. Fallback to SQL LIKE search if FTS5 returned no results or is unavailable
        if not results:
            results = self._search_fallback(tokens, category=category, limit=effective_limit * 2)

        # 3. Deduplicate and apply composite scoring (importance + recency)
        ranked = self._rank_and_bound_results(results, effective_limit)
        return ranked

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract alphanumeric search tokens, stripping stop words and punctuation."""
        raw_tokens = re.findall(r"\b[a-zA-Z0-9_\-\.]{2,}\b", text.lower())
        stop_words = {
            "the",
            "is",
            "at",
            "which",
            "on",
            "and",
            "a",
            "an",
            "in",
            "to",
            "for",
            "of",
            "or",
            "it",
            "my",
            "me",
            "we",
            "can",
            "do",
            "does",
            "how",
            "what",
            "why",
            "who",
            "please",
            "tell",
            "about",
            "with",
            "by",
        }
        tokens = [t for t in raw_tokens if t not in stop_words]
        return tokens[:8]  # Limit tokens for query performance

    def _search_fts5(
        self,
        tokens: list[str],
        category: MemoryCategory | str | None,
        limit: int,
    ) -> list[MemorySearchResult]:
        """Execute FTS5 MATCH query with BM25 ranking."""
        fts_query = " OR ".join(f'"{t}"*' for t in tokens)
        cat_val = (
            category.value
            if isinstance(category, MemoryCategory)
            else (category.upper() if category else None)
        )

        with self.db.connection() as conn:
            cur = conn.cursor()
            try:
                if cat_val:
                    cur.execute(
                        """
                        SELECT m.id, m.category, m.content, m.source, m.importance,
                               m.created_at, m.updated_at, bm25(memories_fts) AS bm25_score
                        FROM memories_fts f
                        JOIN memories m ON f.rowid = m.id
                        WHERE memories_fts MATCH ? AND m.category = ?
                        ORDER BY bm25_score ASC
                        LIMIT ?;
                        """,
                        (fts_query, cat_val, limit),
                    )
                else:
                    cur.execute(
                        """
                        SELECT m.id, m.category, m.content, m.source, m.importance,
                               m.created_at, m.updated_at, bm25(memories_fts) AS bm25_score
                        FROM memories_fts f
                        JOIN memories m ON f.rowid = m.id
                        WHERE memories_fts MATCH ?
                        ORDER BY bm25_score ASC
                        LIMIT ?;
                        """,
                        (fts_query, limit),
                    )

                rows = cur.fetchall()
                results: list[MemorySearchResult] = []
                for r in rows:
                    item = MemoryItem(
                        id=int(r["id"]),
                        category=MemoryCategory(r["category"]),
                        content=str(r["content"]),
                        source=MemorySource(r["source"]),
                        importance=float(r["importance"]),
                        created_at=float(r["created_at"]),
                        updated_at=float(r["updated_at"]),
                    )
                    # Convert negative BM25 score to positive relevance score
                    raw_score = float(r["bm25_score"])
                    norm_score = max(0.1, 10.0 / (abs(raw_score) + 1.0))
                    results.append(
                        MemorySearchResult(memory=item, score=norm_score, match_source="fts5")
                    )

                return results
            finally:
                cur.close()

    def _search_fallback(
        self,
        tokens: list[str],
        category: MemoryCategory | str | None,
        limit: int,
    ) -> list[MemorySearchResult]:
        """Fallback keyword search using SQL LIKE conditions."""
        conditions: list[str] = []
        params: list[object] = []

        for t in tokens:
            conditions.append("content LIKE ?")
            params.append(f"%{t}%")

        if not conditions:
            return []

        where_clause = " OR ".join(conditions)
        cat_val = (
            category.value
            if isinstance(category, MemoryCategory)
            else (category.upper() if category else None)
        )

        with self.db.connection() as conn:
            cur = conn.cursor()
            try:
                if cat_val:
                    sql = f"""
                        SELECT id, category, content, source, importance, created_at, updated_at
                        FROM memories
                        WHERE ({where_clause}) AND category = ?
                        ORDER BY importance DESC, created_at DESC
                        LIMIT ?;
                    """
                    params.extend([cat_val, limit])
                else:
                    sql = f"""
                        SELECT id, category, content, source, importance, created_at, updated_at
                        FROM memories
                        WHERE {where_clause}
                        ORDER BY importance DESC, created_at DESC
                        LIMIT ?;
                    """
                    params.append(limit)

                cur.execute(sql, params)
                rows = cur.fetchall()
                results: list[MemorySearchResult] = []
                for r in rows:
                    content_lower = str(r["content"]).lower()
                    match_count = sum(1 for t in tokens if t in content_lower)
                    item = MemoryItem(
                        id=int(r["id"]),
                        category=MemoryCategory(r["category"]),
                        content=str(r["content"]),
                        source=MemorySource(r["source"]),
                        importance=float(r["importance"]),
                        created_at=float(r["created_at"]),
                        updated_at=float(r["updated_at"]),
                    )
                    results.append(
                        MemorySearchResult(
                            memory=item,
                            score=float(match_count),
                            match_source="like",
                        )
                    )

                return results
            finally:
                cur.close()

    def _rank_and_bound_results(
        self,
        results: list[MemorySearchResult],
        limit: int,
    ) -> list[MemorySearchResult]:
        """Sort by composite score, eliminate duplicates, and enforce character limits."""
        seen_ids: set[int] = set()
        unique_results: list[MemorySearchResult] = []
        now = time.time()

        for res in results:
            if res.memory.id in seen_ids:
                continue
            seen_ids.add(res.memory.id)

            # Recency factor: decay over 30 days
            age_days = (now - res.memory.created_at) / 86400.0
            recency_mult = max(0.5, 1.0 - (age_days * 0.01))

            # Importance factor: 1.0 + (importance * 0.25)
            importance_mult = 1.0 + (res.memory.importance * 0.25)

            composite_score = res.score * importance_mult * recency_mult
            unique_results.append(
                MemorySearchResult(
                    memory=res.memory,
                    score=round(composite_score, 3),
                    match_source=res.match_source,
                )
            )

        unique_results.sort(key=lambda r: r.score, reverse=True)

        # Enforce max context character bounds
        bounded: list[MemorySearchResult] = []
        current_chars = 0
        for res in unique_results:
            item_len = len(res.memory.content)
            if current_chars + item_len > self.max_context_chars:
                break
            bounded.append(res)
            current_chars += item_len
            if len(bounded) >= limit:
                break

        return bounded
