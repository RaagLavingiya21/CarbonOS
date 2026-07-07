"""Manual live eval runner — real Claude vision on real (redacted) utility bills.

NOT collected by pytest (costs API calls, non-deterministic). Run it by hand once
you have redacted real bills:

    export ANTHROPIC_API_KEY=...
    python -m evals.scope2_ocr.run_live path/to/docs

`docs/` should contain the bill files plus a matching label per document. A file
`docs/foo.pdf` is scored against `labels/foo.json` (by stem), using the same label
schema as the golden cases (see harness.py docstring). Emits a JSON scorecard to
stdout; redirect it to a file or forward the numbers to LangSmith if you want
run-over-run tracking — the scoring functions are platform-agnostic.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from evals.scope2_ocr.harness import LABELS_DIR, run_live_case
from evals.scope2_ocr.scoring import Scorecard

_CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


def run(docs_dir: Path) -> dict:
    card = Scorecard()
    for doc in sorted(docs_dir.iterdir()):
        content_type = _CONTENT_TYPES.get(doc.suffix.lower())
        if content_type is None:
            continue
        name = doc.stem
        if not (LABELS_DIR / f"{name}.json").exists():
            print(f"skip {doc.name}: no labels/{name}.json", file=sys.stderr)
            continue
        card.add(run_live_case(name, doc.read_bytes(), content_type))
    return card.summary()


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python -m evals.scope2_ocr.run_live <docs_dir>", file=sys.stderr)
        return 2
    docs_dir = Path(sys.argv[1])
    if not docs_dir.is_dir():
        print(f"not a directory: {docs_dir}", file=sys.stderr)
        return 2
    print(json.dumps(run(docs_dir), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
