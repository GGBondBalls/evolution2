from __future__ import annotations

import ast
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
        self._tool_history: list[dict[str, Any]] = []
        self.db = self._load_retail_db()

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
                "list_all_product_types() -> available product type names",
                "lookup_policy(policy_name: str) -> retail policy text",
                "calculate(expression: str) -> arithmetic result",
                "think(thought: str) -> private reasoning note",
                "transfer_to_human_agents(summary: str) -> escalate to a human support agent",
                "modify_pending_order_address(order_id: str, address: dict) -> update pending order shipping address",
                "modify_pending_order_payment(order_id: str, payment_method_id: str) -> update pending order payment method",
                "modify_pending_order_items(order_id: str, item_ids: list[str], product_ids: list[str]) -> update pending order items",
                "cancel_pending_order(order_id: str, reason: str) -> cancel a pending order",
                "return_delivered_order_items(order_id: str, item_ids: list[str]) -> return delivered order items",
                "exchange_delivered_order_items(order_id: str, item_ids: list[str], product_ids: list[str]) -> exchange delivered order items",
            ]
        )

    def call_tool(self, tool_name: str, args: dict[str, Any]) -> ToolResult:
        if not isinstance(args, dict):
            args = {}
        tool_name = str(tool_name)
        self._tool_history.append({"tool_name": tool_name, "args": dict(args)})

        if tool_name == "find_user_id_by_name_zip":
            return self._find_user_id_by_name_zip(args)
        if tool_name == "find_user_id_by_email":
            return self._find_user_id_by_email(args)
        if tool_name == "get_user_details":
            return self._get_user_details(args)
        if tool_name == "get_order_details":
            return self._get_order_details(args)
        if tool_name == "get_product_details":
            return self._get_product_details(args)
        if tool_name == "list_all_product_types":
            return self._list_all_product_types(args)
        if tool_name == "lookup_policy":
            return self._lookup_policy(args)
        if tool_name == "calculate":
            return self._calculate(args)
        if tool_name == "think":
            return ToolResult(tool_name, args, f"Noted: {args.get('thought', '')}")
        if tool_name == "transfer_to_human_agents":
            return ToolResult(tool_name, args, f"Transferred to human agents: {args.get('summary', '')}")
        if tool_name == "modify_pending_order_address":
            return self._modify_order(order_status="pending", field="address", args=args)
        if tool_name == "modify_pending_order_payment":
            return self._modify_order(order_status="pending", field="payment_method_id", args=args)
        if tool_name == "modify_pending_order_items":
            return self._modify_order(order_status="pending", field="items", args=args)
        if tool_name == "cancel_pending_order":
            return self._set_order_status(
                tool_name=tool_name,
                args=args,
                required_status="pending",
                new_status="cancelled",
            )
        if tool_name == "return_delivered_order_items":
            return self._set_order_status(
                tool_name=tool_name,
                args=args,
                required_status="delivered",
                new_status="return_requested",
            )
        if tool_name == "exchange_delivered_order_items":
            return self._set_order_status(
                tool_name=tool_name,
                args=args,
                required_status="delivered",
                new_status="exchange_requested",
            )
        return ToolResult(tool_name, args, f"Unknown tau-bench retail tool: {tool_name}", ok=False)

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
            self._validate_task_records_if_requested(records, source=str(split_file))
            return records

        task_module = self.config.get("task_module")
        if task_module:
            records = self._load_task_records_from_module(str(task_module))
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
            task_id = record.get("task_id") or record.get("id") or record.get("taskId") or f"#{index}"
            instruction = (
                record.get("instruction")
                or record.get("user_instruction")
                or record.get("query")
                or record.get("message")
            )
            if not isinstance(instruction, str) or not instruction.strip():
                raise ValueError(
                    f"Tau-bench export task {task_id!r} in {source} is missing a non-empty "
                    "instruction/user_instruction/query/message field."
                )

            expected = record.get("expected_answer_contains")
            if expected is None:
                expected = record.get("expected_answer")
            has_expected_answer = bool(self._normalize_expected_answer(expected))
            raw_actions = record.get("actions") or record.get("expected_actions")
            actions = self._normalize_actions(raw_actions)
            if not has_expected_answer and not actions:
                raise ValueError(
                    f"Tau-bench export task {task_id!r} in {source} must provide either "
                    "expected_answer_contains/expected_answer or actions/expected_actions."
                )
            if raw_actions is not None and not actions:
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
        task_id = str(
            record.get("task_id")
            or record.get("id")
            or record.get("taskId")
            or f"tau_retail_{index:04d}"
        )
        instruction = str(
            record.get("instruction")
            or record.get("user_instruction")
            or record.get("query")
            or record.get("message")
            or ""
        )
        if not instruction:
            raise ValueError(f"Tau-bench task {task_id} does not contain an instruction field.")

        expected = record.get("expected_answer_contains")
        if expected is None:
            expected = record.get("expected_answer")
        expected_answer_contains = self._normalize_expected_answer(expected)
        expected_actions = self._normalize_actions(record.get("actions") or record.get("expected_actions"))
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
        metadata["benchmark"] = "tau_bench"
        metadata["domain"] = metadata.get("domain", "retail")
        metadata["intent"] = metadata.get("intent") or self._infer_intent(instruction, tool_names)
        metadata["tool_names"] = list(tool_names) if isinstance(tool_names, list) else []
        metadata["expected_actions"] = expected_actions
        metadata["no_memory_success"] = bool(metadata.get("no_memory_success", True))
        return Task(
            task_id=task_id,
            instruction=instruction,
            expected_answer_contains=expected_answer_contains,
            metadata=metadata,
        )

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
            normalized.append({"name": str(name), "args": dict(args) if isinstance(args, dict) else {}})
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

    def _modify_order(self, order_status: str, field: str, args: dict[str, Any]) -> ToolResult:
        order_id = str(args.get("order_id") or "")
        order = self._get_order_record(order_id)
        if not order:
            return ToolResult(
                f"modify_pending_order_{field}",
                args,
                f"Order {self._clean_order_id(order_id)} was not found.",
                ok=False,
            )
        if str(order.get("status", "")).lower() != order_status:
            return ToolResult(
                f"modify_pending_order_{field}",
                args,
                f"Order {order_id} is {order.get('status')} and cannot be modified as {order_status}.",
                ok=False,
            )
        order[field] = args.get(field) or args.get("new_" + field) or args
        return ToolResult(
            f"modify_pending_order_{field}",
            args,
            f"Order {self._clean_order_id(order_id)} {field} updated.",
        )

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
        if self.evaluation in {"auto", "answer_contains"} and expected:
            success = all(part in final_answer.lower() for part in expected)
            return success, None if success else "expected_answer_mismatch"

        expected_actions = task.metadata.get("expected_actions") or []
        if self.evaluation in {"auto", "tool_sequence", "action_sequence"} and expected_actions:
            success = self._actions_match(expected_actions)
            return success, None if success else "expected_action_sequence_mismatch"

        success = bool(final_answer.strip()) and "unable to determine" not in final_answer.lower()
        return success, None if success else "empty_or_unusable_final_answer"

    def _actions_match(self, expected_actions: list[dict[str, Any]]) -> bool:
        if len(expected_actions) != len(self._tool_history):
            return False
        for expected, actual in zip(expected_actions, self._tool_history, strict=True):
            if expected.get("name") != actual.get("tool_name"):
                return False
            if self.compare_action_args and expected.get("args", {}) != actual.get("args", {}):
                return False
        return True


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
