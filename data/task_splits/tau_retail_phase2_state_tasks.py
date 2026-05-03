TASKS = [
    {
        "id": "tau_retail_phase2_read_001",
        "user_instruction": "Look up the details for order #READ1001.",
        "expected_answer_contains": ["READ1001", "delivered"],
        "actions": [
            {
                "name": "get_order_details",
                "kwargs": {"order_id": "#READ1001"},
            }
        ],
        "intent": "order_lookup",
        "tool_names": ["get_order_details"],
        "no_memory_success": True,
    },
    {
        "id": "tau_retail_phase2_cancel_001",
        "user_instruction": "Cancel pending order #PEND2001 because the customer requested cancellation.",
        "expected_answer_contains": ["cancelled"],
        "actions": [
            {
                "name": "cancel_pending_order",
                "kwargs": {
                    "order_id": "#PEND2001",
                    "reason": "customer_request",
                },
            }
        ],
        "expected_state_diff": {
            "orders": {
                "#PEND2001": {
                    "status": "cancelled",
                    "cancel_reason": "customer_request",
                }
            }
        },
        "intent": "cancel_order",
        "tool_names": ["cancel_pending_order"],
        "no_memory_success": True,
    },
    {
        "id": "tau_retail_phase2_return_policy_fail_001",
        "user_instruction": "Return item item_pend_1 from pending order #PEND2002.",
        "expected_answer_contains": ["cannot return"],
        "actions": [
            {
                "name": "return_delivered_order_items",
                "kwargs": {
                    "order_id": "#PEND2002",
                    "item_ids": ["item_pend_1"],
                },
            }
        ],
        "intent": "refund_or_return",
        "tool_names": ["return_delivered_order_items"],
        "no_memory_success": False,
    },
]
