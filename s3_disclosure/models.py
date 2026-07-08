"""Dataclasses for Scope-3 disclosure datapoint mapping (Epic G). DB-free."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DisclosureDatapoint:
    key: str
    label: str
    value: float | None  # numeric value (looked up), or None for narrative/missing
    text: str | None  # narrative value (e.g. methodology), or None
    unit: str
    source_ref: str | None  # provenance for numeric values; None for narrative
    flag: str = "ok"  # ok | missing


@dataclass
class DisclosureResult:
    framework: str
    format_version: str
    is_provisional: bool
    datapoints: list[DisclosureDatapoint] = field(default_factory=list)
    category_breakdown: list[DisclosureDatapoint] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
