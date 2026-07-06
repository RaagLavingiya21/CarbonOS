"""Scope 2 dual-method calculation engine (PRD 5.4).

Computes and stores two distinct, labeled totals per site and rolled up per
entity/period: location-based (grid-average factor) and market-based (contractual
instruments via the sourcing hierarchy, residual mix for uncovered load). The two
totals are never merged or averaged. Depends on s2_factors and s2_sites only.
No UI or cross-scope imports.
"""
