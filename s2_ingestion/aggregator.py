"""Utility-data aggregator adapter — provider-agnostic pull (PRD 5.1).

Most utilities that aren't hand-entered arrive through an aggregator (Arcadia,
UtilityAPI / Green Button). Which one a customer needs depends on their utilities,
so this module fixes the *shape* of the integration without binding a vendor:

  - `RawUtilityAccount` / `RawBill` — the provider-neutral records every adapter
    must return (roughly the Green Button intersection).
  - `AggregatorProvider` — the interface a concrete adapter implements.
  - `map_raw_bill` — pure: a RawBill + resolved account_id -> the bill-row dict
    `s2_bill_store.insert_bills` persists, unit-normalized to canonical MWh and
    labelled `ingestion_method='aggregator'`. Estimated reads and cost-only rows
    are flagged the same way the CSV path flags them, so true-up dedup applies.
  - `FakeAggregatorProvider` — a deterministic in-memory adapter for tests and
    local dev; the seam a real Arcadia/UtilityAPI client slots into later.
  - `get_provider` — registry that raises for any provider not yet wired, so an
    un-chosen vendor fails loud instead of silently no-op'ing.

Pure business logic: imports only the s2_ingestion.normalize leaf.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Protocol

from s2_ingestion.normalize import UnitConversionError, normalize_to_mwh


@dataclass(frozen=True)
class RawUtilityAccount:
    """A provider's view of one utility account, before it maps to s2_utility_accounts."""

    provider_account_ref: str  # the provider's stable id for this account
    utility_name: str | None = None
    account_number: str | None = None
    service_address: str | None = None
    energy_carrier: str = "electricity"


@dataclass(frozen=True)
class RawBill:
    """A provider's view of one billing period. Quantity absent -> cost-only."""

    provider_account_ref: str
    period_start: date
    period_end: date
    quantity: float | None
    unit: str | None
    cost_usd: float | None = None
    is_estimated_read: bool = False
    provider_record_ref: str | None = None  # for idempotency / audit


class AggregatorProvider(Protocol):
    """The seam a concrete Arcadia / UtilityAPI adapter implements.

    `connection_ref` is whatever the provider uses to scope a customer's data (an
    OAuth grant id, a UtilityAPI authorization uid, etc.). Implementations own auth
    and paging; callers see only the neutral records above.
    """

    name: str

    def fetch_accounts(self, connection_ref: str) -> list[RawUtilityAccount]: ...

    def fetch_bills(
        self, provider_account_ref: str, *, start: date, end: date
    ) -> list[RawBill]: ...


class AggregatorError(RuntimeError):
    """Raised for provider/config failures (unknown provider, auth, transport)."""


def map_raw_bill(raw: RawBill, account_id: int) -> dict:
    """Pure: RawBill + account_id -> a bill row for s2_bill_store.insert_bills.

    Mirrors the CSV commit row shape so both ingestion paths land identical bills
    (and feed the same true-up dedup). Cost-only rows (no quantity) carry no MWh;
    a bad unit raises UnitConversionError, same as CSV.
    """
    is_cost_only = raw.quantity is None or raw.quantity == 0.0
    canonical_mwh: float | None = None
    conversion_note: str | None = None
    if not is_cost_only:
        if not raw.unit:
            raise UnitConversionError("Quantity present but unit is missing.")
        normalized = normalize_to_mwh(raw.quantity, raw.unit)
        canonical_mwh = normalized.canonical_mwh
        conversion_note = normalized.conversion_note
    return {
        "account_id": account_id,
        "period_start": raw.period_start.isoformat(),
        "period_end": raw.period_end.isoformat(),
        "raw_quantity": raw.quantity,
        "raw_unit": raw.unit,
        "canonical_mwh": canonical_mwh,
        "cost_usd": raw.cost_usd,
        "is_estimated_read": raw.is_estimated_read,
        "is_cost_only": is_cost_only,
        "conversion_note": conversion_note,
        "ingestion_method": "aggregator",
        "source_ref": raw.provider_record_ref,
    }


@dataclass
class FakeAggregatorProvider:
    """Deterministic in-memory adapter for tests and local dev.

    Seed it with accounts and bills keyed by connection/account ref; it just serves
    them back (filtered by date), standing in for a real provider client.
    """

    name: str = "fake"
    accounts: dict[str, list[RawUtilityAccount]] = field(default_factory=dict)
    bills: dict[str, list[RawBill]] = field(default_factory=dict)

    def fetch_accounts(self, connection_ref: str) -> list[RawUtilityAccount]:
        return list(self.accounts.get(connection_ref, []))

    def fetch_bills(
        self, provider_account_ref: str, *, start: date, end: date
    ) -> list[RawBill]:
        return [
            bill
            for bill in self.bills.get(provider_account_ref, [])
            if bill.period_end >= start and bill.period_start <= end
        ]


# Provider registry. Real vendors are added here once a design partner's utilities
# fix the choice (see SCOPE2_STATUS.md §7); until then only the fake is registered.
_PROVIDERS: dict[str, AggregatorProvider] = {}


def register_provider(provider: AggregatorProvider) -> None:
    _PROVIDERS[provider.name] = provider


def get_provider(name: str) -> AggregatorProvider:
    """Return a registered provider, or raise — an un-wired vendor never no-ops."""
    try:
        return _PROVIDERS[name]
    except KeyError:
        raise AggregatorError(
            f"Aggregator provider '{name}' is not configured. "
            f"Available: {sorted(_PROVIDERS) or '(none wired yet)'}."
        ) from None


__all__ = [
    "RawUtilityAccount",
    "RawBill",
    "AggregatorProvider",
    "AggregatorError",
    "map_raw_bill",
    "FakeAggregatorProvider",
    "register_provider",
    "get_provider",
]
