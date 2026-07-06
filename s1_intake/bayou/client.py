"""Thin Bayou Energy API client (PDF bill-upload + parse).

Endpoint paths, Basic-auth scheme, and field names follow Bayou's public docs
(research/2.3); the exact request/response shape is isolated in `_http_request`
and `_parse_bill` and must be confirmed against a Bayou sandbox key before going
live. `request` is injectable so tests exercise the client without a real call.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable

BAYOU_BASE_URL = "https://bayou.energy/api/v2"

# Bill "status" values: gas data is available once the bill is unlocked.
_PARSED_STATUSES = {"unlocked", "unlocked_for_gas", "unlocked_for_electric"}
_FAILED_STATUSES = {"not_supported"}


class BayouError(RuntimeError):
    """Bayou API misconfiguration or request failure."""


@dataclass
class BayouBill:
    bill_id: str
    status: str                              # parsing | parsed | failed
    gas_consumption: float | None = None
    gas_consumption_unit: str | None = None  # therms | ccf
    billing_period_from: str | None = None
    billing_period_to: str | None = None
    gas_amount: float | None = None
    account_number: str | None = None
    meter_id: str | None = None


class BayouClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = BAYOU_BASE_URL,
        *,
        request: Callable[..., dict] | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("BAYOU_API_KEY", "")
        self.base_url = base_url.rstrip("/")
        self._request = request or self._http_request

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def submit_bill(self, pdf_bytes: bytes, file_name: str = "bill.pdf") -> str:
        """Upload a bill PDF for parsing. Returns the Bayou bill id."""
        data = self._request(
            "POST", "/bills",
            files={"file": (file_name, pdf_bytes, "application/pdf")},
        )
        bill_id = data.get("id") or data.get("bill_id")
        if not bill_id:
            raise BayouError(f"Bayou did not return a bill id: {data}")
        return str(bill_id)

    def get_bill(self, bill_id: str) -> BayouBill:
        """Fetch the parsed bill (or its in-progress status)."""
        return _parse_bill(bill_id, self._request("GET", f"/bills/{bill_id}"))

    # -- isolated transport (confirm against Bayou docs/sandbox) --------------
    def _http_request(self, method: str, path: str, *, files=None, json=None) -> dict:
        import httpx

        if not self.api_key:
            raise BayouError("BAYOU_API_KEY is not configured.")
        try:
            resp = httpx.request(
                method, f"{self.base_url}{path}",
                auth=(self.api_key, ""),          # Bayou uses the API key as Basic-auth user
                files=files, json=json, timeout=30,
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as exc:
            raise BayouError(f"Bayou request failed: {exc}") from exc


def _num(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_bill(bill_id: str, data: dict) -> BayouBill:
    """Normalize a Bayou bill response (v2 schema) into BayouBill."""
    raw_status = (data.get("status") or "").lower()
    if raw_status in _PARSED_STATUSES:
        status = "parsed"
    elif raw_status in _FAILED_STATUSES:
        status = "failed"
    else:
        status = "parsing"                      # unparsed | locked | partially_unlocked
    meters = data.get("meters") or []
    meter_id = (
        str(meters[0]["id"])
        if meters and isinstance(meters[0], dict) and meters[0].get("id") is not None
        else None
    )
    return BayouBill(
        bill_id=bill_id,
        status=status,
        gas_consumption=_num(data.get("gas_consumption")),
        gas_consumption_unit=data.get("gas_consumption_unit"),
        billing_period_from=data.get("billing_period_from"),
        billing_period_to=data.get("billing_period_to"),
        gas_amount=_num(data.get("gas_amount")),
        account_number=data.get("account_number"),
        meter_id=meter_id,
    )
