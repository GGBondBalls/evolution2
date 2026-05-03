# Tau-Retail Export Schema

This document defines the first-stage local export format for running small
tau-bench retail samples through `TauBenchEnv` without requiring the external
tau-bench package at runtime.

The goal is not to replace the official benchmark. The goal is to make phase-one
closure reproducible: a real or exported retail sample should load, run, write
`tasks.jsonl`, `runs.jsonl`, `trace_events.jsonl`, memory logs, and `metrics.json`,
or fail with an actionable setup error.

## Config

Use the versioned phase-one configs as the starting point:

```yaml
benchmark:
  name: tau_bench
  domain: retail
  split_file: data/task_splits/tau_retail_export_sample_tasks.py
  data_dir: data/tau_bench/retail_export_sample
  evaluation: auto
  require_data: true
  validate_export_schema: true
  max_tasks: 3
```

`split_file` may point to `.json`, `.jsonl`, or `.py`.

`data_file` may point to one merged JSON DB file. `data_dir` may contain either
`db.json`, `data.json`, `retail.json`, `retail_db.json`, or split files named
`users.json`, `orders.json`, `products.json`, and optional `policies.json`.

Set `validate_export_schema: true` for exported samples. This catches missing
instructions, missing expected outcomes, empty task files, and DB files without
the required retail sections before the agent loop starts.

## Task Records

Each task record must be a JSON/Python mapping. The adapter accepts common
tau-bench-like aliases so exported files do not need heavy rewriting.

Required:

```json
{
  "id": "tau_retail_0001",
  "user_instruction": "Find the customer id for yusuf.rossi@example.com.",
  "expected_answer_contains": ["user_1"],
  "actions": [
    {
      "name": "find_user_id_by_email",
      "kwargs": {"email": "yusuf.rossi@example.com"}
    }
  ],
  "intent": "customer_lookup",
  "no_memory_success": true
}
```

Accepted task id keys: `task_id`, `id`, `taskId`.

Accepted instruction keys: `instruction`, `user_instruction`, `query`, `message`.

Accepted expected answer keys: `expected_answer_contains`, `expected_answer`.

Accepted expected action keys: `actions`, `expected_actions`.

Accepted action name keys: `name`, `tool_name`, `action`.

Accepted action argument keys: `args`, `arguments`, `kwargs`.

At least one expected outcome must be present:

1. `expected_answer_contains` or `expected_answer`, used by
   `evaluation=answer_contains` and preferred by `evaluation=auto`.
2. `actions` or `expected_actions`, used by `evaluation=tool_sequence`,
   `evaluation=action_sequence`, and as fallback by `evaluation=auto`.

Recommended metadata:

```json
{
  "intent": "customer_lookup | order_lookup | product_lookup | policy_lookup | refund_or_return | exchange_item | cancel_order | modify_order | retail_support",
  "tool_names": ["find_user_id_by_email"],
  "no_memory_success": true,
  "no_memory_reward": 1.0
}
```

If `intent` is omitted, the adapter infers it from the instruction and expected
tool names. Supplying `intent` is strongly recommended because NT-MemEvo gate
uses it for conservative precondition matching.

## Retail DB

Merged DB example:

```json
{
  "users": [
    {
      "user_id": "user_1",
      "first_name": "Yusuf",
      "last_name": "Rossi",
      "email": "yusuf.rossi@example.com",
      "address": {"zip": "19122"},
      "orders": ["#W2378156"]
    }
  ],
  "orders": [
    {
      "order_id": "#W2378156",
      "user_id": "user_1",
      "status": "delivered",
      "items": [{"item_id": "item_1", "product_id": "1656367028"}]
    }
  ],
  "products": [
    {
      "product_id": "1656367028",
      "name": "Everyday Hoodie",
      "type": "apparel"
    }
  ],
  "policies": {
    "return_window": "Delivered retail orders can be returned within 30 days."
  }
}
```

Required non-empty sections when `validate_export_schema: true`:

1. `users`
2. `orders`
3. `products`

Optional:

1. `policies`
2. `policy`
3. `inventory` as an alias for `products`

The adapter normalizes IDs from common keys:

1. users: `user_id`, `id`, `customer_id`
2. orders: `order_id`, `id`
3. products: `product_id`, `sku`, `id`, `item_id`

Order IDs with or without a leading `#` are accepted by order tools. User zip
codes may be stored directly as `zip`, `zip_code`, or `postal_code`, or nested in
`address` / `shipping_address`.

## Supported Retail Tools

Phase one implements the tools needed for smoke and small exported samples:

1. `find_user_id_by_name_zip`
2. `find_user_id_by_email`
3. `get_user_details`
4. `get_order_details`
5. `get_product_details`
6. `list_all_product_types`
7. `lookup_policy`
8. `calculate`
9. `think`
10. `transfer_to_human_agents`
11. `modify_pending_order_address`
12. `modify_pending_order_payment`
13. `modify_pending_order_items`
14. `cancel_pending_order`
15. `return_delivered_order_items`
16. `exchange_delivered_order_items`

The mutation tools are minimal state updates, not a full official tau-bench
retail simulator. For phase-one closure, use `max_tasks=1` or `max_tasks=3` and
inspect failed tasks before expanding coverage.

## Known Blockers

The following remain second-stage work:

1. Full official tau-bench retail state machine parity.
2. Official policy-violation and state-diff evaluator parity.
3. Real model experiments beyond the deterministic mock actor.
4. Real tau-retail support pool construction for replay verification.
5. Learned support selector, learned gate/ranker, and broader memory merge/split.

When a real export fails, keep the failing task and DB fragment small, run with
`max_tasks=1`, and inspect `trace_events.jsonl` plus `runs.jsonl` first. If the
failure is a missing tool semantic or evaluator mismatch, record it as a phase-two
adapter gap rather than expanding the local smoke fixture.
