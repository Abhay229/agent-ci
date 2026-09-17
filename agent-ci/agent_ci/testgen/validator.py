"""Validate AI-generated test case structure before saving."""

from __future__ import annotations

import re
from typing import Any

from agent_ci.testgen.types import AI_TEST_DISCLAIMER

REQUIRED_FIELDS = ("id", "category", "user_message", "judge_rubric")
ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]{2,63}$")


class TestValidationError(ValueError):
    """Raised when a generated test fails structural validation."""


def _as_string_list(value: Any, field_name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise TestValidationError(f"{field_name} must be a list of strings.")
    result = []
    for item in value:
        if not isinstance(item, str):
            raise TestValidationError(f"{field_name} must contain only strings.")
        result.append(item.strip())
    return result


def validate_generated_test(raw: dict[str, Any], *, source_test_id: str = "") -> dict[str, Any]:
    """Validate and normalize one generated test case.

    Raises TestValidationError when the structure is invalid.
    """
    if not isinstance(raw, dict):
        raise TestValidationError("Test case must be a JSON object.")

    for field in REQUIRED_FIELDS:
        if field not in raw:
            raise TestValidationError(f"Missing required field: {field}")

    test_id = str(raw["id"]).strip()
    if not ID_PATTERN.match(test_id):
        raise TestValidationError(
            f"Invalid id {test_id!r}. Use lowercase letters, numbers, underscores; "
            "must start with a letter."
        )
    if not test_id.startswith("ai_gen_"):
        test_id = f"ai_gen_{test_id.removeprefix('ai_gen_')}"

    category = str(raw["category"]).strip()
    user_message = str(raw["user_message"]).strip()
    judge_rubric = str(raw["judge_rubric"]).strip()

    if not category:
        raise TestValidationError("category must be non-empty.")
    if len(user_message) < 5:
        raise TestValidationError("user_message is too short.")
    if not judge_rubric:
        raise TestValidationError("judge_rubric must be non-empty.")

    return {
        "id": test_id,
        "category": category,
        "user_message": user_message,
        "judge_rubric": judge_rubric,
        "must_include": _as_string_list(raw.get("must_include"), "must_include"),
        "must_not_include": _as_string_list(raw.get("must_not_include"), "must_not_include"),
        "source_test_id": source_test_id or str(raw.get("source_test_id") or ""),
        "disclaimer": AI_TEST_DISCLAIMER,
        "ai_generated": True,
        "trusted": False,
        "review_status": "pending",
    }


def validate_generated_tests(
    raw_tests: list[Any],
    *,
    source_test_id: str = "",
) -> tuple[list[dict[str, Any]], list[str]]:
    """Validate a list of generated tests, returning valid tests and error messages."""
    valid: list[dict[str, Any]] = []
    errors: list[str] = []

    seen_ids: set[str] = set()
    for index, raw in enumerate(raw_tests):
        try:
            normalized = validate_generated_test(raw, source_test_id=source_test_id)
            if normalized["id"] in seen_ids:
                raise TestValidationError(f"Duplicate id {normalized['id']!r}.")
            seen_ids.add(normalized["id"])
            valid.append(normalized)
        except TestValidationError as exc:
            errors.append(f"test[{index}]: {exc}")

    return valid, errors
