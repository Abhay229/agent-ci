"""Load RAG configuration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT_RAG_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "rag.json"


@dataclass
class RAGConfig:
    document_name: str
    collection_name: str
    persist_directory: str
    top_k: int = 3
    chunk_size: int = 300
    chunk_overlap: int = 0

    @classmethod
    def from_dict(cls, data: dict) -> RAGConfig:
        return cls(
            document_name=data.get("document_name", "company_policy"),
            collection_name=data.get("collection_name", "company_policy"),
            persist_directory=data.get("persist_directory", "chroma"),
            top_k=int(data.get("top_k", 3)),
            chunk_size=int(data.get("chunk_size", 300)),
            chunk_overlap=int(data.get("chunk_overlap", 0)),
        )


def load_rag_config(config_path: str | Path | None = None) -> RAGConfig:
    path = Path(config_path) if config_path else DEFAULT_RAG_CONFIG_PATH
    with open(path, encoding="utf-8") as f:
        return RAGConfig.from_dict(json.load(f))
