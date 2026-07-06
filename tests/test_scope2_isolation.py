"""Isolation guardrail for the Scope 2 module (SCOPE2_IMPLEMENTATION_PLAN.md Section 8).

Fails the build if any Scope 2 file (business modules, routers, stores, schemas)
imports a Carbon OS (Scope 3 / PACT) business module or a non-shared db store.
Scope 2 may only reuse shared *infrastructure* — api.middleware.auth, db.client,
db.org_store (tenancy) — and its own db.s2_* stores; never Carbon OS domain logic.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Business-logic packages that make up the Scope 2 module.
SCOPE2_DIRS = [
    REPO_ROOT / "s2_ingestion",
    REPO_ROOT / "s2_sites",
    REPO_ROOT / "s2_factors",
    REPO_ROOT / "s2_calc",
    REPO_ROOT / "s2_quality",
    REPO_ROOT / "s2_reporting",
]

# Carbon OS business-logic packages Scope 2 must not import.
FORBIDDEN_TOP_LEVEL = {
    "calc",
    "factors",
    "parsing",
    "gap_analyzer",
    "copilot",
    "rag",
    "exchange",
    "llm",
    "mcp_server",
}

# Sibling scope modules — Scope 2 must stay independent of Scope 1 / Scope 3 too,
# not just Carbon OS. Any import of an s1_*/s3_* package (or db.s1_*/db.s3_* store)
# is a cross-module coupling and fails the build.
FORBIDDEN_SCOPE_PREFIXES = ("s1_", "s3_")

# Shared-infra db modules Scope 2 routes/stores may import (besides db.s2_*).
ALLOWED_DB_SUBMODULES = {"client", "org_store"}


def _scope2_python_files() -> list[Path]:
    files: list[Path] = []
    for directory in SCOPE2_DIRS:
        files.extend(directory.rglob("*.py"))
    files.extend((REPO_ROOT / "api" / "routes").glob("scope2_*.py"))
    files.extend((REPO_ROOT / "db").glob("s2_*_store.py"))
    schema = REPO_ROOT / "api" / "models" / "scope2_schemas.py"
    if schema.exists():
        files.append(schema)
    return [f for f in files if "__pycache__" not in f.parts]


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.add(node.module)
            # `from db import s2_site_store` -> also record `db.s2_site_store`
            for alias in node.names:
                modules.add(f"{node.module}.{alias.name}")
    return modules


def test_scope2_files_exist() -> None:
    assert _scope2_python_files(), "No Scope 2 files found — isolation test is misconfigured."


def test_scope2_does_not_import_carbon_os() -> None:
    violations: list[str] = []
    for path in _scope2_python_files():
        rel = path.relative_to(REPO_ROOT)
        for module in _imported_modules(path):
            parts = module.split(".")
            top = parts[0]
            if top in FORBIDDEN_TOP_LEVEL or top.startswith(FORBIDDEN_SCOPE_PREFIXES):
                violations.append(f"{rel} imports '{module}'")
            elif top == "db" and len(parts) >= 2:
                sub = parts[1]
                if sub.startswith(FORBIDDEN_SCOPE_PREFIXES):
                    violations.append(f"{rel} imports sibling-scope store '{module}'")
                elif sub not in ALLOWED_DB_SUBMODULES and not sub.startswith("s2_"):
                    violations.append(f"{rel} imports non-shared store '{module}'")
    assert not violations, "Scope 2 isolation breached:\n" + "\n".join(violations)
