"""Regression guard for the framework-agnostic boundary (AD-2, AD-14).

Two rules, both enforced here so every later epic that adds code under ``services/``
re-verifies them automatically:

1. **No Reflex dependency** — no ``services/`` module may import ``reflex`` (Story 1.1
   AC #6). Keeps ``pytest services/`` runnable without a Reflex app.
2. **One-way dependency direction** — no ``services/`` module may import the UI/app
   layer (``finance_app``). The allowed direction is UI -> Service -> Data; a
   ``services/`` -> ``finance_app`` import reverses it and re-couples business logic to
   the app (AD-2).

Together these are what make the Phase 2 FastAPI extraction a re-skin, not a rewrite.

Detection is AST-based: it flags real ``import X`` / ``from X import ...`` statements
(including ``import reflex as rx``) rather than the string appearing in prose/docstrings.
"""
from __future__ import annotations

import ast
from pathlib import Path

SERVICES_DIR = Path(__file__).resolve().parent.parent / "services"


def _service_py_files() -> list[Path]:
    return sorted(SERVICES_DIR.rglob("*.py"))


def _imported_roots(tree: ast.AST) -> set[str]:
    """Top-level package of every absolute import in the module."""
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom):
            # level > 0 is a relative import (stays inside services/) — not a boundary risk.
            if node.level == 0 and node.module:
                roots.add(node.module.split(".", 1)[0])
    return roots


def _offenders(forbidden_root: str) -> list[str]:
    hits: list[str] = []
    for path in _service_py_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        if forbidden_root in _imported_roots(tree):
            hits.append(str(path.relative_to(SERVICES_DIR.parent)))
    return hits


def test_services_dir_exists() -> None:
    assert SERVICES_DIR.is_dir(), f"services/ package tree missing at {SERVICES_DIR}"


def test_no_reflex_import_in_services() -> None:
    """AC #6: no `services/**` module may import the Reflex framework."""
    offenders = _offenders("reflex")
    assert not offenders, (
        "services/ must stay framework-agnostic (AD-2/AD-14). "
        "These modules import reflex:\n" + "\n".join(offenders)
    )


def test_no_ui_layer_import_in_services() -> None:
    """AD-2 dependency direction: `services/**` may not import the UI layer (finance_app)."""
    offenders = _offenders("finance_app")
    assert not offenders, (
        "services/ must not depend on the UI/app layer (AD-2: UI -> Service -> Data is "
        "one-way). These modules import finance_app:\n" + "\n".join(offenders)
    )


def _full_dotted_imports(tree: ast.AST) -> set[str]:
    """Every absolute import's *full* dotted path (unlike `_imported_roots`, which truncates
    to the top-level package -- too coarse to distinguish `services.engine` from a sibling
    like `services.utils`, both of which share the `services` root)."""
    paths: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                paths.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                paths.add(node.module)
    return paths


def test_no_engine_import_in_narrate() -> None:
    """AD-1 engine/narrate hard boundary: `services/narrate/**` may not import
    `services/engine/` (or any of its submodules) -- the evidence pack arrives as an argument,
    never as an import. Scoped to `services/narrate/` only: that package legitimately imports
    sibling `services.utils`, which a root-level check (`_offenders`) can't distinguish from
    `services.engine` since both share the `services` top-level root."""
    narrate_dir = SERVICES_DIR / "narrate"
    offenders: list[str] = []
    for path in sorted(narrate_dir.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imports = _full_dotted_imports(tree)
        if any(imp == "services.engine" or imp.startswith("services.engine.") for imp in imports):
            offenders.append(str(path.relative_to(SERVICES_DIR.parent)))
    assert not offenders, (
        "services/narrate/ must not import services/engine/ (AD-1: the engine's evidence "
        "pack arrives as a function argument, never as an import). These modules import "
        "services.engine:\n" + "\n".join(offenders)
    )
