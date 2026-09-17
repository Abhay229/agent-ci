"""Store AI-generated tests separately from the trusted benchmark."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent_ci.testgen.types import GeneratedTestBatch

DEFAULT_GENERATED_DIR = Path(__file__).resolve().parent.parent.parent / "generated_tests"
DEFAULT_PENDING_PATH = DEFAULT_GENERATED_DIR / "pending.jsonl"
DEFAULT_APPROVED_PATH = DEFAULT_GENERATED_DIR / "approved.jsonl"
DEFAULT_REJECTED_PATH = DEFAULT_GENERATED_DIR / "rejected.jsonl"


class GeneratedTestStore:
    """JSONL storage for AI-generated test batches awaiting human review."""

    def __init__(
        self,
        pending_path: Path | str | None = None,
        approved_path: Path | str | None = None,
        rejected_path: Path | str | None = None,
    ):
        self.pending_path = Path(pending_path or DEFAULT_PENDING_PATH)
        self.approved_path = Path(approved_path or DEFAULT_APPROVED_PATH)
        self.rejected_path = Path(rejected_path or DEFAULT_REJECTED_PATH)

    def _read_jsonl(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        records: list[dict[str, Any]] = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def _append_jsonl(self, path: Path, record: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def save_batch(self, batch: GeneratedTestBatch) -> GeneratedTestBatch:
        if batch.success and batch.tests:
            self._append_jsonl(self.pending_path, batch.to_dict())
        return batch

    def save_batches(self, batches: list[GeneratedTestBatch]) -> int:
        saved = 0
        for batch in batches:
            if batch.success and batch.tests:
                self.save_batch(batch)
                saved += 1
        return saved

    def list_pending(self) -> list[dict[str, Any]]:
        pending = self._read_jsonl(self.pending_path)
        approved_ids = {r["generation_id"] for r in self._read_jsonl(self.approved_path)}
        rejected_ids = {r["generation_id"] for r in self._read_jsonl(self.rejected_path)}
        return [
            batch for batch in pending
            if batch.get("generation_id") not in approved_ids
            and batch.get("generation_id") not in rejected_ids
            and batch.get("review_status") == "pending"
        ]

    def list_approved(self) -> list[dict[str, Any]]:
        return self._read_jsonl(self.approved_path)

    def get_batch(self, generation_id: str) -> dict[str, Any] | None:
        for path in (self.pending_path, self.approved_path, self.rejected_path):
            for batch in self._read_jsonl(path):
                if batch.get("generation_id") == generation_id:
                    return batch
        return None

    def approve(self, generation_id: str, *, reviewer_note: str = "") -> dict[str, Any] | None:
        batch = self.get_batch(generation_id)
        if batch is None:
            return None
        approved = dict(batch)
        approved["review_status"] = "approved"
        approved["reviewed_at"] = datetime.now(timezone.utc).isoformat()
        approved["reviewer_note"] = reviewer_note
        approved["disclaimer"] = batch.get("disclaimer", "AI-generated — requires human review")
        self._append_jsonl(self.approved_path, approved)
        return approved

    def reject(self, generation_id: str, *, reviewer_note: str = "") -> dict[str, Any] | None:
        batch = self.get_batch(generation_id)
        if batch is None:
            return None
        rejected = dict(batch)
        rejected["review_status"] = "rejected"
        rejected["reviewed_at"] = datetime.now(timezone.utc).isoformat()
        rejected["reviewer_note"] = reviewer_note
        self._append_jsonl(self.rejected_path, rejected)
        return rejected


def get_generated_test_store(
    pending_path: Path | str | None = None,
) -> GeneratedTestStore:
    return GeneratedTestStore(pending_path=pending_path)
