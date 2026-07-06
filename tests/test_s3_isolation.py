"""Isolation lint for the Scope-3 module (hygiene rule 6).

Parses every Scope-3 source file (AST) and FAILS if it imports:
  - a Carbon OS shared business module (calc/factors/parsing/gap_analyzer/
    copilot/rag/exchange/llm/mcp_server),
  - a sibling scope (any s1_*/s2_* package, or db.s1_*/db.s2_* store),
  - a db.* / api.* module outside the allowed shared surface.

Allowed shared imports: db.client, db.org_store, api.middleware.auth,
api.models.scope3_schemas, and the module's own s3_*/db.s3_* code.

This keeps Scope 3 cleanly mergeable onto main independently of the other
scope modules. The Scope-3 code vendors its own CEDA engine (s3_factors) rather
than importing the PCF product's factors/, precisely so this test passes.
"""

from __future__ import annotations

import ast
from pathlib import Path

_ROOT = Path(__file__).parent.parent

# Scope-3 owns these package dirs + file-name patterns.
_SCAN_DIRS = ["s3_factors", "s3_measure", "s3_obligations", "s3_targets", "s3_questionnaire"]
_SCAN_GLOBS = ["api/routes/scope3_*.py", "db/s3_*_store.py", "api/models/scope3_schemas.py"]

_FORBIDDEN_BUSINESS = {
    "calc", "factors", "parsing", "gap_analyzer",
    "copilot", "rag", "exchange", "llm", "mcp_server",
}
_ALLOWED_DB = {"db.client", "db.org_store"}
_ALLOWED_API = {"api.middleware.auth", "api.models.scope3_schemas"}


def _scope3_files() -> list[Path]:
    files: list[Path] = []
    for d in _SCAN_DIRS:
        files += (_ROOT / d).rglob("*.py")
    for g in _SCAN_GLOBS:
        files += _ROOT.glob(g)
    return [f for f in files if "__pycache__" not in f.parts]


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    mods: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            mods.add(node.module)
    return mods


def _violation(module: str) -> str | None:
    top = module.split(".")[0]
    if top in _FORBIDDEN_BUSINESS:
        return f"shared business module '{module}'"
    if top.startswith("s1_") or top.startswith("s2_"):
        return f"sibling scope '{module}'"
    if top == "db":
        if module in _ALLOWED_DB or module.startswith("db.s3_"):
            return None
        return f"non-allowed db import '{module}'"
    if top == "api":
        if module in _ALLOWED_API:
            return None
        return f"non-allowed api import '{module}'"
    return None  # stdlib / third-party / own s3_* — fine


def test_scope3_is_isolated():
    offenders: list[str] = []
    files = _scope3_files()
    assert files, "no Scope-3 files found to lint"
    for f in files:
        for module in sorted(_imported_modules(f)):
            problem = _violation(module)
            if problem:
                offenders.append(f"{f.relative_to(_ROOT)} imports {problem}")
    assert not offenders, "Scope-3 isolation violations:\n  " + "\n  ".join(offenders)
