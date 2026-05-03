TASKS = [
    {
        "id": "tau_retail_0001",
        "user_instruction": "Find the customer id for yusuf.rossi@example.com.",
        "expected_answer_contains": ["user_1"],
        "user_id": "user_1",
        "actions": [
            {
                "name": "find_user_id_by_email",
                "kwargs": {"email": "yusuf.rossi@example.com"},
            }
        ],
        "intent": "customer_lookup",
        "no_memory_success": True,
    },
    {
        "id": "tau_retail_0002",
        "user_instruction": "Look up the details for order #W2378156.",
        "expected_answer_contains": ["W2378156", "delivered"],
        "user_id": "user_1",
        "actions": [
            {
                "name": "get_order_details",
                "kwargs": {"order_id": "#W2378156"},
            }
        ],
        "intent": "order_lookup",
        "no_memory_success": True,
    },
    {
        "id": "tau_retail_0003",
        "user_instruction": "Get product details for product 1656367028.",
        "expected_answer_contains": ["1656367028", "Everyday Hoodie"],
        "user_id": "user_1",
        "actions": [
            {
                "name": "get_product_details",
                "kwargs": {"product_id": "1656367028"},
            }
        ],
        "intent": "product_lookup",
        "no_memory_success": True,
    },
]
