"""Scope 2 "one number, many formats" reporting (PRD 5.5).

Prefilled outputs from one dataset: CDP Supply Chain / Climate C6, one major
retail-buyer template (Walmart / Amazon / EcoVadis), and a standard location- vs.
market-based summary export. Buyer/CDP mappings are config/data, not hardcode, so
template drift is a data change. Depends on s2_calc and s2_quality only.
No UI or cross-scope imports.
"""
