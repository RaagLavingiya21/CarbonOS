from __future__ import annotations

import pytest

from copilot.parse_response import _parse_structured


def test_parse_structured_extracts_primary_kg_co2e_when_complete() -> None:
    text = """Supplier provided cradle-to-gate emissions for the cotton body panel.

```json
{
  "response_type": "data_submission",
  "data_provided": "Supplier reported 12.5 kg CO2e cradle-to-gate for the cotton body.",
  "issues_identified": [],
  "completeness_score": "complete",
  "primary_kg_co2e": 12.5
}
```"""
    parsed = _parse_structured(text)
    assert parsed is not None
    assert parsed.primary_kg_co2e == pytest.approx(12.5)


def test_parse_structured_ignores_primary_kg_co2e_when_not_complete() -> None:
    text = """```json
{
  "response_type": "partial",
  "data_provided": "Supplier mentioned a number but no boundary.",
  "issues_identified": ["missing_fields"],
  "completeness_score": "partial",
  "primary_kg_co2e": 12.5
}
```"""
    parsed = _parse_structured(text)
    assert parsed is not None
    assert parsed.primary_kg_co2e is None
