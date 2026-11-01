"""A small, safe expression language for config files (flag conditions, band thresholds).

Expressions are parsed with Python's ast module and interpreted by walking a whitelist of node types: numbers,
strings, booleans, names, arithmetic (+ - * / ** %), comparisons, and/or/not, a if c else b, and calls to
whitelisted functions by name. Attribute access, subscripts, lambdas, comprehensions, imports and anything else
are rejected at compile time. Python's eval() is never used.
"""
from __future__ import annotations

import ast
import math
import operator
from typing import Any, Callable, Dict

ALLOWED = (
    ast.Expression, ast.BoolOp, ast.And, ast.Or, ast.UnaryOp, ast.Not, ast.USub, ast.UAdd, ast.BinOp, ast.Add, ast.Sub,
    ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.Compare, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Eq, ast.NotEq, ast.Call, ast.Name,
    ast.Load, ast.Constant, ast.IfExp, ast.keyword,
)
BINOPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
          ast.Pow: operator.pow, ast.Mod: operator.mod}
CMPOPS = {ast.Lt: operator.lt, ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge, ast.Eq: operator.eq,
          ast.NotEq: operator.ne}
OPS_BY_STR = {">": operator.gt, ">=": operator.ge, "<": operator.lt, "<=": operator.le, "==": operator.eq, "!=": operator.ne}


class ExprError(ValueError):
    """Invalid expression (rejected at compile time) or invalid evaluation."""


class Missing(Exception):
    """Data needed by the expression is not available (rule becomes 'not evaluable')."""

    def __init__(self, what: str):
        super().__init__(what)
        self.what = what


def compile_expr(src: str, allowed_funcs=None) -> ast.Expression:
    if not isinstance(src, str) or not src.strip():
        raise ExprError("empty expression")
    try:
        tree = ast.parse(src.strip(), mode="eval")
    except SyntaxError as e:
        raise ExprError(f"syntax error in '{src}': {e.msg}") from None
    for node in ast.walk(tree):
        if not isinstance(node, ALLOWED):
            raise ExprError(f"'{type(node).__name__}' is not allowed in expressions: {src}")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ExprError(f"only direct function calls are allowed: {src}")
            if allowed_funcs is not None and node.func.id not in allowed_funcs:
                raise ExprError(f"unknown function '{node.func.id}' in: {src}")
        if isinstance(node, ast.Constant) and not isinstance(node.value, (int, float, str, bool)) and node.value is not None:
            raise ExprError(f"constant type not allowed: {src}")
        if isinstance(node, ast.Name) and node.id.startswith("_"):
            raise ExprError(f"names starting with '_' are not allowed: {src}")
    return tree


def evaluate(tree: ast.Expression, names: Dict[str, Any], funcs: Dict[str, Callable]) -> Any:
    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant):
            return n.value
        if isinstance(n, ast.Name):
            if n.id in ("True", "False", "None"):
                return {"True": True, "False": False, "None": None}[n.id]
            if n.id not in names:
                raise ExprError(f"unknown name '{n.id}'")
            v = names[n.id]
            if v is None or (isinstance(v, float) and math.isnan(v)):
                raise Missing(n.id)
            return v
        if isinstance(n, ast.UnaryOp):
            v = ev(n.operand)
            if isinstance(n.op, ast.Not):
                return not v
            return -v if isinstance(n.op, ast.USub) else +v
        if isinstance(n, ast.BinOp):
            a, b = ev(n.left), ev(n.right)
            try:
                r = BINOPS[type(n.op)](a, b)
            except ZeroDivisionError:
                raise Missing("division by zero")
            if isinstance(r, float) and (math.isnan(r) or math.isinf(r)):
                raise Missing("non-finite arithmetic result")
            return r
        if isinstance(n, ast.BoolOp):
            if isinstance(n.op, ast.And):
                for v in n.values:
                    if not ev(v):
                        return False
                return True
            for v in n.values:
                if ev(v):
                    return True
            return False
        if isinstance(n, ast.Compare):
            left = ev(n.left)
            for op, comp in zip(n.ops, n.comparators):
                right = ev(comp)
                if not CMPOPS[type(op)](left, right):
                    return False
                left = right
            return True
        if isinstance(n, ast.IfExp):
            return ev(n.body) if ev(n.test) else ev(n.orelse)
        if isinstance(n, ast.Call):
            fn = funcs.get(n.func.id)
            if fn is None:
                raise ExprError(f"unknown function '{n.func.id}'")
            args = [ev(a) for a in n.args]
            kwargs = {k.arg: ev(k.value) for k in n.keywords}
            return fn(*args, **kwargs)
        raise ExprError(f"unsupported node {type(n).__name__}")

    return ev(tree)


def eval_number(src, names: Dict[str, Any]) -> float:
    """Evaluate a band threshold (number or arithmetic over market variables)."""
    if isinstance(src, (int, float)) and not isinstance(src, bool):
        return float(src)
    tree = compile_expr(str(src), allowed_funcs={"min", "max", "abs"})
    return float(evaluate(tree, names, {"min": min, "max": max, "abs": abs}))
