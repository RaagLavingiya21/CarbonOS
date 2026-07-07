"""Scope 1 activity-data intake (isolated).

Phase 1: pure CSV bulk-intake parsing. Bayou utility connect and Vision-LLM OCR
land here in Phase 2. See research/2.3.
"""

from s1_intake.base_year import BaseYearImport, parse_base_year_csv
from s1_intake.csv_intake import IntakeRow, ParsedIntake, parse_intake_csv

__all__ = [
    "BaseYearImport",
    "IntakeRow",
    "ParsedIntake",
    "parse_base_year_csv",
    "parse_intake_csv",
]
