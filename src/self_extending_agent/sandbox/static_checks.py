from __future__ import annotations

import ast


# This is intentionally conservative for an assignment/demo.
# The generated mathematical/data-transformation tools are expected to be
# pure functions. Expand this only with a proper policy and stronger isolation.
FORBIDDEN_IMPORT_ROOTS = {
    "os", "sys", "subprocess", "socket", "requests", "httpx",
    "urllib", "pathlib", "shutil", "ctypes", "multiprocessing",
}
FORBIDDEN_CALLS = {
    "eval", "exec", "compile", "__import__", "open", "input",
    "breakpoint", "globals", "locals",
}


def validate_generated_source(source: str) -> list[str]:
    reasons: list[str] = []
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [f"Syntax error: {exc}"]

    has_run = False

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif node.module:
                names = [node.module.split(".")[0]]
            for name in names:
                if name in FORBIDDEN_IMPORT_ROOTS:
                    reasons.append(f"Forbidden import: {name}")

        if isinstance(node, ast.FunctionDef) and node.name == "run":
            has_run = True

        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_CALLS:
                reasons.append(f"Forbidden call: {node.func.id}")

        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            reasons.append(f"Dunder attribute access is not allowed: {node.attr}")

    if not has_run:
        reasons.append("Generated source must define run(args: dict) -> dict.")

    return sorted(set(reasons))
