"""Isolation lint (hygiene rule #6): the Scope 1 module must not import Carbon OS
business modules or any sibling scope. Allowed shared imports are only db.client,
db.org_store, api.middleware.auth, api.models.scope1_schemas, and our own
s1_*/db.s1_* code (plus third-party + langgraph infra)."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Everything the Scope 1 module owns.
SCOPE1_PATHS = [
    "s1_calc", "s1_factors", "s1_consolidation", "s1_reporting", "s1_intake",
    "s1_onboarding", "s1_recalc", "s1_fugitive", "s1_process",
    "api/routes/scope1.py", "db/scope1_store.py", "db/s1_bayou_store.py",
    "api/models/scope1_schemas.py", "api/graphs/scope1_ocr_graph.py",
]

# Carbon OS business modules we must never couple to.
FORBIDDEN_TOPLEVEL = {
    "calc", "factors", "parsing", "gap_analyzer", "copilot",
    "rag", "exchange", "llm", "mcp_server",
}


def _is_forbidden(module: str) -> bool:
    if not module:
        return False
    parts = module.split(".")
    top = parts[0]
    if top in FORBIDDEN_TOPLEVEL:
        return True
    if top.startswith(("s2_", "s3_")):                      # sibling scope package
        return True
    if top == "db" and len(parts) > 1 and parts[1].startswith(("s2_", "s3_")):
        return True                                          # db.s2_* / db.s3_* store
    return False


def _module_files():
    for entry in SCOPE1_PATHS:
        path = ROOT / entry
        if path.is_dir():
            yield from path.rglob("*.py")
        elif path.exists():
            yield path


def _imported_modules(path: Path):
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.module


def test_scope1_module_is_isolated() -> None:
    files = list(_module_files())
    assert files, "no Scope 1 module files found — check SCOPE1_PATHS"
    violations = [
        f"{path.relative_to(ROOT)} imports forbidden module '{module}'"
        for path in files
        for module in _imported_modules(path)
        if _is_forbidden(module)
    ]
    assert not violations, "Scope 1 isolation violated:\n" + "\n".join(violations)
