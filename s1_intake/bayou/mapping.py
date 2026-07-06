"""Map a parsed Bayou bill onto the shared OCR review-queue field shape.

Bayou returns validated, trained-parser data, so fields carry a high confidence
(Tier-2). Field names match the Claude utility-bill schema so the review UI and
the apply path are identical regardless of which parser produced the row.
"""

from __future__ import annotations

from s1_intake.bayou.client import BayouBill
from s1_intake.ocr.models import ExtractedField, Extraction

BAYOU_CONFIDENCE = 0.95   # trained parser, validated against bill totals (Tier 2)


def _field(value) -> ExtractedField:
    populated = value not in (None, "")
    return ExtractedField(
        value=str(value) if populated else None,
        confidence=BAYOU_CONFIDENCE if populated else 0.0,
    )


def bayou_bill_to_extraction(bill: BayouBill) -> Extraction:
    fields = {
        "consumption_quantity": _field(bill.gas_consumption),
        "consumption_unit": _field(bill.gas_consumption_unit),
        "billing_period_start": _field(bill.billing_period_from),
        "billing_period_end": _field(bill.billing_period_to),
        "total_cost": _field(bill.gas_amount),
        "account_number": _field(bill.account_number),
    }
    return Extraction(doc_kind="utility_bill", fields=fields, model="bayou")
