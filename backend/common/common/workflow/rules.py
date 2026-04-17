"""Rule evaluator for workflow conditions."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class RuleEvaluator:
    """Evaluate JSON-based workflow conditions against a context dict."""

    OPERATORS = {
        "eq": lambda a, b: a == b,
        "ne": lambda a, b: a != b,
        "lt": lambda a, b: float(a) < float(b),
        "lte": lambda a, b: float(a) <= float(b),
        "gt": lambda a, b: float(a) > float(b),
        "gte": lambda a, b: float(a) >= float(b),
        "in": lambda a, b: a in b,
        "not_in": lambda a, b: a not in b,
    }

    @staticmethod
    def evaluate(condition: dict, context: dict) -> bool:
        """
        Evaluate a condition against the given context.

        Supports:
        - Simple: {"field": "amount", "op": "lt", "value": 100000}
        - AND:    {"op": "and", "conditions": [...]}
        - OR:     {"op": "or", "conditions": [...]}
        """
        if not condition:
            return False

        op = condition.get("op", "")

        # Logical AND
        if op == "and":
            conditions = condition.get("conditions", [])
            return all(RuleEvaluator.evaluate(c, context) for c in conditions)

        # Logical OR
        if op == "or":
            conditions = condition.get("conditions", [])
            return any(RuleEvaluator.evaluate(c, context) for c in conditions)

        # Simple field comparison
        field = condition.get("field")
        value = condition.get("value")
        if not field or not op:
            return False

        # Get context value using dot notation (e.g., "creator.department_id")
        ctx_value = RuleEvaluator._get_nested(context, field)
        if ctx_value is None:
            return False

        operator_fn = RuleEvaluator.OPERATORS.get(op)
        if not operator_fn:
            logger.warning("Unknown operator: %s", op)
            return False

        try:
            return operator_fn(ctx_value, value)
        except (TypeError, ValueError):
            logger.warning("Failed to evaluate rule: field=%s, op=%s, value=%s, ctx=%s",
                           field, op, value, ctx_value)
            return False

    @staticmethod
    def _get_nested(data: dict, key: str) -> Any:
        """Get a value from nested dict using dot notation."""
        parts = key.split(".")
        current = data
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current
