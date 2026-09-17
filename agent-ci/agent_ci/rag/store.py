"""ChromaDB vector store for policy chunks."""

from __future__ import annotations

from pathlib import Path

from agent_ci.rag.config import RAGConfig, load_rag_config
from agent_ci.rag.types import PolicyChunk, RetrievedChunk

_store_cache: dict[str, "PolicyVectorStore"] = {}


class PolicyVectorStore:
    """Local ChromaDB collection for company policy chunks."""

    def __init__(self, config: RAGConfig):
        self.config = config
        self._client = None
        self._collection = None

    def _get_collection(self):
        if self._collection is not None:
            return self._collection

        import chromadb
        from chromadb.utils import embedding_functions

        persist_path = Path(self.config.persist_directory)
        persist_path.mkdir(parents=True, exist_ok=True)

        self._client = chromadb.PersistentClient(path=str(persist_path))
        embed_fn = embedding_functions.DefaultEmbeddingFunction()
        self._collection = self._client.get_or_create_collection(
            name=self.config.collection_name,
            embedding_function=embed_fn,
            metadata={"document": self.config.document_name},
        )
        return self._collection

    def count(self) -> int:
        return self._get_collection().count()

    def upsert_chunks(self, chunks: list[PolicyChunk]) -> int:
        collection = self._get_collection()
        if not chunks:
            return 0

        ids = [chunk.chunk_id for chunk in chunks]
        documents = [chunk.text for chunk in chunks]
        metadatas = [
            {
                "document": chunk.document,
                "section": chunk.section,
                "chunk_id": chunk.chunk_id,
            }
            for chunk in chunks
        ]
        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
        return len(chunks)

    def query(self, query_text: str, top_k: int) -> list[RetrievedChunk]:
        collection = self._get_collection()
        if collection.count() == 0:
            return []

        result = collection.query(query_texts=[query_text], n_results=min(top_k, collection.count()))
        retrieved: list[RetrievedChunk] = []

        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        for idx, chunk_id in enumerate(ids):
            metadata = metadatas[idx] if idx < len(metadatas) else {}
            distance = distances[idx] if idx < len(distances) else None
            score = None if distance is None else round(max(0.0, 1.0 - distance), 4)
            retrieved.append(
                RetrievedChunk(
                    chunk_id=metadata.get("chunk_id", chunk_id),
                    document=metadata.get("document", self.config.document_name),
                    section=metadata.get("section", "Unknown"),
                    text=documents[idx] if idx < len(documents) else "",
                    score=score,
                    metadata={"distance": distance},
                )
            )
        return retrieved

    def clear(self) -> None:
        if self._client is None:
            return
        try:
            self._client.delete_collection(self.config.collection_name)
        except Exception:
            pass
        self._collection = None


def get_vector_store(config_path: str | None = None) -> PolicyVectorStore:
    config = load_rag_config(config_path)
    cache_key = f"{config.persist_directory}:{config.collection_name}"
    if cache_key not in _store_cache:
        _store_cache[cache_key] = PolicyVectorStore(config)
    return _store_cache[cache_key]
