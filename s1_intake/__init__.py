"""Scope 1 activity-data intake (isolated).

Phase 1: pure CSV bulk-intake parsing. Bayou utility connect and Vision-LLM OCR
land here in Phase 2. See research/2.3.
"""

from s1_intake.csv_intake import IntakeRow, ParsedIntake, parse_intake_csv

__all__ = ["IntakeRow", "ParsedIntake", "parse_intake_csv"]
