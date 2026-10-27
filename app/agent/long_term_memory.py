from __future__ import annotations

import logging
import math
import os
import sqlite3
import struct
import time
from typing import Callable, List, Optional, Tuple


logger = logging.getLogger(__name__)


# A retrieved row is (role, content, created_at). Rows are returned in the order
# they should be replayed into a fresh ConversationBufferWindowMemory, i.e.
# oldest first, newest last.
RetrievedRow = Tuple[str, str, float]


def _pack_embedding(vector: List[float]) -> bytes:
    """Pack a float vector into a little-endian float32 BLOB."""
    values = [float(value) for value in vector]
    return struct.pack("<%df" % len(values), *values)


def _unpack_embedding(blob: bytes) -> Optional[List[float]]:
    """Unpack a float32 BLOB back into a vector, or None if it is invalid."""
    try:
        if not blob or len(blob) % 4 != 0:
            return None
        return list(struct.unpack("<%df" % (len(blob) // 4), blob))
    except (struct.error, TypeError, ValueError):
        return None


def _cosine_similarity(left: List[float], right: List[float]) -> float:
    """Cosine similarity between two equal-length vectors."""
    if not left or not right or len(left) != len(right):
        return 0.0

    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


def recent_history_retrieval(
    store: "LongTermMemoryStore",
    user_id: str,
    limit: int,
    now: Optional[float] = None,
) -> List[RetrievedRow]:
    """Fallback retrieval: the most recent ``limit`` messages within the TTL.

    This is used when embeddings are unavailable (no ``embed_fn`` configured,
    or the embedding call fails) so the bot keeps working. Results are ordered
    oldest first for natural replay into a short-term buffer.
    """
    if limit <= 0:
        return []

    now = time.time() if now is None else now
    cutoff = now - store.long_term_ttl_seconds

    try:
        conn = store._open()
    except (sqlite3.Error, OSError) as exc:
        logger.warning("Long-term memory unavailable for retrieval: %s", exc)
        return []

    try:
        with conn:
            rows = conn.execute(
                """
                SELECT role, content, created_at
                FROM conversations
                WHERE user_id = ? AND created_at > ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (user_id, cutoff, limit),
            ).fetchall()
    except sqlite3.Error as exc:
        logger.warning("Long-term memory retrieval failed: %s", exc)
        return []
    finally:
        conn.close()

    # Newest-first comes out of the query; reverse for replay order.
    return [(row[0], row[1], float(row[2])) for row in reversed(rows)]


class LongTermMemoryStore:
    """SQLite-backed long-term conversation memory.

    Every user message and assistant reply is stored as its own row keyed by
    user id and a ``time.time()`` timestamp. Each row also stores a float32
    embedding BLOB produced by ``embed_fn``; ``None`` embeds are allowed and
    simply do not participate in semantic search.

    Vector search strategy: embeddings are stored as BLOBs and ranked with
    Python cosine similarity. ``sqlite-vec`` would be a drop-in alternative for
    in-database ANN search if it is ever installed in this environment; it is
    intentionally not half-wired here.

    The store is defensive: a missing directory, a locked database, or any
    other SQLite/embedding error is logged and treated as a no-op so the bot
    never crashes because long-term memory is unavailable.
    """

    def __init__(
        self,
        db_path: str,
        long_term_ttl_seconds: float,
        embed_fn: Optional[Callable[[str], List[float]]] = None,
        connect_timeout: float = 5.0,
    ) -> None:
        self.db_path = db_path
        self.long_term_ttl_seconds = long_term_ttl_seconds
        self.connect_timeout = connect_timeout
        # One embedding function is used for both writes and queries so the
        # vectors are always comparable.
        self.embed_fn = embed_fn

    def _open(self) -> sqlite3.Connection:
        """Open a connection and make sure the schema exists."""
        parent = os.path.dirname(os.path.abspath(self.db_path))
        if parent:
            os.makedirs(parent, exist_ok=True)

        conn = sqlite3.connect(self.db_path, timeout=self.connect_timeout)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            self._initialize(conn)
        except Exception:
            conn.close()
            raise
        return conn

    def _initialize(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at REAL NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_conversations_user_created
            ON conversations (user_id, created_at)
            """
        )

        # Safe migration: add the embedding column only when it is missing so
        # pre-existing conversations rows are never dropped.
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(conversations)").fetchall()
        }
        if "embedding" not in columns:
            conn.execute("ALTER TABLE conversations ADD COLUMN embedding BLOB")

    def _embed(self, content: str) -> Optional[bytes]:
        """Embed one message for storage. Returns None on any failure."""
        if self.embed_fn is None or not content:
            return None
        try:
            vector = self.embed_fn(content)
            return _pack_embedding(vector)
        except Exception as exc:
            logger.warning("Conversation embedding failed for write: %s", exc)
            return None

    def record_message(
        self,
        user_id: str,
        role: str,
        content: str,
        created_at: Optional[float] = None,
    ) -> bool:
        """Persist a single message. Returns False instead of raising on error."""
        if not content:
            return False

        created_at = time.time() if created_at is None else created_at
        embedding = self._embed(content)
        try:
            conn = self._open()
        except (sqlite3.Error, OSError) as exc:
            logger.warning("Long-term memory unavailable for write: %s", exc)
            return False

        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO conversations
                        (user_id, role, content, created_at, embedding)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (user_id, role, content, created_at, embedding),
                )
            return True
        except sqlite3.Error as exc:
            logger.warning("Long-term memory write failed: %s", exc)
            return False
        finally:
            conn.close()

    def record_exchange(
        self,
        user_id: str,
        user_content: str,
        assistant_content: str,
        created_at: Optional[float] = None,
    ) -> bool:
        """Persist a user turn and its assistant reply in one transaction."""
        if not user_content and not assistant_content:
            return False

        created_at = time.time() if created_at is None else created_at
        user_embedding = self._embed(user_content) if user_content else None
        assistant_embedding = self._embed(assistant_content) if assistant_content else None

        try:
            conn = self._open()
        except (sqlite3.Error, OSError) as exc:
            logger.warning("Long-term memory unavailable for write: %s", exc)
            return False

        try:
            with conn:
                if user_content:
                    conn.execute(
                        """
                        INSERT INTO conversations
                            (user_id, role, content, created_at, embedding)
                        VALUES (?, 'user', ?, ?, ?)
                        """,
                        (user_id, user_content, created_at, user_embedding),
                    )
                if assistant_content:
                    conn.execute(
                        """
                        INSERT INTO conversations
                            (user_id, role, content, created_at, embedding)
                        VALUES (?, 'assistant', ?, ?, ?)
                        """,
                        (user_id, assistant_content, created_at, assistant_embedding),
                    )
            return True
        except sqlite3.Error as exc:
            logger.warning("Long-term memory write failed: %s", exc)
            return False
        finally:
            conn.close()

    def retrieve_relevant(
        self,
        user_id: str,
        query: str,
        top_k: int,
        now: Optional[float] = None,
    ) -> List[RetrievedRow]:
        """Return the most relevant past turns for a user within the TTL.

        The query is embedded with the same ``embed_fn`` used at write time.
        Candidate rows are ranked by cosine similarity, the top ``top_k`` are
        kept, and the result is returned oldest-to-newest so it reads naturally.

        Rows written before the embedding column existed have a NULL embedding;
        they are lazily backfilled here so they remain queryable. If embeddings
        are unavailable the call falls back to recent-history retrieval.
        """
        now = time.time() if now is None else now
        self.prune_user(user_id, now)
        top_k = max(1, int(top_k))

        if not query or self.embed_fn is None:
            return recent_history_retrieval(self, user_id, top_k, now)

        try:
            query_vector = self.embed_fn(query)
        except Exception as exc:
            logger.warning(
                "Embedding the query failed; falling back to recent history: %s",
                exc,
            )
            return recent_history_retrieval(self, user_id, top_k, now)

        cutoff = now - self.long_term_ttl_seconds
        try:
            conn = self._open()
        except (sqlite3.Error, OSError) as exc:
            logger.warning("Long-term memory unavailable for relevance retrieval: %s", exc)
            return []

        rows = []
        try:
            rows = conn.execute(
                """
                SELECT id, role, content, created_at, embedding
                FROM conversations
                WHERE user_id = ? AND created_at > ?
                ORDER BY id ASC
                """,
                (user_id, cutoff),
            ).fetchall()
        except sqlite3.Error as exc:
            logger.warning("Long-term memory relevance retrieval failed: %s", exc)
            return []
        finally:
            conn.close()

        scored: List[Tuple[float, str, str, float]] = []
        backfills: List[Tuple[bytes, int]] = []
        for row_id, role, content, created_at, blob in rows:
            vector = _unpack_embedding(blob) if blob else None
            if vector is None:
                # Lazy backfill for rows that predate the embedding column.
                try:
                    vector = self.embed_fn(content)
                    backfills.append((_pack_embedding(vector), row_id))
                except Exception as exc:
                    logger.warning("Embedding backfill failed for row %s: %s", row_id, exc)

            if vector is None:
                continue

            similarity = _cosine_similarity(query_vector, vector)
            scored.append((similarity, role, content, float(created_at)))

        if backfills:
            self._backfill_embeddings(backfills)

        # Highest similarity first, then replay order (oldest first).
        scored.sort(key=lambda item: item[0], reverse=True)
        top = scored[:top_k]
        top.sort(key=lambda item: item[3])
        return [(role, content, created_at) for _, role, content, created_at in top]

    def _backfill_embeddings(self, updates: List[Tuple[bytes, int]]) -> None:
        try:
            conn = self._open()
        except (sqlite3.Error, OSError) as exc:
            logger.warning("Embedding backfill unavailable: %s", exc)
            return

        try:
            with conn:
                conn.executemany(
                    "UPDATE conversations SET embedding = ? WHERE id = ?",
                    updates,
                )
        except sqlite3.Error as exc:
            logger.warning("Embedding backfill write failed: %s", exc)
        finally:
            conn.close()

    def retrieve_history(
        self,
        user_id: str,
        limit: int,
        now: Optional[float] = None,
    ) -> List[RetrievedRow]:
        """Recent-history retrieval, kept as the non-semantic fallback path."""
        now = time.time() if now is None else now
        self.prune_user(user_id, now)
        return recent_history_retrieval(self, user_id, limit, now)

    def prune_user(self, user_id: str, now: Optional[float] = None) -> int:
        now = time.time() if now is None else now
        cutoff = now - self.long_term_ttl_seconds
        return self._delete("DELETE FROM conversations WHERE user_id = ? AND created_at <= ?", (user_id, cutoff))

    def prune_all(self, now: Optional[float] = None) -> int:
        now = time.time() if now is None else now
        cutoff = now - self.long_term_ttl_seconds
        return self._delete("DELETE FROM conversations WHERE created_at <= ?", (cutoff,))

    def _delete(self, sql: str, params: tuple) -> int:
        try:
            conn = self._open()
        except (sqlite3.Error, OSError) as exc:
            logger.warning("Long-term memory unavailable for prune: %s", exc)
            return 0

        try:
            with conn:
                cursor = conn.execute(sql, params)
                return cursor.rowcount
        except sqlite3.Error as exc:
            logger.warning("Long-term memory prune failed: %s", exc)
            return 0
        finally:
            conn.close()

    def close(self) -> None:
        """No persistent connection is kept, so there is nothing to close."""
