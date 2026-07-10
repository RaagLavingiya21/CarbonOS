"""Bayou credential-connect auto-pull (Option A) — orchestration.

Given a Bayou client already carrying the org's API key, list the account's
bills and map each *parsed* bill onto the shared OCR review-queue extraction
shape. This is the pure, DB-free half of the sync: the caller (route) persists
the returned extractions into the org's OCR queue (same path as the manual
Bayou upload), where a reviewer assigns the source and finalizes -> calc.

PDF download + parsing happen on Bayou's side (the client only lists already-
parsed bills), so there is no local PDF fetch to mock — tests inject the
client's transport to simulate Bayou's `/bills` response.
"""

from __future__ import annotations

from dataclasses import dataclass

from s1_intake.bayou.client import BayouBill, BayouClient
from s1_intake.bayou.mapping import bayou_bill_to_extraction
from s1_intake.ocr.models import Extraction


@dataclass(frozen=True)
class PulledBill:
    bill: BayouBill
    extraction: Extraction


@dataclass(frozen=True)
class PullResult:
    fetched: int                 # bills returned by Bayou
    parsed: list[PulledBill]     # the subset ready to ingest

    @property
    def parsed_count(self) -> int:
        return len(self.parsed)


def pull_parsed_extractions(client: BayouClient) -> PullResult:
    """List the account's bills and map every parsed one to an Extraction.

    Bills still parsing (locked) or failed (unsupported) are skipped — they'll be
    picked up on a later sync once Bayou finishes unlocking them.
    """
    bills = client.list_bills()
    parsed = [
        PulledBill(bill=b, extraction=bayou_bill_to_extraction(b))
        for b in bills
        if b.status == "parsed"
    ]
    return PullResult(fetched=len(bills), parsed=parsed)
