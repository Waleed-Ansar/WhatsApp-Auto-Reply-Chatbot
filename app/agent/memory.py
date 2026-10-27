from __future__ import annotations

import asyncio
import logging
import time
from typing import Callable, Dict, List, Optional

from langchain_classic.memory import ConversationBufferWindowMemory
from langchain_openai import OpenAIEmbeddings

from app.agent.long_term_memory import LongTermMemoryStore
from app.core.config import config


logger = logging.getLogger(__name__)


def _build_default_embed_fn() -> Optional[Callable[[str], List[float]]]:
    """Build the shared embedding function used for writes and queries.

    The same ``embed_query`` method is injected into the store so semantic
    search always compares vectors produced by the same model. If the model
    cannot be constructed (for example no API key), return None and the store
    falls back to recent-history retrieval.
    """
    try:
        model = OpenAIEmbeddings(
            model=config.CHAT_MEMORY_EMBEDDING_MODEL,
            api_key=config.OPENAI_API_KEY,
        )
        return model.embed_query
    except Exception as exc:
        logger.warning(
            "Conversation embedding model unavailable; semantic recall disabled: %s",
            exc,
        )
        return None


class MemoryService:
    """Two-tier memory for the chat agent.

    Tier 1 (short-term, active session)
        A per-user ``ConversationBufferWindowMemory`` kept in memory. It is
        reused while the user stays active (within ``session_ttl_seconds``) and
        discarded once the user has been idle longer than that. Because it is
        a plain in-process dict, it is lost on process restart, which is fine:
        the long-term tier re-seeds a fresh buffer on the next message.

    Tier 2 (long-term, SQLite)
        Every user message and assistant reply is persisted in SQLite. When a
        session expires and the user returns, the most relevant recent history
        within the long-term TTL is retrieved with the same embedding model used
        at write time, and only the top ``top_k`` turns are replayed into a
        fresh short-term buffer. The full history is never loaded.

    Lifecycle
        * Message arrives -> identify user by chat id.
        * Reuse the existing buffer if the user was active recently, otherwise
          discard it and build a fresh one seeded from SQLite.
        * After a reply is generated, both messages are written to SQLite and
          the user's last-active timestamp is updated.
        * Expired rows are pruned lazily per user on return, and globally on a
          periodic schedule (see ``run_periodic_prune``).

    The async methods are the production entry points. ``*_sync`` variants
    contain the same logic without touching an event loop, which keeps the
    core testable in environments where ``asyncio.run`` is unavailable.
    """

    def __init__(
        self,
        *,
        db_path: Optional[str] = None,
        session_ttl_seconds: Optional[float] = None,
        long_term_ttl_seconds: Optional[float] = None,
        window_size: Optional[int] = None,
        top_k: Optional[int] = None,
        prune_interval_seconds: Optional[float] = None,
        long_term_store: Optional[LongTermMemoryStore] = None,
        embed_fn: Optional[Callable[[str], List[float]]] = None,
    ) -> None:
        self.user_memories: Dict[str, ConversationBufferWindowMemory] = {}
        self.user_last_active: Dict[str, float] = {}
        # Slot suggestions used by the appointment flow. Initialized here so the
        # existing get/set/clear helpers never hit a missing attribute.
        self.user_slot_suggestions: Dict[str, list] = {}
        self._lock = asyncio.Lock()

        self.session_ttl_seconds = (
            config.CHAT_MEMORY_SESSION_TTL_SECONDS
            if session_ttl_seconds is None
            else float(session_ttl_seconds)
        )
        self.window_size = (
            config.CHAT_MEMORY_WINDOW_SIZE if window_size is None else int(window_size)
        )
        self.top_k = config.CHAT_MEMORY_TOP_K if top_k is None else int(top_k)
        self.prune_interval_seconds = (
            config.CHAT_MEMORY_PRUNE_INTERVAL_SECONDS
            if prune_interval_seconds is None
            else float(prune_interval_seconds)
        )

        if long_term_store is not None:
            self.long_term = long_term_store
        else:
            long_term_ttl = (
                config.CHAT_MEMORY_LONG_TERM_TTL_SECONDS
                if long_term_ttl_seconds is None
                else float(long_term_ttl_seconds)
            )
            resolved_embed_fn = embed_fn if embed_fn is not None else _build_default_embed_fn()
            self.long_term = LongTermMemoryStore(
                db_path=config.CHAT_MEMORY_DB_PATH if db_path is None else db_path,
                long_term_ttl_seconds=long_term_ttl,
                embed_fn=resolved_embed_fn,
            )

    async def get_or_create_user_memory(
        self,
        chat_id: str,
        *,
        window_size: Optional[int] = None,
        query: Optional[str] = None,
        top_k: Optional[int] = None,
    ) -> ConversationBufferWindowMemory:
        """Return this user's active buffer, re-seeding it if the session expired."""
        window_size = self.window_size if window_size is None else int(window_size)
        now = time.time()

        existing = self.user_memories.get(chat_id)
        if existing is not None and self._is_active(chat_id, now):
            self.user_last_active[chat_id] = now
            return existing

        async with self._lock:
            return self._build_or_reuse_memory(chat_id, window_size, now, query=query, top_k=top_k)

    def get_or_create_user_memory_sync(
        self,
        chat_id: str,
        *,
        window_size: Optional[int] = None,
        query: Optional[str] = None,
        top_k: Optional[int] = None,
    ) -> ConversationBufferWindowMemory:
        """Synchronous variant of :meth:`get_or_create_user_memory`."""
        window_size = self.window_size if window_size is None else int(window_size)
        now = time.time()

        existing = self.user_memories.get(chat_id)
        if existing is not None and self._is_active(chat_id, now):
            self.user_last_active[chat_id] = now
            return existing

        return self._build_or_reuse_memory(chat_id, window_size, now, query=query, top_k=top_k)

    def _build_or_reuse_memory(
        self,
        chat_id: str,
        window_size: int,
        now: float,
        query: Optional[str] = None,
        top_k: Optional[int] = None,
    ) -> ConversationBufferWindowMemory:
        existing = self.user_memories.get(chat_id)
        if existing is not None and self._is_active(chat_id, now):
            self.user_last_active[chat_id] = now
            return existing

        # The old buffer is expired (or this is the first message). Drop it and
        # build a fresh one seeded from long-term memory.
        self.user_memories.pop(chat_id, None)
        self.user_last_active.pop(chat_id, None)

        memory = ConversationBufferWindowMemory(
            memory_key="chat_history",
            return_messages=True,
            k=window_size,
        )
        self._seed_memory(memory, chat_id, query, top_k)
        self.user_memories[chat_id] = memory
        self.user_last_active[chat_id] = now
        return memory

    def _is_active(self, chat_id: str, now: float) -> bool:
        last_active = self.user_last_active.get(chat_id)
        if last_active is None:
            return False
        return (now - last_active) <= self.session_ttl_seconds

    def _seed_memory(
        self,
        memory: ConversationBufferWindowMemory,
        chat_id: str,
        query: Optional[str],
        top_k: Optional[int],
    ) -> None:
        """Replay only the top-k relevant long-term turns into a fresh buffer.

        This calls the same ``retrieve_relevant`` used by the
        ``recall_past_conversations`` tool; the tool only adds formatting.
        """
        top_k = self.top_k if top_k is None else int(top_k)
        history = self.long_term.retrieve_relevant(chat_id, query or "", top_k)
        for role, content, _created_at in history:
            if role == "assistant":
                memory.chat_memory.add_ai_message(content)
            else:
                memory.chat_memory.add_user_message(content)

    async def record_exchange(
        self,
        chat_id: str,
        user_content: str,
        assistant_content: str,
    ) -> None:
        """Persist a completed user turn and update the last-active timestamp."""
        self.record_exchange_sync(chat_id, user_content, assistant_content)

    def record_exchange_sync(
        self,
        chat_id: str,
        user_content: str,
        assistant_content: str,
    ) -> None:
        """Synchronous variant of :meth:`record_exchange`."""
        now = time.time()
        self.user_last_active[chat_id] = now

        try:
            self.long_term.record_exchange(chat_id, user_content, assistant_content, now)
        except Exception as exc:
            logger.warning("Failed to persist conversation for %s: %s", chat_id, exc)

        # Lazy per-user prune on each completed turn.
        try:
            self.long_term.prune_user(chat_id, now)
        except Exception as exc:
            logger.warning("Failed to prune conversation for %s: %s", chat_id, exc)

    async def prune_expired_all(self, now: Optional[float] = None) -> int:
        now = time.time() if now is None else now
        try:
            return self.long_term.prune_all(now)
        except Exception as exc:
            logger.warning("Global long-term memory prune failed: %s", exc)
            return 0

    async def run_periodic_prune(self) -> None:
        """Run a global prune on a fixed interval. Cancelled on shutdown."""
        while True:
            await self.prune_expired_all()
            await asyncio.sleep(self.prune_interval_seconds)

    def get_user_slot_suggestions(self, chat_id: str):
        """Get slot suggestions for a specific user"""
        return self.user_slot_suggestions.get(chat_id)

    def set_user_slot_suggestions(self, chat_id: str, suggestions: list):
        """Set slot suggestions for a specific user"""
        self.user_slot_suggestions[chat_id] = suggestions

    def clear_user_slot_suggestions(self, chat_id: str):
        """Clear slot suggestions for a specific user"""
        self.user_slot_suggestions.pop(chat_id, None)

    def get_formatted_memory(self, chat_id: str):
        """Get formatted memory for API response"""
        memory = self.user_memories.get(chat_id)
        if not memory:
            return None

        messages = memory.chat_memory.messages
        return [{"type": msg.type, "content": msg.content} for msg in messages]

    def delete_user_memory(self, chat_id: str):
        """Delete short-term memory (and last-active marker) for a user."""
        existed = chat_id in self.user_memories
        self.user_memories.pop(chat_id, None)
        self.user_last_active.pop(chat_id, None)
        return existed

    def get_all_chat_ids(self):
        """Get all chat IDs with stored memories"""
        return list(self.user_memories.keys())


memory_service = MemoryService()
