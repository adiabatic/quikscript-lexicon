"""Builds the editor server’s data file, editor/server/payload.json, from the lexicon.

The file is generated and never edited by hand. It contains the JSON object the Desk page inlines (the word set with its frequencies, the TRY letter order, the REP table and the confusion groups) plus two lookup maps that only the language server reads. `latin_by_spelling` maps each accepted Quikscript spelling to the Latin word, tag and column of each entry with that spelling. `spellings_by_latin` maps each lowercased Latin word to its entries’ tags, frequencies and spelling columns. `make check` runs `python -m qslex.payload --check`, which fails whenever the committed file differs from a rebuild.
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
    latin_by_spelling,
    load_records,
    spellings_by_latin,
)
from qslex.readlex import repo_root
from qslex.words import load_contractions

EDITOR = "editor"
SERVER = "server"
PAYLOAD = "payload.json"


def build(root: Path | None = None) -> tuple[str, Lexicon]:
    """The file’s contents: one JSON object and a final newline."""
    root = root if root is not None else repo_root()
    records = load_records(root)
    contractions = load_contractions()
    lexicon = derive(records, contractions)
    crosscheck(lexicon, root)
    data = checker(lexicon)
    data["latin_by_spelling"] = latin_by_spelling(records, contractions)
    data["spellings_by_latin"] = spellings_by_latin(records)
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
