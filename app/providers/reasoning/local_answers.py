from __future__ import annotations

import ast
import math
import operator
import re

from app.domain.models import ActionType, ReasoningResult


def local_answer(text: str) -> ReasoningResult | None:
    """Handle small, unambiguous requests without a model or network call."""
    lower = text.lower().strip().rstrip("?!.")
    if lower in {"hey", "hi", "hello", "hey companion", "hello companion"}:
        return _answer("Hi! How can I help you?")
    if lower in {"thanks", "thank you"}:
        return _answer("You're welcome!")
    if lower in {"what is your name", "what's your name", "whats your name",
                 "who are you", "what are you called"}:
        return _answer("I'm Local Companion, your local personal assistant.")
    if lower in {"what is my name", "what's my name", "whats my name",
                 "do you know my name", "do you remember my name", "who am i"}:
        return ReasoningResult(
            action=ActionType.SEARCH_MEMORY,
            parameters={"query": "name", "memory_kind": "user_name"},
            confidence=1.0, response="",
        )
    name_match = re.fullmatch(
        r"(?:remember\s+(?:that\s+)?)?my name is\s+([^\r\n?!]+)[.!]?",
        text.strip(), flags=re.I,
    )
    if name_match:
        name = name_match.group(1).strip().rstrip(".").strip()
        if name:
            return ReasoningResult(
                action=ActionType.SAVE_MEMORY,
                parameters={"content": f"my name is {name}", "user_name": name},
                confidence=1.0, response="",
            )
    # Personal statements and explicit notes must be written by the app, not acknowledged by a model.
    fact = re.sub(r"^(?:remember|save|store|note that|keep in mind)\s+(?:that\s+)?", "",
                  text.strip(), flags=re.I)
    if (fact != text.strip() or re.match(
            r"^(?:my\s+.+?\s+(?:is|are)\s+|I\s+(?:live in|work at|work as|like|prefer)\s+)",
            fact, flags=re.I)):
        if fact.strip():
            return ReasoningResult(action=ActionType.SAVE_MEMORY,
                                   parameters={"content": fact.strip()}, confidence=1.0, response="")

    expression = re.sub(r"^(?:what is|what's|calculate|compute)\s+", "", lower)
    for word, symbol in (("plus", "+"), ("minus", "-"), ("times", "*"),
                         ("multiplied by", "*"), ("divided by", "/")):
        expression = re.sub(rf"\b{word}\b", symbol, expression)
    # Restricted grammar and bounded input: never evaluate user code.
    if (len(expression) <= 120 and re.fullmatch(r"[\d\s.()+*/%-]+", expression)
            and re.search(r"\d", expression) and re.search(r"[+*/%-]", expression)):
        try:
            tree = ast.parse(expression, mode="eval")
            operations = {ast.Add: operator.add, ast.Sub: operator.sub,
                          ast.Mult: operator.mul, ast.Div: operator.truediv,
                          ast.Mod: operator.mod}

            def evaluate(node: ast.AST) -> float | int:
                if isinstance(node, ast.Constant) and type(node.value) in (int, float):
                    value = node.value
                elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
                    value = evaluate(node.operand) * (-1 if isinstance(node.op, ast.USub) else 1)
                elif isinstance(node, ast.BinOp) and type(node.op) in operations:
                    value = operations[type(node.op)](evaluate(node.left), evaluate(node.right))
                else:
                    raise ValueError("Unsupported operation")
                if abs(value) > 1e100 or not math.isfinite(value):
                    raise ValueError("Result is too large")
                return value

            value = evaluate(tree.body)
            if isinstance(value, float) and value.is_integer():
                value = int(value)
            return _answer(str(value))
        except ZeroDivisionError:
            return _answer("I can't divide by zero.")
        except (SyntaxError, ValueError, OverflowError, RecursionError):
            return _answer("Please use a simple arithmetic expression with +, -, *, /, or %.")

    # Normalize this common typo only for retrieval, never rewrite saved facts.
    query = re.sub(r"\bme{3,}ting\b", "meeting", lower)
    if (re.match(r"^(?:when|what is|what's|what time|what date|where is|where's)\b", query)
            and re.search(r"\b(?:my|our|meeting|birthday|deadline|anniversary|appointment)\b", query)
            and not re.search(r"\b(?:weather|temperature|forecast|news|headlines)\b", query)):
        return ReasoningResult(action=ActionType.SEARCH_MEMORY,
                               parameters={"query": query}, confidence=0.95, response="")
    return None


def _answer(response: str) -> ReasoningResult:
    return ReasoningResult(action=ActionType.ANSWER, parameters={},
                           confidence=1.0, response=response)
