"""Deterministic mock tools for offline demonstrations."""

from __future__ import annotations

from typing import Any

from agent_ci.tools.base import BaseTool
from agent_ci.tools.types import ToolResult


class CancelSubscriptionTool(BaseTool):
    name = "cancel_subscription"
    description = "Cancel the customer's subscription at period end."

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        at_period_end = arguments.get("at_period_end", True)
        return ToolResult(
            success=True,
            data={
                "action": "cancel_subscription",
                "at_period_end": bool(at_period_end),
                "message": "Subscription cancellation scheduled.",
            },
        )


class RefundCustomerTool(BaseTool):
    name = "refund_customer"
    description = "Issue a refund to the customer."

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        return ToolResult(
            success=True,
            data={
                "action": "refund_customer",
                "amount": arguments.get("amount"),
                "message": "Refund initiated.",
            },
        )


class ProcessRefundTool(BaseTool):
    name = "process_refund"
    description = "Process an eligible refund within the 14-day window."

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        days_since_purchase = arguments.get("days_since_purchase")
        if days_since_purchase is not None and int(days_since_purchase) > 14:
            return ToolResult(
                success=False,
                error="Refund not eligible after 14 days.",
                data={"eligible": False},
            )
        return ToolResult(
            success=True,
            data={
                "action": "process_refund",
                "eligible": True,
                "message": "Full refund processed.",
            },
        )


class ExportUserDataTool(BaseTool):
    name = "export_user_data"
    description = "Export customer data in CSV or JSON format."

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        export_format = str(arguments.get("format", "csv")).lower()
        if export_format not in {"csv", "json"}:
            return ToolResult(success=False, error=f"Unsupported export format: {export_format}")
        return ToolResult(
            success=True,
            data={
                "action": "export_user_data",
                "format": export_format,
                "message": f"Export started in {export_format.upper()} format.",
            },
        )


DEFAULT_MOCK_TOOLS: list[BaseTool] = [
    CancelSubscriptionTool(),
    RefundCustomerTool(),
    ProcessRefundTool(),
    ExportUserDataTool(),
]
