"""Cascade-exposure detection (Epic C / unit P.1.4.b).

The research's "novel differentiated signal": a company that is not directly
regulated is still EXPOSED if it sells to a customer who *is* regulated, because
that customer cascades a Scope 3 data request downstream. Given a profile's
`key_customers`, match them against a curated, dated regulated-buyer list and
surface the exposure + which regime drives it.

Pure logic, deterministic, DB-free. MVP uses a maintained list; external
obligation enrichment (D&B / filings) is a later BUY per the build-vs-buy call.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from s3_obligations.models import ObligationProfile

_BUYERS_PATH = Path(__file__).parent / "data" / "regulated_buyers.yaml"


@dataclass
class CascadeSignal:
    customer: str  # the key_customer as the company named it
    matched_buyer: str  # canonical buyer name from the list
    regimes: list[str] = field(default_factory=list)
    rationale: str = ""
    source: str = "curated-list"  # provenance (vs. future external enrichment)


@functools.lru_cache(maxsize=4)
def _load_buyers(version: str = "v2026-07") -> list[dict]:
    data = yaml.safe_load(_BUYERS_PATH.read_text())
    if not isinstance(data, dict) or "buyers" not in data:
        raise ValueError("regulated_buyers.yaml missing 'buyers'.")
    return data["buyers"]


def detect_cascade(profile: ObligationProfile, version: str = "v2026-07") -> list[CascadeSignal]:
    """Return one CascadeSignal per key_customer that matches a regulated buyer.

    Matching is case-insensitive substring against each buyer's `match` aliases,
    kept specific to avoid false positives. Deterministic ordering (by input).
    """
    buyers = _load_buyers(version)
    signals: list[CascadeSignal] = []
    for raw_customer in profile.key_customers:
        customer = (raw_customer or "").strip()
        if not customer:
            continue
        low = customer.lower()
        for buyer in buyers:
            aliases = [str(a).strip().lower() for a in buyer.get("match", [])]
            if any(alias and alias in low for alias in aliases):
                regimes = list(buyer.get("regimes", []))
                signals.append(
                    CascadeSignal(
                        customer=customer,
                        matched_buyer=buyer["name"],
                        regimes=regimes,
                        rationale=(
                            f"{buyer['name']} is subject to {', '.join(regimes)} and cascades "
                            f"Scope 3 data requests to suppliers. {buyer.get('note', '')}".strip()
                        ),
                    )
                )
                break  # first (most specific) buyer match wins for this customer
    return signals
