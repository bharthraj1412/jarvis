# history/linker.py
"""
Semantic session linker using ChromaDB.

On session close, the session summary is embedded into a ChromaDB collection.
This allows finding semantically related past sessions and injecting
their context into the current working memory.

Gracefully degrades if ChromaDB is not installed.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


_DB_DIR = Path.home() / ".jarvis" / "history"
_COLLECTION_NAME = "session_links"

_chroma_available = False
try:
    import chromadb
    _chroma_available = True
except ImportError:
    pass


class HistoryLinker:
    """Builds semantic links between JARVIS sessions using ChromaDB embeddings."""

    def __init__(self) -> None:
        self._collection: Any = None
        if _chroma_available:
            try:
                db_path = str(_DB_DIR / ".chromadb_sessions")
                client = chromadb.PersistentClient(path=db_path)
                self._collection = client.get_or_create_collection(
                    name=_COLLECTION_NAME,
                    metadata={"hnsw:space": "cosine"},
                )
            except Exception as e:
                print(f"[HistoryLinker] ChromaDB init failed: {e}")

    @property
    def available(self) -> bool:
        return self._collection is not None

    def on_session_close(self, session_id: str, summary: str, mode: str = "", backend: str = "") -> None:
        """Embed a session summary into the vector store on close."""
        if not self.available or not summary or not summary.strip():
            return
        try:
            self._collection.upsert(
                ids=[session_id],
                documents=[summary],
                metadatas=[{"mode": mode, "backend": backend}],
            )
        except Exception as e:
            print(f"[HistoryLinker] Embed error: {e}")

    def find_related(self, session_id: str, n: int = 5) -> list[dict]:
        """Find sessions semantically related to the given session.

        Returns a list of dicts with keys: session_id, similarity, mode, backend.
        """
        if not self.available:
            return []
        try:
            # Get the document for this session
            result = self._collection.get(ids=[session_id], include=["documents"])
            if not result or not result["documents"] or not result["documents"][0]:
                return []
            query_text = result["documents"][0]

            count = self._collection.count()
            if count <= 1:
                return []

            # Query for similar sessions (n+1 because the session itself will match)
            search = self._collection.query(
                query_texts=[query_text],
                n_results=min(n + 1, count),
                include=["metadatas", "distances"],
            )

            if not search or not search["ids"] or not search["ids"][0]:
                return []

            results = []
            for i, sid in enumerate(search["ids"][0]):
                if sid == session_id:
                    continue
                dist = search["distances"][0][i] if search["distances"] else 0
                meta = search["metadatas"][0][i] if search["metadatas"] else {}
                results.append({
                    "session_id": sid,
                    "similarity": round(1.0 - dist, 3),
                    "mode": meta.get("mode", ""),
                    "backend": meta.get("backend", ""),
                })

            return results[:n]

        except Exception as e:
            print(f"[HistoryLinker] Search error: {e}")
            return []

    def inject_context(self, session_id: str, working_memory: Any) -> int:
        """Inject top-3 related session summaries as context blocks into working memory.

        Returns the number of context blocks injected.
        """
        related = self.find_related(session_id, n=3)
        if not related:
            return 0

        injected = 0
        for rel in related:
            try:
                result = self._collection.get(ids=[rel["session_id"]], include=["documents"])
                if result and result["documents"] and result["documents"][0]:
                    summary = result["documents"][0]
                    context_block = (
                        f"[Related Session Context (similarity: {rel['similarity']:.2f})]:\n"
                        f"{summary[:500]}"
                    )
                    working_memory.add("user", context_block)
                    injected += 1
            except Exception:
                continue

        return injected
