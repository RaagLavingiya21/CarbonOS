"""Driver & obligation front door (Epic C) — pure-logic obligation engine.

Diagnoses which regulatory/customer drivers actually bite for a company profile
and what is due when. DB-free and unit-testable; the API/persistence layer
(Epic C A-phases) wraps this. Rules live as dated, versioned data in
data/obligation_rules/ — never hardcoded — per the Epic C plan.
"""
