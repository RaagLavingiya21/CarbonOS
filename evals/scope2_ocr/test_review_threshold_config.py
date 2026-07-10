"""REVIEW_THRESHOLD must honor the S2_OCR_REVIEW_THRESHOLD env override.

Calibration (run_calibration.py) recommends a data-driven cutoff; deploying it
should be a config change, not a code change. Reloading the module with the env
set proves the wiring, and the module is restored to its default afterward.
"""

from __future__ import annotations

import importlib

import s2_ingestion.ocr as ocr


def test_default_threshold_is_085(monkeypatch) -> None:
    monkeypatch.delenv("S2_OCR_REVIEW_THRESHOLD", raising=False)
    importlib.reload(ocr)
    try:
        assert ocr.REVIEW_THRESHOLD == 0.85
    finally:
        importlib.reload(ocr)


def test_env_overrides_threshold(monkeypatch) -> None:
    monkeypatch.setenv("S2_OCR_REVIEW_THRESHOLD", "0.7")
    importlib.reload(ocr)
    try:
        assert ocr.REVIEW_THRESHOLD == 0.7
    finally:
        monkeypatch.delenv("S2_OCR_REVIEW_THRESHOLD", raising=False)
        importlib.reload(ocr)  # restore the default for other tests
