"""Tests for conversation utilities."""

from __future__ import annotations

import unittest

from agent_ci.conversation import (
    TEST_TYPE_MULTI,
    TEST_TYPE_SINGLE,
    build_provider_messages,
    build_transcript,
    format_conversation_for_judge,
    get_conversation,
    get_display_user_message,
    get_primary_user_message,
    get_test_type,
)
from agent_ci.dataset import MULTI_TURN_TEST_CASES, SINGLE_TURN_TEST_CASES


class TestConversationUtilities(unittest.TestCase):
    def test_single_turn_type(self):
        tc = SINGLE_TURN_TEST_CASES[0]
        self.assertEqual(get_test_type(tc), TEST_TYPE_SINGLE)

    def test_multi_turn_type(self):
        tc = MULTI_TURN_TEST_CASES[0]
        self.assertEqual(get_test_type(tc), TEST_TYPE_MULTI)

    def test_single_turn_conversation(self):
        tc = SINGLE_TURN_TEST_CASES[0]
        conv = get_conversation(tc)
        self.assertEqual(len(conv), 1)
        self.assertEqual(conv[0]["role"], "user")
        self.assertEqual(conv[0]["content"], tc["user_message"])

    def test_multi_turn_conversation(self):
        tc = MULTI_TURN_TEST_CASES[0]
        conv = get_conversation(tc)
        self.assertEqual(len(conv), 3)
        self.assertEqual(conv[-1]["role"], "user")
        self.assertEqual(conv[-1]["content"], "Two months ago.")

    def test_primary_user_message_multi_turn(self):
        tc = MULTI_TURN_TEST_CASES[0]
        self.assertEqual(get_primary_user_message(tc), "Two months ago.")

    def test_display_user_message_multi_turn(self):
        tc = MULTI_TURN_TEST_CASES[0]
        display = get_display_user_message(tc)
        self.assertIn("User: I want a refund.", display)
        self.assertIn("Assistant:", display)

    def test_build_transcript(self):
        conv = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
            {"role": "user", "content": "Need help"},
        ]
        transcript = build_transcript(conv, "Sure, I can help.")
        self.assertEqual(len(transcript), 4)
        self.assertEqual(transcript[-1]["role"], "assistant")
        self.assertEqual(transcript[-1]["content"], "Sure, I can help.")

    def test_build_provider_messages(self):
        conv = get_conversation(MULTI_TURN_TEST_CASES[0])
        messages = build_provider_messages(conv)
        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(messages[-1]["role"], "user")

    def test_format_conversation_for_judge(self):
        tc = MULTI_TURN_TEST_CASES[0]
        formatted = format_conversation_for_judge(tc, final_response="No full refund available.")
        self.assertIn("Customer: I want a refund.", formatted)
        self.assertIn("Agent: No full refund available.", formatted)

    def test_multi_turn_must_end_with_user(self):
        bad = {
            "id": "bad",
            "conversation": [
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": "Hello"},
            ],
        }
        with self.assertRaises(ValueError):
            get_conversation(bad)


if __name__ == "__main__":
    unittest.main()
