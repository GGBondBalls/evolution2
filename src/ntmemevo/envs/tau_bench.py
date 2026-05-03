from __future__ import annotations

import ast
import copy
import importlib
import json
import operator
from pathlib import Path
from typing import Any

from ntmemevo.envs.base import AgentEnv
from ntmemevo.types import Task, ToolResult


class TauBenchEnv(AgentEnv):
    """Minimal tau-bench retail adapter.

    The adapter intentionally avoids a hard dependency on tau-bench. It can run an
    offline smoke split from local JSON/JSONL/Python files, and it can also read the
    installed tau-bench package when it is available.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.domain = str(config.get("domain", "retail")).lower()
        if self.domain != "retail":
            raise ValueError(
                f"TauBenchEnv currently supports only benchmark.domain=retail, got {self.domain!r}."
            )
        self.evaluation = str(config.get("evaluation", "auto")).lower()
        self.compare_action_args = bool(config.get("compare_action_args", False))
        self.strict_action_args = bool(config.get("strict_action_args", False))
        self._tool_history: list[dict[str, Any]] = []
        self._last_evaluation_detail: dict[str, Any] = {}
        self._task_initial_db: dict[str, Any] | None = None
        self.initial_db = self._load_retail_db()
        self.db = copy.deepcopy(self.initial_db)

    @property
    def last_evaluation_detail(self) -> dict[str, Any]:
        return dict(self._last_evaluation_detail)

    def start_task(self, task: Task) -> None:
        self.db = copy.deepcopy(self.initial_db)
        self._task_initial_db = copy.deepcopy(self.db)
        self._tool_history = []
        self._last_evaluation_detail = {
            "task_id": task.task_id,
            "evaluation_requested": self.evaluation,
            "evaluation_mode": None,
            "state_diff_passed": None,
            "expected_actions_matched": None,
            "policy_violation_count": 0,
            "tool_semantic_error_count": 0,
        }

    def load_tasks(self, max_tasks: int | None = None) -> list[Task]:
        records = self._load_task_records()
        tasks = [self._task_from_record(record, index) for index, record in enumerate(records, start=1)]
        return tasks[:max_tasks] if max_tasks else tasks

    def tool_descriptions(self) -> str:
        return "\n".join(
            [
                "find_user_id_by_name_zip(first_name: str, last_name: str, zip: str) -> matching user id",
                "find_user_id_by_email(email: str) -> matching user id",
                "get_user_details(user_id: str) -> customer profile, addresses, and order ids",
                "get_order_details(order_id: str) -> order status, items, payment, and shipping details",
                "get_product_details(product_id: str) -> product name, type, price, and variants",
                "get_item_details(item_id: str) -> inventory variant details for a concrete item id",
                "list_all_product_types() -> available product type names",
                "lookup_policy(policy_name: str) -> retail policy text",
                "calculate(expression: str) -> arithmetic result",
                "think(thought: str) -> private reasoning note",
                "transfer_to_human_agents(summary: str) -> escalate to a human support agent",
                "modify_user_address(user_id: str, address1: str, address2: str, city: str, state: str, country: str, zip: str) -> update a user's default address",
                "modify_pending_order_address(order_id: str, address: dict) -> update pending order shipping address",
                "modify_pending_order_payment(order_id: str, payment_method_id: str) -> update pending order payment method",
                "modify_pending_order_items(order_id: str, item_ids: list[str], new_item_ids: list[str], payment_method_id: str) -> update pending order items",
                "cancel_pending_order(order_id: str, reason: str) -> cancel a pending order",
                "return_delivered_order_items(order_id: str, item_ids: list[str], payment_method_id: str) -> return delivered order items",
                "exchange_delivered_order_items(order_id: str, item_ids: list[str], new_item_ids: list[str], payment_method_id: str) -> exchange delivered order items",
            ]
        )

    def call_tool(self, tool_name: str, args: dict[str, Any]) -> ToolResult:
        if not isinstance(args, dict):
            args = {}
        tool_name = str(tool_name)
        result: ToolResult
        if tool_name == "find_user_id_by_name_zip":
            result = self._find_user_id_by_name_zip(args)
        elif tool_name == "find_user_id_by_email":
            result = self._find_user_id_by_email(args)
        elif tool_name == "get_user_details":
            result = self._get_user_details(args)
        elif tool_name == "get_order_details":
            result = self._get_order_details(args)
        elif tool_name == "get_product_details":
            result = self._get_product_details(args)
        elif tool_name == "get_item_details":
            result = self._get_item_details(args)
        elif tool_name == "list_all_product_types":
            result = self._list_all_product_types(args)
        elif tool_name == "lookup_policy":
            result = self._lookup_policy(args)
        elif tool_name == "calculate":
            result = self._calculate(args)
        elif tool_name == "think":
            result = ToolResult(tool_name, args, f"Noted: {args.get('thought', '')}")
        elif tool_name == "transfer_to_human_agents":
            result = ToolResult(
                tool_name,
                args,
                f"Transferred to human agents: {args.get('summary', '')}",
            )
        elif tool_name == "modify_user_address":
            result = self._modify_user_address(args)
        elif tool_name == "modify_pending_order_address":
            result = self._modify_order(
                tool_name=tool_name,
                order_status="pending",
                field="shipping_address",
                args=args,
            )
        elif tool_name == "modify_pending_order_payment":
            result = self._modify_order(
                tool_name=tool_name,
                order_status="pending",
                field="payment_method_id",
                args=args,
            )
        elif tool_name == "modify_pending_order_items":
            result = self._modify_order(
                tool_name=tool_name,
                order_status="pending",
                field="items",
                args=args,
            )
        elif tool_name == "cancel_pending_order":
            result = self._cancel_pending_order(args)
        elif tool_name == "return_delivered_order_items":
            result = self._return_delivered_order_items(args)
        elif tool_name == "exchange_delivered_order_items":
            result = self._exchange_delivered_order_items(args)
        else:
            result = ToolResult(tool_name, args, f"Unknown tau-bench retail tool: {tool_name}", ok=False)

        self._tool_history.append(
            {
                "tool_name": result.tool_name,
                "args": dict(args),
                "ok": result.ok,
                "observation": result.observation,
            }
        )
        return result

    def _cancel_pending_order(self, args: dict[str, Any]) -> ToolResult:
        order_id = str(args.get("order_id") or "")
        result = self._set_order_status(
            tool_name="cancel_pending_order",
            args=args,
            required_status="pending",
            new_status="cancelled",
        )
        if result.ok:
            order = self._get_order_record(order_id)
            if order is not None:
                order["cancel_reason"] = str(args.get("reason") or "customer_request")
        return result

    def _return_delivered_order_items(self, args: dict[str, Any]) -> ToolResult:
        order_id = str(args.get("order_id") or "")
        item_ids = self._normalize_id_list(args.get("item_ids") or args.get("items") or args.get("item_id"))
        order = self._get_order_record(order_id)
        if not order:
            return ToolResult(
                "return_delivered_order_items",
                args,
                f"Order {self._clean_order_id(order_id)} was not found.",
                ok=False,
            )
        current_status = str(order.get("status", "")).lower()
        if current_status != "delivered":
            return ToolResult(
                "return_delivered_order_items",
                args,
                f"Order {self._clean_order_id(order_id)} is {current_status} and cannot return delivered items.",
                ok=False,
            )
        missing = self._missing_item_ids(order, item_ids)
        if missing:
            return ToolResult(
                "return_delivered_order_items",
                args,
                f"Order {self._clean_order_id(order_id)} does not contain item ids: {', '.join(missing)}.",
                ok=False,
            )
        order["status"] = "return_requested"
        order["return_item_ids"] = item_ids
        if args.get("payment_method_id"):
            order["return_payment_method_id"] = str(args["payment_method_id"])
        self._mark_order_items(order, item_ids, "return_requested")
        return ToolResult(
            "return_delivered_order_items",
            args,
            f"Order {self._clean_order_id(order_id)} return requested for item_ids={item_ids}.",
        )

    def _exchange_delivered_order_items(self, args: dict[str, Any]) -> ToolResult:
        order_id = str(args.get("order_id") or "")
        item_ids = self._normalize_id_list(args.get("item_ids") or args.get("items") or args.get("item_id"))
        product_ids = self._normalize_id_list(
            args.get("new_item_ids")
            or args.get("product_ids")
            or args.get("replacement_product_ids")
            or args.get("product_id")
        )
        order = self._get_order_record(order_id)
        if not order:
            return ToolResult(
                "exchange_delivered_order_items",
                args,
                f"Order {self._clean_order_id(order_id)} was not found.",
                ok=False,
            )
        current_status = str(order.get("status", "")).lower()
        if current_status != "delivered":
            return ToolResult(
                "exchange_delivered_order_items",
                args,
                f"Order {self._clean_order_id(order_id)} is {current_status} and cannot exchange delivered items.",
                ok=False,
            )
        missing_items = self._missing_item_ids(order, item_ids)
        if missing_items:
            return ToolResult(
                "exchange_delivered_order_items",
                args,
                f"Order {self._clean_order_id(order_id)} does not contain item ids: {', '.join(missing_items)}.",
                ok=False,
            )
        missing_products = [
            product_id
            for product_id in product_ids
            if product_id not in self.db["products"] and self._find_item_variant(product_id) is None
        ]
        if missing_products:
            return ToolResult(
                "exchange_delivered_order_items",
                args,
                f"Products were not found for exchange: {', '.join(missing_products)}.",
                ok=False,
            )
        order["status"] = "exchange_requested"
        order["exchange_item_ids"] = item_ids
        order["exchange_product_ids"] = product_ids
        order["exchange_new_item_ids"] = product_ids
        if args.get("payment_method_id"):
            order["exchange_payment_method_id"] = str(args["payment_method_id"])
        self._mark_order_items(order, item_ids, "exchange_requested")
        return ToolResult(
            "exchange_delivered_order_items",
            args,
            (
                f"Order {self._clean_order_id(order_id)} exchange requested for "
                f"item_ids={item_ids}; product_ids={product_ids}."
            ),
        )

    def evaluate(self, task: Task, final_answer: str) -> tuple[bool, float, str | None]:
        try:
            success, error_type = self._evaluate_task(task, final_answer)
            return success, 1.0 if success else 0.0, error_type
        finally:
            self._tool_history = []

    def _load_task_records(self) -> list[dict[str, Any]]:
        split_file = self.config.get("split_file") or self.config.get("tasks_file")
        if split_file:
            records = self._load_task_records_from_path(Path(str(split_file)))
            records = self._filter_task_records(records, source=str(split_file))
            self._validate_task_records_if_requested(records, source=str(split_file))
            return records

        task_module = self.config.get("task_module")
        if task_module:
            records = self._load_task_records_from_module(str(task_module))
            records = self._filter_task_records(records, source=str(task_module))
            self._validate_task_records_if_requested(records, source=str(task_module))
            return records

        task_split = str(self.config.get("task_split", "train")).lower()
        module_names = [
            f"tau_bench.envs.retail.tasks_{task_split}",
            "tau_bench.envs.retail.tasks",
        ]
        last_error: Exception | None = None
        for module_name in module_names:
            try:
                records = self._load_task_records_from_module(module_name)
                records = self._filter_task_records(records, source=module_name)
                self._validate_task_records_if_requested(records, source=module_name)
                return records
            except (ImportError, AttributeError, ValueError) as exc:
                last_error = exc

        message = (
            "Tau-bench retail tasks are not configured. Set benchmark.split_file to a local "
            "JSON/JSONL/Python task file, set benchmark.task_module to an installed module, "
            "or install tau-bench and set benchmark.task_split. Example local smoke config: "
            "configs/tau_retail_nomem.yaml."
        )
        if last_error is not None:
            message += f" Last import error: {last_error}"
        raise FileNotFoundError(message)

    def _load_task_records_from_path(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            raise FileNotFoundError(
                "Tau-bench retail task file not found: "
                f"{path}. Set benchmark.split_file to a local tau-bench task JSON/JSONL/Python file "
                "or install tau-bench and use benchmark.task_split."
            )
        suffix = path.suffix.lower()
        if suffix == ".jsonl":
            records = [
                json.loads(line)
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            return self._ensure_record_list(records, source=str(path))
        if suffix == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            return self._records_from_loaded_object(data, source=str(path))
        if suffix == ".py":
            data = self._literal_task_object_from_python(path)
            return self._records_from_loaded_object(data, source=str(path))
        raise ValueError(
            f"Unsupported tau-bench task file suffix {suffix!r} for {path}. "
            "Supported suffixes: .json, .jsonl, .py."
        )

    def _load_task_records_from_module(self, module_name: str) -> list[dict[str, Any]]:
        module = importlib.import_module(module_name)
        for attr in ("TASKS", "tasks", "TASKS_TRAIN", "TASKS_TEST", "TASKS_DEV"):
            if hasattr(module, attr):
                return self._records_from_loaded_object(getattr(module, attr), source=module_name)
        raise AttributeError(
            f"Module {module_name!r} does not expose TASKS, tasks, TASKS_TRAIN, TASKS_TEST, or TASKS_DEV."
        )

    def _records_from_loaded_object(self, data: Any, source: str) -> list[dict[str, Any]]:
        if isinstance(data, dict):
            tasks_key = self.config.get("tasks_key")
            keys = [str(tasks_key)] if tasks_key else ["tasks", "TASKS", "train", "test", "dev", "items"]
            for key in keys:
                if key in data:
                    return self._ensure_record_list(data[key], source=source)
        return self._ensure_record_list(data, source=source)

    def _ensure_record_list(self, records: Any, source: str) -> list[dict[str, Any]]:
        if not isinstance(records, list):
            raise ValueError(f"Tau-bench task data in {source} must be a list of records.")
        normalized = []
        for index, record in enumerate(records, start=1):
            if not isinstance(record, dict):
                raise ValueError(f"Task #{index} in {source} is not a mapping.")
            normalized.append(record)
        return normalized

    def _filter_task_records(self, records: list[dict[str, Any]], source: str) -> list[dict[str, Any]]:
        filtered = list(records)
        split_ids = self._configured_task_split_ids()
        if split_ids is not None:
            wanted = set(split_ids)
            filtered = [
                record
                for record in filtered
                if self._record_task_id(record) in wanted
            ]
            if not filtered:
                raise ValueError(
                    f"Tau-bench task split filter selected no records from {source}. "
                    "Check benchmark.task_split_file and benchmark.task_split."
                )

        task_ids = self._configured_task_ids()
        if task_ids is not None:
            wanted = set(task_ids)
            filtered = [
                record
                for record in filtered
                if self._record_task_id(record) in wanted
            ]
            if not filtered:
                raise ValueError(
                    f"Tau-bench task_ids filter selected no records from {source}. "
                    "Check benchmark.task_ids."
                )
        return filtered

    def _configured_task_split_ids(self) -> list[str] | None:
        split_path = self.config.get("task_split_file") or self.config.get("split_ids_file")
        if not split_path:
            return None
        path = Path(str(split_path))
        if not path.exists():
            raise FileNotFoundError(
                f"Tau-bench task split file not found: {path}. "
                "Set benchmark.task_split_file to a split JSON file such as tau2 split_tasks.json."
            )
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"Tau-bench task split file {path} must be a JSON object.")
        split_name = str(self.config.get("task_split", "base"))
        if split_name not in data:
            raise ValueError(
                f"Tau-bench task split {split_name!r} was not found in {path}. "
                f"Available splits: {sorted(data)}."
            )
        ids = data[split_name]
        if not isinstance(ids, list):
            raise ValueError(f"Tau-bench task split {split_name!r} in {path} must be a list.")
        return [str(item) for item in ids]

    def _configured_task_ids(self) -> list[str] | None:
        raw_task_ids = self.config.get("task_ids")
        if raw_task_ids is None:
            return None
        if isinstance(raw_task_ids, str):
            return [part.strip() for part in raw_task_ids.split(",") if part.strip()]
        if isinstance(raw_task_ids, list):
            return [str(item) for item in raw_task_ids]
        raise ValueError("benchmark.task_ids must be a comma-separated string or a list.")

    def _record_task_id(self, record: dict[str, Any]) -> str:
        return str(record.get("task_id") or record.get("id") or record.get("taskId") or "")

    def _validate_task_records_if_requested(
        self,
        records: list[dict[str, Any]],
        source: str,
    ) -> None:
        if not bool(self.config.get("validate_export_schema", False)):
            return
        if not records:
            raise ValueError(
                f"Tau-bench export task file {source} contains no tasks. "
                "Expected at least one task record; see docs/tau_retail_export_schema.md."
            )
        for index, record in enumerate(records, start=1):
            task_id = self._record_task_id(record) or f"#{index}"
            instruction = self._instruction_from_record(record)
            if not isinstance(instruction, str) or not instruction.strip():
                raise ValueError(
                    f"Tau-bench export task {task_id!r} in {source} is missing a non-empty "
                    "instruction/user_instruction/query/message field or tau2 user_scenario.instructions."
                )

            expected = self._expected_answer_from_record(record)
            has_expected_answer = bool(self._normalize_expected_answer(expected))
            raw_actions = self._expected_actions_from_record(record)
            actions = self._normalize_actions(raw_actions)
            has_expected_state_diff = bool(
                self._expected_state_diff_from_record(record)
            )
            has_official_criteria = bool(
                isinstance(record.get("evaluation_criteria"), dict)
                and record["evaluation_criteria"].get("reward_basis") is not None
            )
            if not has_expected_answer and not actions and not has_expected_state_diff and not has_official_criteria:
                raise ValueError(
                    f"Tau-bench export task {task_id!r} in {source} must provide either "
                    "expected_answer_contains/expected_answer, actions/expected_actions, "
                    "expected_state_diff/state_diff/expected_db_state, or tau2 evaluation_criteria."
                )
            if raw_actions not in (None, []) and not actions:
                raise ValueError(
                    f"Tau-bench export task {task_id!r} in {source} has actions/expected_actions "
                    "but no valid action records. Each action needs name/tool_name/action and "
                    "optional args/arguments/kwargs."
                )

    def _literal_task_object_from_python(self, path: Path) -> Any:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        names = {
            str(self.config.get("tasks_variable"))
            if self.config.get("tasks_variable")
            else "tasks",
            "tasks",
            "TASKS",
            "TASKS_TRAIN",
            "TASKS_TEST",
            "TASKS_DEV",
        }
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in names:
                        return ast.literal_eval(node.value)
        raise ValueError(
            f"No literal task assignment found in {path}. Expected one of {sorted(names)}."
        )

    def _task_from_record(self, record: dict[str, Any], index: int) -> Task:
        task_id = self._record_task_id(record) or f"tau_retail_{index:04d}"
        instruction = self._instruction_from_record(record)
        if not instruction:
            raise ValueError(f"Tau-bench task {task_id} does not contain an instruction field.")

        expected = self._expected_answer_from_record(record)
        expected_answer_contains = self._normalize_expected_answer(expected)
        expected_actions = self._normalize_actions(self._expected_actions_from_record(record))
        tool_names = record.get("tool_names") or [action["name"] for action in expected_actions]

        metadata = {
            key: value
            for key, value in record.items()
            if key
            not in {
                "task_id",
                "id",
                "taskId",
                "instruction",
                "user_instruction",
                "query",
                "message",
                "expected_answer_contains",
                "expected_answer",
            }
        }
        expected_state_diff = self._expected_state_diff_from_record(record)
        if expected_state_diff and "expected_state_diff" not in metadata:
            metadata["expected_state_diff"] = expected_state_diff
        if "evaluation_criteria" in record:
            metadata["source_format"] = "tau2_official"
        metadata["benchmark"] = "tau_bench"
        metadata["domain"] = metadata.get("domain", "retail")
        metadata["intent"] = metadata.get("intent") or self._infer_intent(instruction, tool_names)
        metadata["tool_names"] = list(tool_names) if isinstance(tool_names, list) else []
        metadata["expected_actions"] = expected_actions
        default_no_memory_success = False if metadata.get("source_format") == "tau2_official" else True
        metadata["no_memory_success"] = bool(
            metadata.get("no_memory_success", default_no_memory_success)
        )
        return Task(
            task_id=task_id,
            instruction=instruction,
            expected_answer_contains=expected_answer_contains,
            metadata=metadata,
        )

    def _instruction_from_record(self, record: dict[str, Any]) -> str:
        direct = (
            record.get("instruction")
            or record.get("user_instruction")
            or record.get("query")
            or record.get("message")
        )
        if isinstance(direct, str) and direct.strip():
            return " ".join(direct.split())

        instructions = {}
        user_scenario = record.get("user_scenario")
        if isinstance(user_scenario, dict):
            candidate = user_scenario.get("instructions")
            if isinstance(candidate, dict):
                instructions = candidate
        if not instructions:
            return ""

        parts = []
        for key, label in (
            ("task_instructions", "Task style"),
            ("reason_for_call", "Customer request"),
            ("known_info", "Known info"),
            ("unknown_info", "Unknown info"),
        ):
            value = instructions.get(key)
            if isinstance(value, str) and value.strip():
                parts.append(f"{label}: {' '.join(value.split())}")
        return " ".join(parts)

    def _expected_answer_from_record(self, record: dict[str, Any]) -> Any:
        if "expected_answer_contains" in record:
            return record.get("expected_answer_contains")
        return record.get("expected_answer")

    def _expected_actions_from_record(self, record: dict[str, Any]) -> Any:
        actions = record.get("actions")
        if actions is None:
            actions = record.get("expected_actions")
        if actions is not None:
            return actions
        criteria = record.get("evaluation_criteria")
        if isinstance(criteria, dict):
            return criteria.get("actions")
        return None

    def _expected_state_diff_from_record(self, record: dict[str, Any]) -> Any:
        for key in ("expected_state_diff", "state_diff", "expected_db_state"):
            value = record.get(key)
            if value:
                return value
        criteria = record.get("evaluation_criteria")
        if isinstance(criteria, dict):
            for key in ("expected_state_diff", "state_diff", "expected_db_state"):
                value = criteria.get(key)
                if value:
                    return value
        return {}

    def _normalize_expected_answer(self, expected: Any) -> tuple[str, ...]:
        if expected is None:
            return ()
        if isinstance(expected, str):
            return (expected,)
        if isinstance(expected, list):
            return tuple(str(item) for item in expected)
        return (str(expected),)

    def _normalize_actions(self, actions: Any) -> list[dict[str, Any]]:
        if not isinstance(actions, list):
            return []
        normalized: list[dict[str, Any]] = []
        for action in actions:
            if not isinstance(action, dict):
                continue
            name = action.get("name") or action.get("tool_name") or action.get("action")
            if not name:
                continue
            args = action.get("args") or action.get("arguments") or action.get("kwargs") or {}
            optional_args = action.get("optional_args") or action.get("optional_fields") or []
            ignore_args = action.get("ignore_args") or action.get("ignore_fields") or []
            normalized.append(
                {
                    "name": str(name),
                    "args": dict(args) if isinstance(args, dict) else {},
                    "optional_args": list(optional_args) if isinstance(optional_args, list) else [],
                    "ignore_args": list(ignore_args) if isinstance(ignore_args, list) else [],
                }
            )
        return normalized

    def _infer_intent(self, instruction: str, tool_names: Any) -> str:
        tools = " ".join(str(tool) for tool in tool_names or [])
        text = f"{instruction} {tools}".lower()
        if "refund" in text or "return" in text:
            return "refund_or_return"
        if "exchange" in text:
            return "exchange_item"
        if "cancel" in text:
            return "cancel_order"
        if "address" in text or "payment" in text or "modify" in text:
            return "modify_order"
        if "product" in text or "inventory" in text or "item" in text:
            return "product_lookup"
        if "policy" in text:
            return "policy_lookup"
        if "user" in text or "customer" in text or "email" in text:
            return "customer_lookup"
        if "order" in text:
            return "order_lookup"
        return "retail_support"

    def _load_retail_db(self) -> dict[str, Any]:
        data_file = self.config.get("data_file") or self.config.get("db_file")
        if data_file:
            path = Path(str(data_file))
            if not path.exists():
                raise FileNotFoundError(
                    f"Tau-bench retail data_file not found: {path}. "
                    "Set benchmark.data_file to a local retail DB JSON file."
                )
            return self._normalize_db(
                json.loads(path.read_text(encoding="utf-8")),
                source=str(path),
            )

        data_dir = self.config.get("data_dir")
        if data_dir:
            return self._load_db_from_dir(Path(str(data_dir)))

        external = self._load_external_tau_bench_data()
        if external is not None:
            return self._normalize_db(external, source="tau_bench.envs.retail.data.load_data()")

        if bool(self.config.get("require_data", False)):
            raise FileNotFoundError(
                "Tau-bench retail data is not configured. Set benchmark.data_file or "
                "benchmark.data_dir, or install tau-bench so tau_bench.envs.retail.data.load_data() "
                "is available."
            )
        return self._normalize_db({}, source="empty_default")

    def _load_db_from_dir(self, data_dir: Path) -> dict[str, Any]:
        if not data_dir.exists():
            raise FileNotFoundError(f"Tau-bench retail data_dir not found: {data_dir}")
        for filename in ("db.json", "data.json", "retail.json", "retail_db.json"):
            path = data_dir / filename
            if path.exists():
                return self._normalize_db(
                    json.loads(path.read_text(encoding="utf-8")),
                    source=str(path),
                )

        merged: dict[str, Any] = {}
        for key, filename in {
            "users": "users.json",
            "orders": "orders.json",
            "products": "products.json",
            "policies": "policies.json",
        }.items():
            path = data_dir / filename
            if path.exists():
                merged[key] = json.loads(path.read_text(encoding="utf-8"))
        if not merged:
            raise FileNotFoundError(
                f"No supported tau-bench retail data files found in {data_dir}. "
                "Expected db.json/data.json/retail.json or users.json/orders.json/products.json."
            )
        return self._normalize_db(merged, source=str(data_dir))

    def _load_external_tau_bench_data(self) -> Any | None:
        try:
            module = importlib.import_module("tau_bench.envs.retail.data")
        except ImportError:
            return None
        load_data = getattr(module, "load_data", None)
        if load_data is None:
            return None
        return load_data()

    def _normalize_db(self, data: Any, source: str = "configured data") -> dict[str, Any]:
        if not isinstance(data, dict):
            data = {}
        normalized = {
            "users": self._records_by_id(data.get("users", {}), ("user_id", "id", "customer_id")),
            "orders": self._records_by_id(data.get("orders", {}), ("order_id", "id")),
            "products": self._records_by_id(
                data.get("products", data.get("inventory", {})),
                ("product_id", "sku", "id", "item_id"),
            ),
            "policies": dict(data.get("policies", data.get("policy", {})) or {}),
            "raw": data,
        }
        if bool(self.config.get("validate_export_schema", False)):
            self._validate_normalized_db(normalized, source=source)
        return normalized

    def _validate_normalized_db(self, db: dict[str, Any], source: str) -> None:
        missing = [
            section
            for section in ("users", "orders", "products")
            if not db.get(section)
        ]
        if missing:
            joined = ", ".join(missing)
            raise ValueError(
                f"Tau-bench retail export DB in {source} is missing required non-empty "
                f"section(s): {joined}. Expected users, orders, products, and optional "
                "policies; see docs/tau_retail_export_schema.md."
            )

    def _records_by_id(self, records: Any, id_keys: tuple[str, ...]) -> dict[str, dict[str, Any]]:
        normalized: dict[str, dict[str, Any]] = {}
        if isinstance(records, dict):
            iterable = records.items()
            for fallback_id, record in iterable:
                if isinstance(record, dict):
                    item = dict(record)
                    record_id = self._first_present(item, id_keys) or str(fallback_id)
                    item.setdefault(id_keys[0], record_id)
                    normalized[str(record_id)] = item
            return normalized
        if isinstance(records, list):
            for record in records:
                if not isinstance(record, dict):
                    continue
                item = dict(record)
                record_id = self._first_present(item, id_keys)
                if record_id is not None:
                    normalized[str(record_id)] = item
        return normalized

    def _first_present(self, record: dict[str, Any], keys: tuple[str, ...]) -> str | None:
        for key in keys:
            value = record.get(key)
            if value is not None:
                return str(value)
        return None

    def _find_user_id_by_name_zip(self, args: dict[str, Any]) -> ToolResult:
        first_name = str(args.get("first_name") or args.get("first") or "").lower()
        last_name = str(args.get("last_name") or args.get("last") or "").lower()
        zip_code = str(args.get("zip") or args.get("zip_code") or args.get("zipcode") or "")
        full_name = str(args.get("name") or "").lower()
        for user_id, user in self.db["users"].items():
            user_first = str(user.get("first_name") or "").lower()
            user_last = str(user.get("last_name") or "").lower()
            user_name = str(user.get("name") or f"{user_first} {user_last}").lower()
            if (not user_first or not user_last) and user_name:
                name_parts = user_name.split()
                user_first = user_first or (name_parts[0] if name_parts else "")
                user_last = user_last or (name_parts[-1] if len(name_parts) > 1 else "")
            user_zip = self._user_zip(user)
            name_match = (
                (first_name and last_name and first_name == user_first and last_name == user_last)
                or (full_name and full_name == user_name)
            )
            if name_match and (not zip_code or zip_code == user_zip):
                return ToolResult(
                    "find_user_id_by_name_zip",
                    args,
                    f"user_id={user_id}; name={user_name.title()}; zip={user_zip}",
                )
        return ToolResult("find_user_id_by_name_zip", args, "No matching user found.", ok=False)

    def _find_user_id_by_email(self, args: dict[str, Any]) -> ToolResult:
        email = str(args.get("email") or "").lower()
        for user_id, user in self.db["users"].items():
            if str(user.get("email") or "").lower() == email:
                return ToolResult("find_user_id_by_email", args, f"user_id={user_id}; email={email}")
        return ToolResult("find_user_id_by_email", args, f"No user found for email={email}.", ok=False)

    def _get_user_details(self, args: dict[str, Any]) -> ToolResult:
        user_id = str(args.get("user_id") or args.get("customer_id") or "")
        user = self.db["users"].get(user_id)
        if not user:
            return ToolResult("get_user_details", args, f"User {user_id} was not found.", ok=False)
        return ToolResult("get_user_details", args, self._compact_record(user))

    def _get_order_details(self, args: dict[str, Any]) -> ToolResult:
        order_id = str(args.get("order_id") or args.get("id") or "")
        order = self._get_order_record(order_id)
        if not order:
            return ToolResult(
                "get_order_details",
                args,
                f"Order {self._clean_order_id(order_id)} was not found.",
                ok=False,
            )
        return ToolResult("get_order_details", args, self._compact_record(order))

    def _get_product_details(self, args: dict[str, Any]) -> ToolResult:
        product_id = str(args.get("product_id") or args.get("sku") or args.get("item_id") or args.get("id") or "")
        product = self.db["products"].get(product_id)
        if not product:
            return ToolResult("get_product_details", args, f"Product {product_id} was not found.", ok=False)
        return ToolResult("get_product_details", args, self._compact_record(product))

    def _get_item_details(self, args: dict[str, Any]) -> ToolResult:
        item_id = str(args.get("item_id") or args.get("variant_id") or args.get("id") or "")
        variant = self._find_item_variant(item_id)
        if variant is None:
            return ToolResult("get_item_details", args, f"Item {item_id} was not found.", ok=False)
        return ToolResult("get_item_details", args, self._compact_record(variant))

    def _list_all_product_types(self, args: dict[str, Any]) -> ToolResult:
        product_types = sorted(
            {
                str(product.get("type") or product.get("product_type") or product.get("category") or "unknown")
                for product in self.db["products"].values()
            }
        )
        return ToolResult("list_all_product_types", args, "product_types=" + ", ".join(product_types))

    def _lookup_policy(self, args: dict[str, Any]) -> ToolResult:
        policy_name = str(args.get("policy_name") or args.get("name") or args.get("topic") or "")
        policies = self.db["policies"]
        if policy_name in policies:
            return ToolResult("lookup_policy", args, f"{policy_name}: {policies[policy_name]}")
        lower_name = policy_name.lower()
        for name, text in policies.items():
            if lower_name and lower_name in str(name).lower():
                return ToolResult("lookup_policy", args, f"{name}: {text}")
        if len(policies) == 1 and not policy_name:
            name, text = next(iter(policies.items()))
            return ToolResult("lookup_policy", args, f"{name}: {text}")
        return ToolResult("lookup_policy", args, f"Policy {policy_name} was not found.", ok=False)

    def _calculate(self, args: dict[str, Any]) -> ToolResult:
        expression = str(args.get("expression") or args.get("expr") or "")
        try:
            value = _safe_arithmetic_eval(expression)
        except ValueError as exc:
            return ToolResult("calculate", args, str(exc), ok=False)
        return ToolResult("calculate", args, f"{expression} = {value}")

    def _modify_order(
        self,
        tool_name: str,
        order_status: str,
        field: str,
        args: dict[str, Any],
    ) -> ToolResult:
        order_id = str(args.get("order_id") or "")
        order = self._get_order_record(order_id)
        if not order:
            return ToolResult(
                tool_name,
                args,
                f"Order {self._clean_order_id(order_id)} was not found.",
                ok=False,
            )
        if str(order.get("status", "")).lower() != order_status:
            return ToolResult(
                tool_name,
                args,
                f"Order {order_id} is {order.get('status')} and cannot be modified as {order_status}.",
                ok=False,
            )
        if field == "shipping_address":
            value = (
                args.get("address")
                or args.get("shipping_address")
                or args.get("new_address")
                or self._address_from_args(args)
            )
        elif field == "payment_method_id":
            value = args.get("payment_method_id") or args.get("new_payment_method_id")
        elif field == "items":
            value = self._updated_order_items(order, args)
        else:
            value = args.get(field) or args.get("new_" + field) or args
        if value is None:
            return ToolResult(
                tool_name,
                args,
                f"No update value was provided for {field}.",
                ok=False,
            )
        order[field] = value
        if field == "items" and args.get("new_item_ids"):
            order["status"] = "pending (item modified)"
        return ToolResult(
            tool_name,
            args,
            f"Order {self._clean_order_id(order_id)} {field} updated.",
        )

    def _modify_user_address(self, args: dict[str, Any]) -> ToolResult:
        user_id = str(args.get("user_id") or args.get("customer_id") or "")
        user = self.db["users"].get(user_id)
        if not user:
            return ToolResult("modify_user_address", args, f"User {user_id} was not found.", ok=False)
        address = self._address_from_args(args) or args.get("address") or args.get("shipping_address")
        if not isinstance(address, dict):
            return ToolResult(
                "modify_user_address",
                args,
                "No valid address fields were provided.",
                ok=False,
            )
        user["address"] = address
        return ToolResult("modify_user_address", args, f"User {user_id} address updated.")

    def _set_order_status(
        self,
        tool_name: str,
        args: dict[str, Any],
        required_status: str,
        new_status: str,
    ) -> ToolResult:
        order_id = str(args.get("order_id") or "")
        order = self._get_order_record(order_id)
        if not order:
            return ToolResult(
                tool_name,
                args,
                f"Order {self._clean_order_id(order_id)} was not found.",
                ok=False,
            )
        current_status = str(order.get("status", "")).lower()
        if current_status != required_status:
            return ToolResult(
                tool_name,
                args,
                f"Order {order_id} is {current_status} and cannot transition to {new_status}.",
                ok=False,
            )
        order["status"] = new_status
        return ToolResult(
            tool_name,
            args,
            f"Order {self._clean_order_id(order_id)} status updated to {new_status}.",
        )

    def _updated_order_items(self, order: dict[str, Any], args: dict[str, Any]) -> list[dict[str, Any]]:
        item_ids = self._normalize_id_list(args.get("item_ids") or args.get("item_id"))
        new_item_ids = self._normalize_id_list(args.get("new_item_ids") or args.get("new_item_id"))
        if item_ids and new_item_ids:
            updated_items = [dict(item) for item in order.get("items", []) if isinstance(item, dict)]
            for old_item_id, new_item_id in zip(item_ids, new_item_ids):
                variant = self._find_item_variant(new_item_id)
                for item in updated_items:
                    current_item_id = str(item.get("item_id") or item.get("id") or "")
                    if current_item_id == old_item_id:
                        item["item_id"] = new_item_id
                        if variant is not None:
                            item["product_id"] = variant.get("product_id", item.get("product_id"))
                            item["price"] = variant.get("price", item.get("price"))
                            if "options" in variant:
                                item["options"] = variant["options"]
                        break
            return updated_items

        product_ids = self._normalize_id_list(args.get("product_ids") or args.get("product_id"))
        if not product_ids:
            items = args.get("items")
            if isinstance(items, list):
                return [dict(item) for item in items if isinstance(item, dict)]
            return list(order.get("items", []))
        existing_items = [dict(item) for item in order.get("items", []) if isinstance(item, dict)]
        updated: list[dict[str, Any]] = []
        for index, product_id in enumerate(product_ids):
            base = existing_items[index] if index < len(existing_items) else {}
            base["product_id"] = product_id
            base.setdefault("item_id", f"item_{index + 1}")
            product = self.db["products"].get(product_id)
            if product and product.get("name"):
                base["name"] = product["name"]
            updated.append(base)
        return updated

    def _address_from_args(self, args: dict[str, Any]) -> dict[str, Any] | None:
        address_keys = ("address1", "address2", "city", "state", "country", "zip")
        if not any(key in args for key in address_keys):
            return None
        return {key: args.get(key, "") for key in address_keys}

    def _normalize_id_list(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, list):
            return [str(item) for item in value]
        return [str(value)]

    def _missing_item_ids(self, order: dict[str, Any], item_ids: list[str]) -> list[str]:
        if not item_ids:
            return []
        existing = {
            str(item.get("item_id") or item.get("id") or "")
            for item in order.get("items", [])
            if isinstance(item, dict)
        }
        return [item_id for item_id in item_ids if item_id not in existing]

    def _mark_order_items(self, order: dict[str, Any], item_ids: list[str], status: str) -> None:
        if not item_ids:
            return
        wanted = set(item_ids)
        for item in order.get("items", []):
            if isinstance(item, dict) and str(item.get("item_id") or item.get("id") or "") in wanted:
                item["status"] = status

    def _find_item_variant(self, item_id: str) -> dict[str, Any] | None:
        item_id = str(item_id or "")
        if not item_id:
            return None
        for product_id, product in self.db["products"].items():
            variants = product.get("variants")
            if not isinstance(variants, dict):
                continue
            variant = variants.get(item_id)
            if isinstance(variant, dict):
                item = dict(variant)
                item.setdefault("item_id", item_id)
                item.setdefault("product_id", product_id)
                item.setdefault("product_name", product.get("name"))
                return item
        return None

    def _compact_record(self, record: dict[str, Any]) -> str:
        return json.dumps(record, ensure_ascii=False, sort_keys=True)

    def _clean_order_id(self, order_id: str) -> str:
        return order_id.strip().lstrip("#")

    def _get_order_record(self, order_id: str) -> dict[str, Any] | None:
        raw_order_id = str(order_id or "").strip()
        clean_order_id = self._clean_order_id(raw_order_id)
        candidates = [
            raw_order_id,
            clean_order_id,
            f"#{clean_order_id}" if clean_order_id else "",
        ]
        for candidate in candidates:
            if candidate and candidate in self.db["orders"]:
                return self.db["orders"][candidate]
        return None

    def _user_zip(self, user: dict[str, Any]) -> str:
        direct = user.get("zip") or user.get("zip_code") or user.get("postal_code")
        if direct is not None:
            return str(direct)
        address = user.get("address") or user.get("shipping_address")
        if isinstance(address, dict):
            nested = address.get("zip") or address.get("zip_code") or address.get("postal_code")
            if nested is not None:
                return str(nested)
        return ""

    def _evaluate_task(self, task: Task, final_answer: str) -> tuple[bool, str | None]:
        expected = [part.lower() for part in task.expected_answer_contains]
        expected_actions = task.metadata.get("expected_actions") or []
        expected_state_diff = self._expected_state_diff(task)
        action_detail = self._compare_actions(expected_actions)
        state_detail = self._compare_state_diff(expected_state_diff)
        tool_semantic_errors = self._tool_semantic_errors()
        policy_violations = self._policy_violations(tool_semantic_errors)

        answer_success: bool | None = None
        if expected:
            answer_success = all(part in final_answer.lower() for part in expected)

        evaluation_mode = self._selected_evaluation_mode(
            has_expected_answer=answer_success is not None,
            has_expected_actions=bool(expected_actions),
            has_expected_state_diff=bool(expected_state_diff),
        )

        success: bool
        error_type: str | None
        if evaluation_mode == "answer_contains":
            success = bool(answer_success)
            error_type = None if success else "expected_answer_mismatch"
        elif evaluation_mode == "action_sequence":
            success = bool(action_detail["passed"])
            error_type = None if success else self._action_error_type(action_detail)
        elif evaluation_mode == "state_diff":
            success = bool(state_detail["passed"])
            error_type = None if success else "state_diff_mismatch"
        elif evaluation_mode == "policy_violation":
            success = len(policy_violations) == 0
            error_type = None if success else "policy_violation"
        elif evaluation_mode == "official_like":
            checks: list[bool] = []
            if expected_actions:
                checks.append(bool(action_detail["passed"]))
            if expected_state_diff:
                checks.append(bool(state_detail["passed"]))
            if answer_success is not None:
                checks.append(bool(answer_success))
            if not checks:
                checks.append(
                    bool(final_answer.strip())
                    and "unable to determine" not in final_answer.lower()
                )
            unexpected_policy_violations = [] if self._expects_policy_violation(task) else policy_violations
            success = all(checks) and not unexpected_policy_violations
            error_type = self._official_like_error_type(
                answer_success=answer_success,
                action_detail=action_detail,
                state_detail=state_detail,
                policy_violations=unexpected_policy_violations,
            )
        else:
            success = bool(final_answer.strip()) and "unable to determine" not in final_answer.lower()
            error_type = None if success else "empty_or_unusable_final_answer"

        self._last_evaluation_detail = {
            "task_id": task.task_id,
            "evaluation_requested": self.evaluation,
            "evaluation_mode": evaluation_mode,
            "success": success,
            "error_type": error_type,
            "answer_contains_passed": answer_success,
            "expected_answer_parts": list(task.expected_answer_contains),
            "expected_actions_matched": action_detail["passed"] if expected_actions else None,
            "expected_action_count": len(expected_actions),
            "actual_action_count": len(self._tool_history),
            "action_args_compared": self.compare_action_args,
            "action_mismatches": action_detail["mismatches"],
            "state_diff_passed": state_detail["passed"] if expected_state_diff else None,
            "state_diff_expected": expected_state_diff or None,
            "state_diff_mismatches": state_detail["mismatches"],
            "state_diff_summary": self._state_diff_summary(),
            "policy_violation_count": len(policy_violations),
            "policy_violations": policy_violations,
            "tool_semantic_error_count": len(tool_semantic_errors),
            "tool_semantic_errors": tool_semantic_errors,
        }
        return success, error_type

    def _selected_evaluation_mode(
        self,
        has_expected_answer: bool,
        has_expected_actions: bool,
        has_expected_state_diff: bool,
    ) -> str:
        if self.evaluation in {"tool_sequence", "action_sequence"}:
            return "action_sequence"
        if self.evaluation == "answer_contains":
            return "answer_contains"
        if self.evaluation == "state_diff":
            return "state_diff"
        if self.evaluation == "policy_violation":
            return "policy_violation"
        if self.evaluation == "official_like":
            return "official_like"
        if self.evaluation == "auto":
            if has_expected_state_diff:
                return "state_diff"
            if has_expected_answer:
                return "answer_contains"
            if has_expected_actions:
                return "action_sequence"
        return "heuristic_final_answer"

    def _expected_state_diff(self, task: Task) -> dict[str, Any]:
        value = (
            task.metadata.get("expected_state_diff")
            or task.metadata.get("state_diff")
            or task.metadata.get("expected_db_state")
            or {}
        )
        return dict(value) if isinstance(value, dict) else {}

    def _expects_policy_violation(self, task: Task) -> bool:
        return bool(
            task.metadata.get("expected_policy_violation")
            or task.metadata.get("expect_policy_violation")
            or task.metadata.get("allow_policy_violation")
        )

    def _official_like_error_type(
        self,
        answer_success: bool | None,
        action_detail: dict[str, Any],
        state_detail: dict[str, Any],
        policy_violations: list[dict[str, Any]],
    ) -> str | None:
        if policy_violations:
            return "policy_violation"
        if action_detail["evaluated"] and not action_detail["passed"]:
            return self._action_error_type(action_detail)
        if state_detail["evaluated"] and not state_detail["passed"]:
            return "state_diff_mismatch"
        if answer_success is False:
            return "expected_answer_mismatch"
        return None

    def _action_error_type(self, action_detail: dict[str, Any]) -> str:
        mismatch_reasons = {
            str(mismatch.get("reason")) for mismatch in action_detail["mismatches"]
        }
        if "tool_name_mismatch" in mismatch_reasons:
            return "expected_tool_name_mismatch"
        if "arg_value_mismatch" in mismatch_reasons or "missing_required_arg" in mismatch_reasons:
            return "expected_action_arg_mismatch"
        return "expected_action_sequence_mismatch"

    def _compare_actions(self, expected_actions: list[dict[str, Any]]) -> dict[str, Any]:
        mismatches: list[dict[str, Any]] = []
        if not expected_actions:
            return {"evaluated": False, "passed": None, "mismatches": mismatches}
        if len(expected_actions) != len(self._tool_history):
            mismatches.append(
                {
                    "reason": "action_count_mismatch",
                    "expected_count": len(expected_actions),
                    "actual_count": len(self._tool_history),
                }
            )
        for index, expected in enumerate(expected_actions):
            actual = self._tool_history[index] if index < len(self._tool_history) else None
            if actual is None:
                mismatches.append(
                    {
                        "reason": "missing_actual_action",
                        "index": index,
                        "expected_tool_name": expected.get("name"),
                    }
                )
                continue
            if expected.get("name") != actual.get("tool_name"):
                mismatches.append(
                    {
                        "reason": "tool_name_mismatch",
                        "index": index,
                        "expected_tool_name": expected.get("name"),
                        "actual_tool_name": actual.get("tool_name"),
                    }
                )
            if self.compare_action_args:
                mismatches.extend(self._compare_action_args(index, expected, actual))
        return {"evaluated": True, "passed": not mismatches, "mismatches": mismatches}

    def _compare_action_args(
        self,
        index: int,
        expected: dict[str, Any],
        actual: dict[str, Any],
    ) -> list[dict[str, Any]]:
        mismatches: list[dict[str, Any]] = []
        expected_args = expected.get("args", {}) if isinstance(expected.get("args", {}), dict) else {}
        actual_args = actual.get("args", {}) if isinstance(actual.get("args", {}), dict) else {}
        optional_args = set(str(item) for item in expected.get("optional_args", []))
        ignore_args = set(str(item) for item in expected.get("ignore_args", []))
        for key, expected_value in expected_args.items():
            if key in ignore_args:
                continue
            if key not in actual_args:
                if key not in optional_args:
                    mismatches.append(
                        {
                            "reason": "missing_required_arg",
                            "index": index,
                            "arg_name": key,
                            "expected": expected_value,
                        }
                    )
                continue
            normalized_expected = self._normalize_arg_value(key, expected_value)
            normalized_actual = self._normalize_arg_value(key, actual_args[key])
            if normalized_expected != normalized_actual:
                mismatches.append(
                    {
                        "reason": "arg_value_mismatch",
                        "index": index,
                        "arg_name": key,
                        "expected": expected_value,
                        "actual": actual_args[key],
                        "normalized_expected": normalized_expected,
                        "normalized_actual": normalized_actual,
                    }
                )
        if self.strict_action_args:
            extra_args = set(actual_args) - set(expected_args) - ignore_args
            for key in sorted(extra_args):
                mismatches.append(
                    {
                        "reason": "unexpected_arg",
                        "index": index,
                        "arg_name": key,
                        "actual": actual_args[key],
                    }
                )
        return mismatches

    def _normalize_arg_value(self, key: str, value: Any) -> Any:
        if isinstance(value, dict):
            return {
                str(child_key): self._normalize_arg_value(str(child_key), child_value)
                for child_key, child_value in sorted(value.items())
            }
        if isinstance(value, list):
            normalized = [self._normalize_arg_value(key, item) for item in value]
            return sorted(normalized, key=lambda item: json.dumps(item, sort_keys=True))
        if isinstance(value, str):
            text = value.strip()
            key_lower = key.lower()
            if key_lower in {"order_id", "orderid"} or key_lower.endswith("_order_id"):
                return self._clean_order_id(text).lower()
            if key_lower.endswith("_id") or key_lower in {"item_ids", "product_ids", "new_item_ids"}:
                return text.strip("#").lower()
            return text.lower()
        return value

    def _compare_state_diff(self, expected_state_diff: dict[str, Any]) -> dict[str, Any]:
        mismatches: list[dict[str, Any]] = []
        if not expected_state_diff:
            return {"evaluated": False, "passed": None, "mismatches": mismatches}
        for section, expected_records in expected_state_diff.items():
            expected_by_id = self._expected_state_records(str(section), expected_records)
            actual_section = self.db.get(section, {})
            for record_id, expected_fields in expected_by_id.items():
                actual_record = self._record_for_state_section(str(section), str(record_id), actual_section)
                if actual_record is None:
                    mismatches.append(
                        {
                            "reason": "missing_state_record",
                            "section": section,
                            "record_id": record_id,
                        }
                    )
                    continue
                mismatches.extend(
                    self._compare_expected_fields(
                        section=str(section),
                        record_id=str(record_id),
                        path="",
                        expected=expected_fields,
                        actual=actual_record,
                    )
                )
        return {"evaluated": True, "passed": not mismatches, "mismatches": mismatches}

    def _expected_state_records(self, section: str, records: Any) -> dict[str, dict[str, Any]]:
        id_keys = {
            "orders": ("order_id", "id"),
            "users": ("user_id", "id", "customer_id"),
            "products": ("product_id", "sku", "id", "item_id"),
        }.get(section, ("id",))
        if isinstance(records, dict):
            by_id: dict[str, dict[str, Any]] = {}
            for record_id, fields in records.items():
                if isinstance(fields, dict):
                    by_id[str(record_id)] = fields
            return by_id
        if isinstance(records, list):
            by_id = {}
            for record in records:
                if not isinstance(record, dict):
                    continue
                record_id = self._first_present(record, id_keys)
                if record_id is None:
                    continue
                fields = dict(record)
                for key in id_keys:
                    fields.pop(key, None)
                by_id[str(record_id)] = fields
            return by_id
        return {}

    def _record_for_state_section(
        self,
        section: str,
        record_id: str,
        actual_section: Any,
    ) -> dict[str, Any] | None:
        if not isinstance(actual_section, dict):
            return None
        if section == "orders":
            return self._get_order_record(record_id)
        candidates = [record_id, record_id.strip().lstrip("#")]
        for candidate in candidates:
            if candidate in actual_section:
                return actual_section[candidate]
        return None

    def _compare_expected_fields(
        self,
        section: str,
        record_id: str,
        path: str,
        expected: Any,
        actual: Any,
    ) -> list[dict[str, Any]]:
        mismatches: list[dict[str, Any]] = []
        if isinstance(expected, dict):
            if not isinstance(actual, dict):
                return [
                    {
                        "reason": "state_type_mismatch",
                        "section": section,
                        "record_id": record_id,
                        "path": path,
                        "expected_type": "dict",
                        "actual": actual,
                    }
                ]
            for key, expected_value in expected.items():
                child_path = f"{path}.{key}" if path else str(key)
                if key not in actual:
                    mismatches.append(
                        {
                            "reason": "missing_state_field",
                            "section": section,
                            "record_id": record_id,
                            "path": child_path,
                            "expected": expected_value,
                        }
                    )
                    continue
                mismatches.extend(
                    self._compare_expected_fields(
                        section=section,
                        record_id=record_id,
                        path=child_path,
                        expected=expected_value,
                        actual=actual[key],
                    )
                )
            return mismatches
        key = path.rsplit(".", 1)[-1] if path else ""
        normalized_expected = self._normalize_arg_value(key, expected)
        normalized_actual = self._normalize_arg_value(key, actual)
        if normalized_expected != normalized_actual:
            mismatches.append(
                {
                    "reason": "state_value_mismatch",
                    "section": section,
                    "record_id": record_id,
                    "path": path,
                    "expected": expected,
                    "actual": actual,
                    "normalized_expected": normalized_expected,
                    "normalized_actual": normalized_actual,
                }
            )
        return mismatches

    def _state_diff_summary(self) -> dict[str, Any]:
        before = self._task_initial_db or self.initial_db
        summary: dict[str, Any] = {}
        for section in ("users", "orders", "products"):
            before_records = before.get(section, {})
            after_records = self.db.get(section, {})
            section_diff = self._section_diff(before_records, after_records)
            if section_diff:
                summary[section] = section_diff
        return summary

    def _section_diff(
        self,
        before_records: Any,
        after_records: Any,
    ) -> dict[str, Any]:
        if not isinstance(before_records, dict) or not isinstance(after_records, dict):
            return {}
        diff: dict[str, Any] = {}
        for record_id in sorted(set(before_records) | set(after_records)):
            before = before_records.get(record_id)
            after = after_records.get(record_id)
            if before != after:
                diff[record_id] = self._record_diff(before, after)
        return diff

    def _record_diff(self, before: Any, after: Any) -> dict[str, Any]:
        if not isinstance(before, dict) or not isinstance(after, dict):
            return {"before": before, "after": after}
        changes: dict[str, Any] = {}
        for key in sorted(set(before) | set(after)):
            before_value = before.get(key)
            after_value = after.get(key)
            if before_value != after_value:
                changes[key] = {"before": before_value, "after": after_value}
        return changes

    def _tool_semantic_errors(self) -> list[dict[str, Any]]:
        return [
            {
                "tool_name": record.get("tool_name"),
                "args": record.get("args", {}),
                "observation": record.get("observation", ""),
            }
            for record in self._tool_history
            if record.get("ok") is False
        ]

    def _policy_violations(self, tool_semantic_errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
        mutation_tools = {
            "modify_pending_order_address",
            "modify_pending_order_payment",
            "modify_pending_order_items",
            "cancel_pending_order",
            "return_delivered_order_items",
            "exchange_delivered_order_items",
            "modify_user_address",
        }
        violations = []
        for error in tool_semantic_errors:
            tool_name = str(error.get("tool_name") or "")
            if tool_name in mutation_tools:
                violation = dict(error)
                violation["violation_type"] = "retail_tool_precondition_failed"
                violations.append(violation)
        return violations


def _safe_arithmetic_eval(expression: str) -> int | float:
    operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    def evaluate(node: ast.AST) -> int | float:
        if isinstance(node, ast.Expression):
            return evaluate(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in operators:
            return operators[type(node.op)](evaluate(node.left), evaluate(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in operators:
            return operators[type(node.op)](evaluate(node.operand))
        raise ValueError(f"Unsupported arithmetic expression: {expression}")

    return evaluate(ast.parse(expression, mode="eval"))
