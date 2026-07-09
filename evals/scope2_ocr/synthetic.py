"""Synthetic utility-bill generator for the Scope 2 OCR eval corpus.

The eval harness (`harness.py` / `scoring.py`) already exists but had nothing to
run on: real bills are scarce, PII-laden, and copyrighted. This module renders
*synthetic* bills as images with Pillow, from known values, so we get:

  - perfect, auto-generated ground truth (no hand-labeling),
  - a committable, license-clean corpus,
  - **controlled difficulty** (clean / moderate / hard) so REVIEW_THRESHOLD is
    calibrated against a spread of legibility, not just pristine documents.

`generate_bill(spec, difficulty=..., seed=...)` returns the PNG bytes plus the
exact `labels/{name}.json` dict the harness expects. `canonical_mwh` in the label
is computed with the real `normalize_to_mwh` (single source of truth — never hand
math), so a generated bill is scored against the same conversion the pipeline uses.

Determinism: identical (spec, difficulty, seed) → byte-identical PNG, so tests and
CI corpora are reproducible.
"""

from __future__ import annotations

import io
import random
from dataclasses import dataclass, field

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from s2_ingestion.normalize import normalize_to_mwh

CONTENT_TYPE = "image/png"
DIFFICULTIES = ("clean", "moderate", "hard")

# Display labels for the canonical carrier codes stored in the label.
_CARRIER_DISPLAY = {
    "electricity": "Electricity",
    "natural_gas": "Natural Gas",
    "steam": "Steam",
}

_WIDTH, _HEIGHT = 1000, 1400
_MARGIN = 60


@dataclass(frozen=True)
class MeterSpec:
    """One metered line item on the bill."""

    energy_carrier: str  # canonical: "electricity" | "natural_gas" | ...
    service_period_start: str  # ISO "YYYY-MM-DD"
    service_period_end: str
    consumption_quantity: float
    consumption_unit: str  # printed as-is: "kWh" | "therms" | "MMBtu" | ...
    is_estimated_read: bool = False
    meter_number: str | None = None
    demand_kw: float | None = None
    total_cost_usd: float | None = None


@dataclass(frozen=True)
class BillSpec:
    """A whole synthetic bill: header + one or more meters."""

    utility_name: str
    account_number: str
    service_address: str
    meters: list[MeterSpec] = field(default_factory=list)


@dataclass(frozen=True)
class GeneratedBill:
    """Output of the generator: image bytes + the harness-shaped ground-truth label."""

    name: str
    png_bytes: bytes
    content_type: str
    label: dict
    difficulty: str


# --- fonts -----------------------------------------------------------------


def _font(size: int) -> ImageFont.ImageFont:
    """A legible font at `size`, degrading gracefully across Pillow builds."""
    for name in ("DejaVuSans.ttf", "Arial.ttf", "Helvetica.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    try:  # Pillow >= 10.1 supports a scalable default.
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


# --- label construction ----------------------------------------------------


def _meter_label(meter: MeterSpec) -> dict:
    """The label meters[] entry, with canonical_mwh from the real converter."""
    canonical_mwh = normalize_to_mwh(
        meter.consumption_quantity, meter.consumption_unit
    ).canonical_mwh
    return {
        "energy_carrier": meter.energy_carrier,
        "service_period_start": meter.service_period_start,
        "service_period_end": meter.service_period_end,
        "consumption_quantity": meter.consumption_quantity,
        "consumption_unit": meter.consumption_unit,
        "canonical_mwh": canonical_mwh,
        "is_estimated_read": meter.is_estimated_read,
    }


def build_label(spec: BillSpec, *, name: str, difficulty: str) -> dict:
    """The ground-truth `labels/{name}.json` dict for a spec."""
    return {
        "doc": name,
        "notes": f"Synthetic {difficulty} bill ({len(spec.meters)} meter(s)).",
        "header": {
            "utility_name": spec.utility_name,
            "account_number": spec.account_number,
            "service_address": spec.service_address,
        },
        "meters": [_meter_label(m) for m in spec.meters],
    }


# --- rendering -------------------------------------------------------------


def _render_clean(spec: BillSpec) -> Image.Image:
    """Draw a crisp, high-contrast bill before any difficulty degradation."""
    img = Image.new("RGB", (_WIDTH, _HEIGHT), "white")
    draw = ImageDraw.Draw(img)
    title = _font(40)
    label = _font(24)
    body = _font(26)

    y = _MARGIN
    draw.text((_MARGIN, y), spec.utility_name, fill="black", font=title)
    y += 60
    draw.text((_MARGIN, y), "Utility Statement", fill="black", font=label)
    y += 50
    draw.line([(_MARGIN, y), (_WIDTH - _MARGIN, y)], fill="black", width=2)
    y += 24

    draw.text((_MARGIN, y), f"Account Number: {spec.account_number}", fill="black", font=body)
    y += 40
    draw.text((_MARGIN, y), f"Service Address: {spec.service_address}", fill="black", font=body)
    y += 56

    for i, meter in enumerate(spec.meters, start=1):
        draw.line([(_MARGIN, y), (_WIDTH - _MARGIN, y)], fill="gray", width=1)
        y += 20
        carrier = _CARRIER_DISPLAY.get(meter.energy_carrier, meter.energy_carrier)
        mtr = meter.meter_number or f"MTR-{100 + i}"
        draw.text((_MARGIN, y), f"Meter {mtr}  —  {carrier}", fill="black", font=body)
        y += 40
        draw.text(
            (_MARGIN, y),
            f"Service Period: {meter.service_period_start} to {meter.service_period_end}",
            fill="black",
            font=body,
        )
        y += 40
        draw.text(
            (_MARGIN, y),
            f"Consumption: {meter.consumption_quantity:g} {meter.consumption_unit}",
            fill="black",
            font=body,
        )
        y += 40
        read_type = "Estimated" if meter.is_estimated_read else "Actual"
        draw.text((_MARGIN, y), f"Read Type: {read_type}", fill="black", font=body)
        y += 40
        if meter.demand_kw is not None:
            draw.text((_MARGIN, y), f"Demand: {meter.demand_kw:g} kW", fill="black", font=body)
            y += 40
        if meter.total_cost_usd is not None:
            draw.text((_MARGIN, y), f"Amount: ${meter.total_cost_usd:.2f}", fill="black", font=body)
            y += 40
        y += 16

    return img


def _seeded_noise(seed: int) -> Image.Image:
    """A deterministic full-frame RGB noise image (seed-reproducible).

    Generated at low resolution from a seeded RNG then upscaled — fast, and unlike
    `Image.effect_noise` it is reproducible (that helper uses an unseeded source).
    """
    w, h = _WIDTH // 5, _HEIGHT // 5
    data = random.Random(seed).randbytes(w * h)
    tile = Image.frombytes("L", (w, h), data)
    return tile.resize((_WIDTH, _HEIGHT), Image.BILINEAR).convert("RGB")


def _degrade(img: Image.Image, difficulty: str, seed: int) -> Image.Image:
    """Apply deterministic, seed-controlled legibility degradation."""
    if difficulty == "clean":
        return img

    # Seed-derived, bounded parameters (kept legible on purpose).
    r = (seed * 2654435761) % (2**32)  # cheap deterministic spread
    angle_sign = 1 if (r & 1) else -1

    if difficulty == "moderate":
        img = img.rotate(angle_sign * 2.0, resample=Image.BICUBIC, fillcolor="white")
        return img.filter(ImageFilter.GaussianBlur(radius=0.6))

    if difficulty == "hard":
        # Simulate a low-res phone photo: downscale then upscale, fade, rotate, blur, noise.
        small = img.resize((int(_WIDTH * 0.55), int(_HEIGHT * 0.55)), Image.BILINEAR)
        img = small.resize((_WIDTH, _HEIGHT), Image.BILINEAR)
        img = ImageEnhance.Contrast(img).enhance(0.72)
        img = img.rotate(angle_sign * 4.0, resample=Image.BICUBIC, fillcolor="white")
        img = img.filter(ImageFilter.GaussianBlur(radius=1.0))
        return Image.blend(img, _seeded_noise(seed), alpha=0.12)

    raise ValueError(f"Unknown difficulty '{difficulty}'. Expected one of {DIFFICULTIES}.")


def generate_bill(
    spec: BillSpec,
    *,
    difficulty: str = "clean",
    seed: int = 0,
    name: str = "synthetic",
) -> GeneratedBill:
    """Render a synthetic bill image and its ground-truth label.

    Deterministic: identical (spec, difficulty, seed) → identical PNG bytes.
    """
    if difficulty not in DIFFICULTIES:
        raise ValueError(f"Unknown difficulty '{difficulty}'. Expected one of {DIFFICULTIES}.")
    img = _degrade(_render_clean(spec), difficulty, seed)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return GeneratedBill(
        name=name,
        png_bytes=buf.getvalue(),
        content_type=CONTENT_TYPE,
        label=build_label(spec, name=name, difficulty=difficulty),
        difficulty=difficulty,
    )


__all__ = [
    "CONTENT_TYPE",
    "DIFFICULTIES",
    "BillSpec",
    "MeterSpec",
    "GeneratedBill",
    "build_label",
    "generate_bill",
]
