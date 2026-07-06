"""Scope 2 grid emission-factor library, versioned (PRD 5.4).

eGRID (US subregions), IEA (countries), Green-e (US) and AIB (EU) residual mix,
and steam/heat factors. Each factor is pinned to a vintage year so a reporting
period always resolves to the factor set in effect for it, and historical
restatements never break on an annual refresh. Pure business logic; no UI or
cross-scope imports.
"""
