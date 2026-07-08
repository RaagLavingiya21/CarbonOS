"""Bayou Energy utility-bill parsing (Phase 2).

Bayou's PDF bill-upload API runs trained parsers over US gas bills, returning
validated therms/CCF (Tier-2 data quality). We submit a bill, poll for the
parsed result, and feed it into the same OCR review queue as our Claude
extractor. The HTTP layer is isolated + injectable so the mapping/pipeline is
unit-testable without a live key. See research/2.3 section B1.
"""

from s1_intake.bayou.client import BayouBill, BayouClient, BayouError
from s1_intake.bayou.mapping import BAYOU_CONFIDENCE, bayou_bill_to_extraction
from s1_intake.bayou.sync import PulledBill, PullResult, pull_parsed_extractions

__all__ = [
    "BAYOU_CONFIDENCE",
    "BayouBill",
    "BayouClient",
    "BayouError",
    "PullResult",
    "PulledBill",
    "bayou_bill_to_extraction",
    "pull_parsed_extractions",
]
