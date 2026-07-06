"""Data model for OCR extraction."""

from __future__ import annotations

from dataclasses import dataclass

REVIEW_THRESHOLD = 0.85   # per-field confidence below this routes to human review


@dataclass(frozen=True)
class ExtractedField:
    value: str | None
    confidence: float      # 0.0-1.0


@dataclass
class Extraction:
    doc_kind: str                          # utility_bill | fuel_invoice
    fields: dict[str, ExtractedField]
    model: str = ""
    error: str | None = None

    @property
    def min_confidence(self) -> float:
        """Lowest confidence among populated fields (0.0 if none populated)."""
        populated = [f.confidence for f in self.fields.values() if f.value not in (None, "")]
        return min(populated) if populated else 0.0

    def needs_review(self, threshold: float = REVIEW_THRESHOLD) -> bool:
        return bool(self.error) or not self.fields or self.min_confidence < threshold

    def to_dict(self) -> dict:
        """JSON-serializable form (for the queue row + graph state)."""
        return {
            name: {"value": f.value, "confidence": f.confidence}
            for name, f in self.fields.items()
        }
