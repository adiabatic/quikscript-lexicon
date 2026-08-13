"""The editor server’s data file, projected from the lexicon like every artifact.

editor/server/payload.json is generated, never hand-edited: it is the JSON object the Desk page inlines — the word set with its frequencies, the TRY letter order, the REP table and the confusion groups — grown by the two lookup maps only the language server reads: the readings that key each spelling to the entries writing it, and the writings that key each Latin word to its spellings. One derivation feeding every consumer is what makes a server that disagrees with lexicon/ a freshness failure rather than a discovery.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from qslex.projection import (
    Lexicon,
    checker,
    crosscheck,
    derive,
    load_records,
    readings,
    writings,
)
from qslex.readlex import repo_root
from qslex.words import load_contractions

EDITOR = "editor"
SERVER = "server"
PAYLOAD = "payload.json"


def build(root: Path | None = None) -> tuple[str, Lexicon]:
    """The payload as the file carries it: one JSON object and one final newline."""
    root = root if root is not None else repo_root()
    records = load_records(root)
    contractions = load_contractions()
    lexicon = derive(records, contractions)
    crosscheck(lexicon, root)
    data = checker(lexicon)
    data["readings"] = readings(records, contractions)
    data["writings"] = writings(records)
    return json.dumps(data, ensure_ascii=False, sort_keys=True) + "\n", lexicon


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Write the editor server’s payload from the lexicon"
    )
    parser.add_argument(
        "--out", type=Path, default=repo_root() / EDITOR / SERVER / PAYLOAD
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="rebuild in memory and fail if what is on disk differs",
    )
    args = parser.parse_args(argv)

    written, lexicon = build()
    if not args.check:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(written, encoding="utf-8", newline="\n")
        print(f"wrote {args.out}")
        print()
        print(f"{len(lexicon.union)} spellings, {len(written.encode('utf-8'))} bytes")
        return 0

    stale = ""
    if not args.out.is_file():
        stale = f"{args.out} is missing"
    elif args.out.read_text(encoding="utf-8") != written:
        stale = f"{args.out} differs from a fresh build"
    if stale:
        print(stale)
        print("\nFAILED: 1 artifact(s) out of date; run `make payload`")
        return 1
    print("OK: 1 artifact matches a fresh build")
    return 0


if __name__ == "__main__":
    sys.exit(main())
