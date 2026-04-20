# memory/vector_store.py
from __future__ import annotations

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from pathlib import Path

_DB_PATH = str(Path(__file__).resolve().parent.parent / "memory_db")

class VectorMemory:
    def __init__(self, collection_name: str = "jarvis"):
        self.client = chromadb.PersistentClient(path=_DB_PATH)
        self.ef = SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.ef,
        )

    def store(self, text: str, metadata: dict = None, doc_id: str = None):
        import uuid
        self.collection.add(
            documents=[text],
            metadatas=[metadata or {}],
            ids=[doc_id or str(uuid.uuid4())],
        )

    def recall(self, query: str, n: int = 5) -> list[str]:
        results = self.collection.query(
            query_texts=[query], n_results=n
        )
        return results["documents"][0] if results["documents"] else []
