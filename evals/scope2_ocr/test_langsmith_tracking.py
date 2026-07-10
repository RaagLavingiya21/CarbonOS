"""The opt-in LangSmith adapter must be a safe, offline no-op when disabled.

This guards the CI-offline guarantee: with the env unset, no LangSmith import
happens, no network is touched, and no call raises. The enabled path talks to a
live service and is not exercised here.
"""

from __future__ import annotations

from evals.scope2_ocr import langsmith_tracking as ls


def test_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("S2_OCR_LANGSMITH", raising=False)
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
    assert ls.is_enabled() is False


def test_flag_on_but_no_key_stays_disabled(monkeypatch) -> None:
    monkeypatch.setenv("S2_OCR_LANGSMITH", "1")
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
    assert ls.is_enabled() is False


def test_all_calls_are_noops_when_disabled(monkeypatch) -> None:
    monkeypatch.delenv("S2_OCR_LANGSMITH", raising=False)
    # traced_extract returns the original callable unchanged.
    assert ls.traced_extract(len) is len
    # log_experiment / upload_corpus_dataset return None and never raise.
    assert ls.log_experiment({"review_recall": 1.0}, threshold=0.85) is None
    assert ls.upload_corpus_dataset("/tmp/nope", {"a": {"meters": []}}) is None
