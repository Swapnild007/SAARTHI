"""Bounded arithmetic parser, shared by deterministic requests and tests."""
import ast
import math
import operator
import re


def calculate(text: str) -> dict:
    expression = re.sub(r'^.*?\b(?:calculate|compute|calculator|what is)\b', '', text, flags=re.I).strip(' :?')
    percent = re.fullmatch(r'(-?\d+(?:\.\d+)?)\s*(?:%|percent)\s+of\s+(-?\d+(?:\.\d+)?)', expression, re.I)
    if percent:
        expression = f'{percent[1]} / 100 * {percent[2]}'
    expression = expression.replace('×', '*').replace('÷', '/').replace('^', '**')
    expression = re.sub(r'(?<=\d)\s*[xX]\s*(?=[\d(])', '*', expression)
    if len(expression) > 200 or not re.fullmatch(r'[\d\s.+*/%()\-]+', expression):
        raise ValueError('Enter arithmetic such as (12 + 8) * 3 or 15% of 200.')
    tree = ast.parse(expression, mode='eval')
    if len(list(ast.walk(tree))) > 80:
        raise ValueError('Calculation is too complex.')
    operations = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.Mod: operator.mod, ast.Pow: operator.pow}
    def visit(node):
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            value = float(node.value)
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = visit(node.operand) * (-1 if isinstance(node.op, ast.USub) else 1)
        elif isinstance(node, ast.BinOp) and type(node.op) in operations:
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Pow) and (abs(right) > 100 or abs(left) > 1e12):
                raise ValueError('Power exceeds safe calculation limits.')
            value = operations[type(node.op)](left, right)
        else:
            raise ValueError('Unsupported calculation.')
        if not isinstance(value, (int, float)) or not math.isfinite(value) or abs(value) > 1e100:
            raise ValueError('Result exceeds safe calculation limits.')
        return value
    try:
        value = visit(tree)
    except (ZeroDivisionError, OverflowError):
        raise ValueError('Calculation is undefined or exceeds safe limits.') from None
    return {'expression': expression, 'value': value}
