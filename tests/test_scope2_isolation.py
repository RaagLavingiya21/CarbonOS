"""Isolation guardrail for the Scope 2 module (SCOPE2_IMPLEMENTATION_PLAN.md Section 8).

Fails the build if any Scope 2 file imports a Carbon OS (Scope 3 / PACT) business
module or a non-s2 db store. Scope 2 may only reuse shared *infrastructure*
(api.middleware.auth, db.client) — never Carbon OS domain logic or data.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Directories/files that make up the Scope 2 module.
SCOPE2_DIRS = [
    REPO_ROOT / "s2_ingestion",
    REPO_ROOT / "s2_sites",
    REPO_ROOT / "s2_factors",
    REPO_ROOT / "s2_calc",
    REPO_ROOT / "s2_quality",
    REPO_ROOT / "s2_reporting",
]
SCOPE2_EXTRA_FILES = [
    REPO_ROOT / "api" / "models" / "scope2_schemas.py",
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

# Shared infrastructure that IS allowed from the db package.
ALLOWED_DB_MODULES = {"db.client"}


def _scope2_python_files() -> list[Path]:
    files: list[Path] = []
    for directory in SCOPE2_DIRS:
        files.extend(directory.rglob("*.py"))
    files.extend(f for f in SCOPE2_EXTRA_FILES if f.exists())
    return [f for f in files if "__pycache__" not in f.parts]


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.add(node.module)
    return modules


def test_scope2_files_exist() -> None:
    assert _scope2_python_files(), "No Scope 2 files found — isolation test is misconfigured."


def test_scope2_does_not_import_carbon_os() -> None:
    violations: list[str] = []
    for path in _scope2_python_files():
        for module in _imported_modules(path):
            top = module.split(".")[0]
            if top in FORBIDDEN_TOP_LEVEL:
                violations.append(f"{path.relative_to(REPO_ROOT)} imports '{module}'")
            if top == "db" and module not in ALLOWED_DB_MODULES:
                violations.append(
                    f"{path.relative_to(REPO_ROOT)} imports non-shared store '{module}'"
                )
    assert not violations, "Scope 2 isolation breached:\n" + "\n".join(violations)
