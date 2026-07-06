"""s3_factors — vendored CEDA emission-factor engine for the Scope-3 module.

`ef_lookup.py` and `material_mapping.py` are self-contained COPIES of the PCF
product's `factors/` equivalents, vendored here so the Scope-3 module does not
import the shared `factors` business module (hygiene rule 6 — see
tests/test_s3_isolation.py). Kept close to upstream to ease periodic re-sync;
the only edit vs. upstream is the intra-package import path. They read the same
shared reference workbook (data/Open CEDA 2025 …xlsx), which is read-only data,
not a code dependency.
"""
