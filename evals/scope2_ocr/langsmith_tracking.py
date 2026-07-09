"""Opt-in LangSmith experiment tracking for the OCR calibration runs.

This is an **eval-layer-only** adapter: the production OCR path (`s2_ingestion/ocr.py`)
never imports it, so that code stays LangChain/LangSmith-free. `langsmith` is already
a project dependency but is **lazy-imported inside functions here**, so nothing loads
unless tracking is explicitly enabled.

Enable with env:
    S2_OCR_LANGSMITH=1
    LANGSMITH_API_KEY=ls-...            (the langsmith SDK reads this itself)
    LANGSMITH_PROJECT=scope2-ocr-calibration   (optional; this default otherwise)

When disabled (default) every function here is a safe no-op that imports nothing and
touches no network — which keeps CI fully offline. When enabled, logging is
best-effort: any LangSmith/network error is swallowed with a warning, never raised,
because experiment tracking must not break an eval run. The home-grown `Scorecard`
remains the source of truth; LangSmith is a mirror.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Callable, TypeVar
from uuid import uuid4

logger = logging.getLogger("evals.scope2_ocr.langsmith")

_TRUTHY = {"1", "true", "yes", "on"}

F = TypeVar("F", bound=Callable)


def is_enabled() -> bool:
    """True only when explicitly toggled on *and* an API key is present."""
    flag_on = os.getenv("S2_OCR_LANGSMITH", "").strip().lower() in _TRUTHY
    has_key = bool(os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY"))
    return flag_on and has_key


def _project() -> str:
    return os.getenv("LANGSMITH_PROJECT", "scope2-ocr-calibration")


def traced_extract(fn: F) -> F:
    """Wrap the extraction callable with LangSmith tracing — only when enabled.

    Applied at the *runner* level (never in ocr.py) so each synthetic-bill
    extraction becomes an inspectable run. A no-op passthrough when disabled.
    """
    if not is_enabled():
        return fn
    try:
        from langsmith import traceable

        return traceable(name="extract_bill_document", run_type="llm", project_name=_project())(fn)
    except Exception as exc:  # pragma: no cover - depends on live SDK
        logger.warning("LangSmith tracing unavailable, running untraced: %s", exc)
        return fn


def log_experiment(
    summary: dict,
    *,
    threshold: float,
    metadata: dict | None = None,
) -> None:
    """Record one calibration run (aggregate + per-case metrics + recommended
    threshold) as a LangSmith run. Best-effort; no-op when disabled."""
    if not is_enabled():
        return
    try:  # pragma: no cover - exercised only against the live service
        from langsmith import Client

        client = Client()
        run_id = uuid4()
        now = datetime.now(timezone.utc)
        client.create_run(
            id=run_id,
            name="scope2-ocr-calibration",
            run_type="chain",
            inputs=metadata or {},
            project_name=_project(),
            start_time=now,
        )
        client.update_run(
            run_id,
            outputs={**summary, "recommended_threshold": threshold},
            end_time=datetime.now(timezone.utc),
        )
        # Headline metrics as feedback scores so they're filterable/plottable in the UI.
        for key in ("field_accuracy", "mwh_within_tol_rate", "review_precision", "review_recall"):
            if summary.get(key) is not None:
                client.create_feedback(run_id, key=key, score=float(summary[key]))
        client.create_feedback(run_id, key="recommended_threshold", score=float(threshold))
        logger.info("Logged calibration run to LangSmith project %r", _project())
    except Exception as exc:
        logger.warning("LangSmith experiment logging failed (continuing): %s", exc)


def upload_corpus_dataset(corpus_dir: str, labels: dict[str, dict]) -> None:
    """Create/refresh a LangSmith dataset from the synthetic corpus labels.

    inputs = {"doc": name}, outputs = the expected meters[]. Best-effort; no-op
    when disabled. Idempotent by dataset name.
    """
    if not is_enabled():
        return
    try:  # pragma: no cover - exercised only against the live service
        from langsmith import Client

        client = Client()
        dataset_name = f"scope2-ocr::{os.path.basename(os.path.normpath(corpus_dir))}"
        if client.has_dataset(dataset_name=dataset_name):
            dataset = client.read_dataset(dataset_name=dataset_name)
        else:
            dataset = client.create_dataset(dataset_name=dataset_name)
        for name, label in labels.items():
            client.create_example(
                inputs={"doc": name},
                outputs={"meters": label.get("meters", []), "header": label.get("header", {})},
                dataset_id=dataset.id,
            )
        logger.info("Uploaded %d examples to LangSmith dataset %r", len(labels), dataset_name)
    except Exception as exc:
        logger.warning("LangSmith dataset upload failed (continuing): %s", exc)


__all__ = ["is_enabled", "traced_extract", "log_experiment", "upload_corpus_dataset"]
