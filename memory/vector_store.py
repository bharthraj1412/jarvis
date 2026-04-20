# memory/vector_store.py
"""
ChromaDB-backed vector memory for JARVIS MK37.

BUG-FIX (Critical): Unconditional imports of `chromadb` and
`sentence-transformers` caused an ImportError crash on any machine
where those optional packages are not installed.  All heavy imports
are now inside a try/except guard; the class degrades gracefully to a
no-op when the dependencies are absent.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

_DB_PATH = str(Path(__file__).resolve().parent.parent / "memory_db")

# ── Optional dependency guard ─────────────────────────────────────────────
_CHROMA_AVAILABLE = False
_EF_AVAILABLE = False

try:
    import chromadb  # type: ignore
    _CHROMA_AVAILABLE = True
except ImportError:
    pass

try:
    from chromadb.utils.embedding_functions import (  # type: ignore
        SentenceTransformerEmbeddingFunction,
    )
    _EF_AVAILABLE = True
except ImportError:
    pass


class VectorMemory:
    """
    Thin wrapper around a ChromaDB persistent collection.

    Degrades gracefully: if chromadb / sentence-transformers are not
    installed, every method is a documented no-op so the rest of the
    application keeps working without vector search.
    """

    def __init__(self, collection_name: str = "jarvis"):
        self._collection = None
        self._available = False

        if not (_CHROMA_AVAILABLE and _EF_AVAILABLE):
            print(
                "[VectorMemory] ⚠️  chromadb / sentence-transformers not installed. "
                "Vector memory disabled.  Run: pip install chromadb sentence-transformers"
            )
            return

        try:
            ef = SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )
            client = chromadb.PersistentClient(path=_DB_PATH)
            self._collection = client.get_or_create_collection(
                name=collection_name,
                embedding_function=ef,
            )
            self._available = True
        except Exception as e:
            print(f"[VectorMemory] ⚠️  Initialisation failed: {e}")

    # ── Public API ────────────────────────────────────────────────────────

    def store(
        self,
        text: str,
        metadata: Optional[dict] = None,
        doc_id: Optional[str] = None,
    ) -> None:
        """Embed and persist a text snippet.  No-op if unavailable."""
        if not self._available or not self._collection:
            return
        import uuid
        try:
            self._collection.add(
                documents=[text],
                metadatas=[metadata or {}],
                ids=[doc_id or str(uuid.uuid4())],
            )
        except Exception as e:
            print(f"[VectorMemory] ⚠️  store() failed: {e}")

    def recall(self, query: str, n: int = 5) -> list[str]:
        """Return the top-n semantically similar snippets.  Returns [] if unavailable."""
        if not self._available or not self._collection:
            return []
        try:
            count = self._collection.count()
            if count == 0:
                return []
            results = self._collection.query(
                query_texts=[query],
                n_results=min(n, count),
            )
            return results["documents"][0] if results.get("documents") else []
        except Exception as e:
            print(f"[VectorMemory] ⚠️  recall() failed: {e}")
            return []

    @property
    def available(self) -> bool:
        """True if the vector store is operational."""
        return self._available
