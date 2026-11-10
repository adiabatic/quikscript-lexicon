"""Builds the Quikscript Lookup page, site/lookup.html, from the lexicon.

site/lookup.html is generated and never edited by hand. Its box takes Latin words and lists the Quikscript spellings of each, as the box at the top of the VS Code client's Fixes panel does, and clicking a spelling copies it. The page inlines the Latin-to-spellings map, `src/qslex/web/lookup.js` (the lookup code the language server also uses) and the vendored fonts, so it is one file that works from a file: URL and makes no network requests. `make check` runs `python -m qslex.lookup_page --check`, which fails whenever the committed page differs from a rebuild.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from qslex.checker_data import load_records, spellings_by_latin
from qslex.desk import FONT_DIR, FONTS, SITE, WEB, asset, data_uri, substitute
from qslex.readlex import repo_root

PAGE = "lookup.html"
TEMPLATE = "lookup-page.html"
STYLESHEET = "lookup-page.css"
LOOKUP = "lookup.js"
APP = "lookup-page.js"
FACES = (
    "SANS_JUNIOR_REGULAR",
    "SANS_JUNIOR_BOLD",
    "SANS_SENIOR_REGULAR",
    "MONO_REGULAR",
)


def data(root: Path) -> str:
    """The object `lookup.js` reads, as JSON text with the options `qslex.payload` uses."""
    lookup = {"spellings_by_latin": spellings_by_latin(load_records(root))}
    return json.dumps(lookup, ensure_ascii=False, sort_keys=True)


def build(root: Path | None = None) -> str:
    root = root if root is not None else repo_root()
    stylesheet = substitute(
        (WEB / STYLESHEET).read_text(encoding="utf-8"),
        {
            f"__QS_FONT_{key}__": data_uri(asset(FONT_DIR / FONTS[key], root))
            for key in FACES
        },
    )
    return substitute(
        (WEB / TEMPLATE).read_text(encoding="utf-8"),
        {
            "__QS_CSS__": stylesheet,
            "__QS_DATA__": data(root),
            "__QS_LOOKUP__": (WEB / LOOKUP).read_text(encoding="utf-8"),
            "__QS_APP__": (WEB / APP).read_text(encoding="utf-8"),
        },
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the Quikscript Lookup page from the lexicon"
    )
    parser.add_argument("--out", type=Path, default=repo_root() / SITE / PAGE)
    parser.add_argument(
        "--check",
        action="store_true",
        help="rebuild in memory and fail if what is on disk differs",
    )
    args = parser.parse_args(argv)

    page = build()
    if not args.check:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(page, encoding="utf-8", newline="\n")
        print(f"wrote {args.out}")
        print()
        print(f"{len(page.encode('utf-8'))} bytes, self-contained")
        return 0

    stale = ""
    if not args.out.is_file():
        stale = f"{args.out} is missing"
    elif args.out.read_text(encoding="utf-8") != page:
        stale = f"{args.out} differs from a fresh build"
    if stale:
        print(stale)
        print("\nFAILED: 1 artifact(s) out of date; run `make site`")
        return 1
    print("OK: 1 artifact matches a fresh build")
    return 0


if __name__ == "__main__":
    sys.exit(main())
