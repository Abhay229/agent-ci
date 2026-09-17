"""Ingest the company policy into the local ChromaDB vector store."""

from agent_ci.rag.ingest import ingest_policy

if __name__ == "__main__":
    count = ingest_policy(reset=True)
    print(f"Ingested {count} policy chunks into ChromaDB.")
