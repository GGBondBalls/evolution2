from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ntmemevo.envs.base import AgentEnv
from ntmemevo.types import Task, ToolResult


class TinyToolsEnv(AgentEnv):
    def __init__(self, split_file: Path) -> None:
        self.split_file = split_file
        self.orders = {
            "ORD-1001": {"status": "delivered", "delivered_days_ago": 3},
            "ORD-1002": {"status": "cancelled", "refundable": False},
            "ORD-1003": {"status": "delivered", "delivered_days_ago": 6},
        }
        self.inventory = {
            "SKU-RED-M": {"status": "in_stock", "quantity": 12},
            "SKU-BLUE-S": {"status": "in_stock", "quantity": 4},
        }
        self.policies = {
            "return_window": "Delivered retail orders can be returned within 30 days.",
        }

    def load_tasks(self, max_tasks: int | None = None) -> list[Task]:
        if not self.split_file.exists():
            raise FileNotFoundError(f"Tiny split file not found: {self.split_file}")
        data = json.loads(self.split_file.read_text(encoding="utf-8"))
        tasks = [
            Task(
                task_id=item["task_id"],
                instruction=item["instruction"],
                expected_answer_contains=tuple(item.get("expected_answer_contains", [])),
                metadata={key: value for key, value in item.items() if key not in {"task_id", "instruction"}},
            )
            for item in data
        ]
        return tasks[:max_tasks] if max_tasks else tasks

    def tool_descriptions(self) -> str:
        return "\n".join(
            [
                "get_order_status(order_id: str) -> order status and refund information",
                "check_inventory(sku: str) -> stock status",
                "check_exchange_eligibility(order_id: str, replacement_sku: str) -> exchange eligibility",
                "lookup_policy(policy_name: str) -> policy text",
            ]
        )

    def call_tool(self, tool_name: str, args: dict[str, Any]) -> ToolResult:
        if tool_name == "get_order_status":
            order_id = str(args.get("order_id", ""))
            order = self.orders.get(order_id)
            if not order:
                return ToolResult(tool_name, args, f"Order {order_id} was not found.", ok=False)
            if order.get("status") == "cancelled" and not order.get("refundable", True):
                observation = f"Order {order_id} is cancelled and not refundable."
            else:
                observation = f"Order {order_id} status is {order['status']}."
            return ToolResult(tool_name, args, observation)

        if tool_name == "check_inventory":
            sku = str(args.get("sku", ""))
            item = self.inventory.get(sku)
            if not item:
                return ToolResult(tool_name, args, f"SKU {sku} was not found.", ok=False)
            return ToolResult(tool_name, args, f"SKU {sku} is {item['status']} with quantity {item['quantity']}.")

        if tool_name == "check_exchange_eligibility":
            order_id = str(args.get("order_id", ""))
            replacement_sku = str(args.get("replacement_sku", ""))
            order = self.orders.get(order_id)
            item = self.inventory.get(replacement_sku)
            if order and item and order["status"] == "delivered" and item["status"] == "in_stock":
                return ToolResult(
                    tool_name,
                    args,
                    f"Order {order_id} is exchange eligible with replacement {replacement_sku}.",
                )
            return ToolResult(tool_name, args, f"Order {order_id} is not exchange eligible.", ok=False)

        if tool_name == "lookup_policy":
            policy_name = str(args.get("policy_name", ""))
            policy = self.policies.get(policy_name)
            if not policy:
                return ToolResult(tool_name, args, f"Policy {policy_name} was not found.", ok=False)
            return ToolResult(tool_name, args, policy)

        return ToolResult(tool_name, args, f"Unknown tool: {tool_name}", ok=False)

    def evaluate(self, task: Task, final_answer: str) -> tuple[bool, float, str | None]:
        answer = final_answer.lower()
        expected = [part.lower() for part in task.expected_answer_contains]
        success = all(part in answer for part in expected)
        return success, 1.0 if success else 0.0, None if success else "expected_answer_mismatch"
