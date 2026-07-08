"""Neutral intermediate representation for disclosure documents.

A regime mapper turns a DisclosureData + DisclosureMeta into a `Disclosure` — a
list of titled `Section`s of typed rows. One PDF renderer and one XLSX renderer
turn any `Disclosure` into bytes, so adding a regime is just a small mapper (no
new fpdf2/openpyxl plumbing, no re-solving Latin-1 safety). Pure, DB-free.
"""

from __future__ import annotations

from dataclasses import dataclass, field

Cell = str | int | float
Row = list[Cell]


@dataclass
class Section:
    title: str
    kind: str                        # "keyvalue" | "table" | "note"
    rows: list[Row] = field(default_factory=list)   # table: first row is the header
    emphasize_last: bool = False     # bold the final (total) row of a table
    note: str = ""                   # body text for kind == "note"


@dataclass
class Disclosure:
    regime: str                      # human label, e.g. "ESRS E1"
    doc_title: str                   # PDF H1
    subtitle: str                    # PDF grey subhead, e.g. "ESRS E1-6 · AR5"
    filename_slug: str               # "esrs-e1" | "cdp" | "epa-ghgrp" | "sb253"
    sections: list[Section] = field(default_factory=list)
    # xlsx layout: (sheet_name, [sections on that sheet]); defaults to one sheet per section
    sheet_map: list[tuple[str, list[Section]]] = field(default_factory=list)
