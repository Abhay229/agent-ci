"""Utilities for single-turn and multi-turn test cases."""

from __future__ import annotations

TEST_TYPE_SINGLE = "single_turn"
TEST_TYPE_MULTI = "multi_turn"

VALID_ROLES = frozenset({"user", "assistant"})


def get_test_type(test_case: dict) -> str:
    """Return ``single_turn`` or ``multi_turn`` for a test case."""
    if test_case.get("test_type") == TEST_TYPE_MULTI:
        return TEST_TYPE_MULTI
    if test_case.get("conversation"):
        return TEST_TYPE_MULTI
    return TEST_TYPE_SINGLE


def get_conversation(test_case: dict) -> list[dict[str, str]]:
    """Return normalized conversation turns for a test case."""
    if test_case.get("conversation"):
        turns: list[dict[str, str]] = []
        for index, turn in enumerate(test_case["conversation"]):
            role = turn.get("role")
            content = turn.get("content")
            if role not in VALID_ROLES:
                raise ValueError(
                    f"Invalid role {role!r} in conversation for test {test_case.get('id')!r}"
                )
            if not isinstance(content, str) or not content.strip():
                raise ValueError(
                    f"Empty content in conversation turn {index} for test {test_case.get('id')!r}"
                )
            turns.append({"role": role, "content": content.strip()})
        if not turns or turns[-1]["role"] != "user":
            raise ValueError(
                f"Multi-turn test {test_case.get('id')!r} must end with a user message."
            )
        return turns

    user_message = test_case.get("user_message")
    if not user_message:
        raise ValueError(f"Test case {test_case.get('id')!r} has no user_message or conversation.")
    return [{"role": "user", "content": user_message.strip()}]


def get_primary_user_message(test_case: dict) -> str:
    """Return the latest user message — used for RAG retrieval and legacy fields."""
    for turn in reversed(get_conversation(test_case)):
        if turn["role"] == "user":
            return turn["content"]
    return str(test_case.get("user_message", ""))


def get_display_user_message(test_case: dict) -> str:
    """Human-readable user input for reports and dashboards."""
    if get_test_type(test_case) == TEST_TYPE_SINGLE:
        return get_primary_user_message(test_case)

    lines = []
    for turn in get_conversation(test_case):
        label = "User" if turn["role"] == "user" else "Assistant"
        lines.append(f"{label}: {turn['content']}")
    return "\n".join(lines)


def format_conversation_for_judge(test_case: dict, final_response: str | None = None) -> str:
    """Format the full conversation transcript for LLM judges."""
    lines = []
    for turn in get_conversation(test_case):
        label = "Customer" if turn["role"] == "user" else "Agent"
        lines.append(f"{label}: {turn['content']}")
    if final_response:
        lines.append(f"Agent: {final_response}")
    return "\n".join(lines)


def build_provider_messages(conversation: list[dict[str, str]]) -> list[dict[str, str]]:
    """Build chat messages for the provider from prior turns.

    The last user message is included — the model generates the assistant reply
    that follows it.
    """
    return [{"role": turn["role"], "content": turn["content"]} for turn in conversation]


def build_transcript(
    conversation: list[dict[str, str]],
    final_response: str,
) -> list[dict[str, str]]:
    """Return the full transcript including the generated assistant response."""
    transcript = [{"role": turn["role"], "content": turn["content"]} for turn in conversation]
    transcript.append({"role": "assistant", "content": final_response})
    return transcript
