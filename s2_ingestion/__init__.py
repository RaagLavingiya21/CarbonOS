"""Scope 2 utility-bill ingestion.

Aggregator pull (Arcadia / UtilityAPI-Green Button), CSV bulk import, PDF/OCR
fallback, unit normalization to canonical MWh, and estimated-read / true-up
dedup. Pure business logic: no FastAPI or frontend imports, and no imports from
any Carbon OS (Scope 3 / PACT) module or `s2_*` sibling except leaf utilities.
"""
