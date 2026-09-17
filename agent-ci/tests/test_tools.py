"""Tests for the tool execution architecture."""

from __future__ import annotations

import unittest

from agent_ci.tools.executor import ToolExecutor
from agent_ci.tools.mock_tools import CancelSubscriptionTool, ProcessRefundTool
from agent_ci.tools.registry import ToolRegistry
from agent_ci.tools.types import STATUS_FAILED, STATUS_SUCCESS


class TestToolRegistry(unittest.TestCase):
    def test_default_tools_registered(self):
        registry = ToolRegistry()
        self.assertIn("cancel_subscription", registry.list_tools())
        self.assertIn("refund_customer", registry.list_tools())
        self.assertIn("process_refund", registry.list_tools())

    def test_custom_tool_registration(self):
        registry = ToolRegistry(tools=[])
        tool = CancelSubscriptionTool()
        registry.register(tool)
        self.assertTrue(registry.has("cancel_subscription"))


class TestToolExecutor(unittest.TestCase):
    def setUp(self):
        self.executor = ToolExecutor()

    def test_execute_cancel_subscription(self):
        record = self.executor.execute("cancel_subscription", {"at_period_end": True})
        self.assertEqual(record.tool, "cancel_subscription")
        self.assertEqual(record.status, STATUS_SUCCESS)
        self.assertTrue(record.result["at_period_end"])

    def test_execute_unknown_tool(self):
        record = self.executor.execute("unknown_tool", {})
        self.assertEqual(record.status, STATUS_FAILED)

    def test_process_refund_ineligible(self):
        record = self.executor.execute("process_refund", {"days_since_purchase": 30})
        self.assertEqual(record.status, STATUS_FAILED)

    def test_process_refund_eligible(self):
        record = self.executor.execute("process_refund", {"days_since_purchase": 1})
        self.assertEqual(record.status, STATUS_SUCCESS)
        self.assertTrue(record.result["eligible"])

    def test_execute_many(self):
        records = self.executor.execute_many([
            {"tool": "cancel_subscription", "arguments": {"at_period_end": True}},
            {"tool": "export_user_data", "arguments": {"format": "csv"}},
        ])
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].status, STATUS_SUCCESS)
        self.assertEqual(records[1].status, STATUS_SUCCESS)


class TestMockToolClasses(unittest.TestCase):
    def test_cancel_subscription_tool(self):
        result = CancelSubscriptionTool().execute({"at_period_end": True})
        self.assertTrue(result.success)

    def test_process_refund_tool(self):
        result = ProcessRefundTool().execute({"days_since_purchase": 2})
        self.assertTrue(result.success)


if __name__ == "__main__":
    unittest.main()
