"""Deterministic tests for the synthetic bill generator (no API)."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from evals.scope2_ocr.synthetic import (
    DIFFICULTIES,
    BillSpec,
    MeterSpec,
    generate_bill,
)
from s2_ingestion.normalize import normalize_to_mwh

_SPEC = BillSpec(
    utility_name="PG&E",
    account_number="1234567",
    service_address="1 Main St, San Francisco, CA",
    meters=[
        MeterSpec("electricity", "2025-01-01", "2025-01-31", 1500, "kWh", total_cost_usd=210.5),
        MeterSpec(
            "natural_gas", "2025-01-01", "2025-01-31", 1080, "therms", is_estimated_read=True
        ),
    ],
)


@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_generation_is_deterministic(difficulty: str) -> None:
    a = generate_bill(_SPEC, difficulty=difficulty, seed=7).png_bytes
    b = generate_bill(_SPEC, difficulty=difficulty, seed=7).png_bytes
    assert a == b


@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_png_decodes_and_is_nontrivial(difficulty: str) -> None:
    bill = generate_bill(_SPEC, difficulty=difficulty, seed=1)
    assert bill.content_type == "image/png"
    img = Image.open(io.BytesIO(bill.png_bytes))
    img.load()
    assert img.size == (1000, 1400)
    assert len(bill.png_bytes) > 2000


def test_auto_label_canonical_mwh_matches_normalizer() -> None:
    """The label's canonical_mwh must come from the real converter, not hand math."""
    bill = generate_bill(_SPEC, difficulty="clean", seed=0)
    meters = bill.label["meters"]
    assert meters[0]["canonical_mwh"] == normalize_to_mwh(1500, "kWh").canonical_mwh
    assert meters[1]["canonical_mwh"] == normalize_to_mwh(1080, "therms").canonical_mwh
    # Header + carriers round-trip into the label unchanged.
    assert bill.label["header"]["utility_name"] == "PG&E"
    assert [m["energy_carrier"] for m in meters] == ["electricity", "natural_gas"]
    assert meters[1]["is_estimated_read"] is True


def test_difficulty_tiers_produce_distinct_images() -> None:
    clean = generate_bill(_SPEC, difficulty="clean", seed=5).png_bytes
    moderate = generate_bill(_SPEC, difficulty="moderate", seed=5).png_bytes
    hard = generate_bill(_SPEC, difficulty="hard", seed=5).png_bytes
    assert clean != moderate != hard
    assert clean != hard


def test_seed_changes_degraded_output() -> None:
    a = generate_bill(_SPEC, difficulty="hard", seed=1).png_bytes
    b = generate_bill(_SPEC, difficulty="hard", seed=2).png_bytes
    assert a != b


def test_unknown_difficulty_rejected() -> None:
    with pytest.raises(ValueError):
        generate_bill(_SPEC, difficulty="blurry", seed=0)
