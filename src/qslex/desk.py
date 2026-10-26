"""Builds the Quikscript Desk page, site/index.html, from the lexicon.

site/index.html is generated and never edited by hand. Its word set, suggestion tables, fonts and Markdown parser are all inlined from the committed lexicon JSON and the pinned vendored assets. The page is a single file that works from a file: URL and makes no network requests. `make check` runs `python -m qslex.desk --check`, which fails whenever the committed page differs from a rebuild.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import html
import re
import sys
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from qslex.checker_data import (
    CheckerDataError,
    Lexicon,
    Record,
    crosscheck,
    derive,
    load_records,
    payload,
)
from qslex.readlex import repo_root
from qslex.words import load_contractions

SITE = "site"
PAGE = "index.html"

WEB = Path(__file__).resolve().parent / "web"
TEMPLATE = "template.html"
STYLESHEET = "app.css"
CORE = "core.js"
APP = "app.js"

FONTS = {
    "SANS_JUNIOR_REGULAR": "AbbotsMortonSpaceportSansJunior-Regular.woff2",
    "SANS_JUNIOR_BOLD": "AbbotsMortonSpaceportSansJunior-Bold.woff2",
    "SANS_SENIOR_REGULAR": "AbbotsMortonSpaceportSansSenior-Regular.woff2",
    "SANS_SENIOR_BOLD": "AbbotsMortonSpaceportSansSenior-Bold.woff2",
    "MONO_REGULAR": "AbbotsMortonSpaceportMono-Regular.woff2",
}
FONT_DIR = Path("data") / "abbots-morton-spaceport"
MARKED_JS = Path("data") / "marked" / "marked.umd.js"

SHA256 = {
    FONT_DIR / FONTS["SANS_JUNIOR_REGULAR"]: (
        "f2a997c4725a84b347040dae4ff776170152fb8c23f5fd35e04bff98c1dc2028"
    ),
    FONT_DIR / FONTS["SANS_JUNIOR_BOLD"]: (
        "c788179a96b5fe0070f8c18d72c2021f87026b809940af7434e6a2636a9d7920"
    ),
    FONT_DIR / FONTS["SANS_SENIOR_REGULAR"]: (
        "09364498461369468ffa69c62f827581d096d6b45666705c94687f03d7bb70f8"
    ),
    FONT_DIR / FONTS["SANS_SENIOR_BOLD"]: (
        "088af65711523d3220e3449659f7404c4110bdefde7dd980bd6fa48d66eae316"
    ),
    FONT_DIR / FONTS["MONO_REGULAR"]: (
        "b4e9223937997b78ece9dcecbb3cfd8b4e0d1a9eaecde9316d74f8ae621e1a59"
    ),
    MARKED_JS: "7a1f8c5e7226b75ff16644bdb2c0130d2ae7371e7ea3106c2d6dac77ab0ff7b6",
}

SAMPLE_WORDS = (("hello", "ITJ"), ("world", "NN1"), ("quick", "AJ0"), ("script", "NN1"))
SAMPLE_HEADING = "# Quikscript Desk"
SAMPLE_PROSE = (
    "Write Markdown on the left and read it on the right. A Quikscript word the "
    "lexicon does not list gets a dotted red underline; click an underlined word "
    "for the spellings it is nearest to."
)

CLOSING_SCRIPT = "</script"
PLACEHOLDER = re.compile(r"__QS_[A-Z_]+__")


class PageError(CheckerDataError):
    pass


@dataclass(frozen=True)
class PageSummary:
    """Counts printed after a build.

    They are informational. tests/test_desk.py checks the spelling counts. Nothing checks the page size.
    """

    lexicon: Lexicon
    size: int

    def report(self) -> str:
        return (
            f"{len(self.lexicon.union)} spellings — {len(self.lexicon.listed)} the "
            f"dictionary lists, plus "
            f"{len(self.lexicon.union) - len(self.lexicon.listed)} senior "
            f"contractions it does not\n"
            f"{self.size} bytes, self-contained"
        )


def asset(name: Path, root: Path) -> bytes:
    """A vendored file’s bytes, after checking them against its SHA-256 digest in `SHA256`.

    The page inlines each of these files, so a changed font or parser would otherwise end up in the generated page with no readable diff. Each vendored directory’s README records where its files came from.
    """
    path = root / name
    if not path.is_file():
        raise PageError(
            f"vendored asset not found at {path}. It is checked in at {name} in a "
            f"source checkout; pass an explicit root when running from elsewhere."
        )
    data = path.read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if actual != SHA256[name]:
        raise PageError(
            f"{path} has SHA-256 {actual}, expected {SHA256[name]}. The digest is "
            f"pinned in src/qslex/desk.py and in that directory’s README. "
            f"Update the digest in both places together."
        )
    return data


def variants(word: str) -> tuple[str, ...]:
    """The candidate misspellings of a word, in the order the sample tries them."""
    if len(word) < 2:
        return ()
    return (word[:-1], word[1:], word[1] + word[0] + word[2:])


def sample(records: Iterable[Record], lexicon: Lexicon) -> str:
    """The document the page opens with, built from the lexicon.

    Each Quikscript word in it is looked up by (Latn, pos), so the sample always uses the lexicon’s current spellings. The misspelling is the first candidate variant of the first sample word that the word set rejects. The page therefore opens with one underlined word to click.
    """
    spelled = {(row.latin.lower(), row.pos): row.qs for row in records}
    missing = [key for key in SAMPLE_WORDS if not spelled.get(key)]
    if missing:
        raise PageError(f"the sample words are not all in the lexicon: {missing}")
    written = [spelled[key] for key in SAMPLE_WORDS]
    accepted = frozenset(lexicon.union)
    wrong = next((word for word in variants(written[0]) if word not in accepted), None)
    if wrong is None:
        raise PageError(f"every candidate variant of {SAMPLE_WORDS[0]} is a spelling")
    line = " ".join([*written, wrong])
    return "\n".join((SAMPLE_HEADING, "", SAMPLE_PROSE, "", line, ""))


def data_uri(raw: bytes) -> str:
    return "data:font/woff2;base64," + base64.b64encode(raw).decode("ascii")


def substitute(text: str, chunks: Mapping[str, str]) -> str:
    """Fills every placeholder, and fails if a chunk contains `</script`.

    A chunk containing `</script` would end its script element wherever the browser’s HTML tokenizer found the string. Without this check, the page would be truncated and the build would still pass. No input contains the string now.
    """
    for token, chunk in chunks.items():
        if CLOSING_SCRIPT in chunk.lower():
            raise PageError(
                f"{token} contains {CLOSING_SCRIPT}, which would end the script "
                f"element early"
            )
        if token not in text:
            raise PageError(f"{token} is not in the template")
        text = text.replace(token, chunk)
    leftover = sorted(set(PLACEHOLDER.findall(text)))
    if leftover:
        raise PageError(f"the template has placeholders nothing filled: {leftover}")
    return text


def build(root: Path | None = None) -> tuple[str, PageSummary]:
    root = root if root is not None else repo_root()
    records = load_records(root)
    lexicon = derive(records, load_contractions())
    crosscheck(lexicon, root)

    stylesheet = substitute(
        (WEB / STYLESHEET).read_text(encoding="utf-8"),
        {
            f"__QS_FONT_{key}__": data_uri(asset(FONT_DIR / name, root))
            for key, name in FONTS.items()
        },
    )
    page = substitute(
        (WEB / TEMPLATE).read_text(encoding="utf-8"),
        {
            "__QS_CSS__": stylesheet,
            "__QS_SAMPLE__": html.escape(sample(records, lexicon)),
            "__QS_MARKED__": asset(MARKED_JS, root).decode("utf-8"),
            "__QS_DATA__": payload(lexicon),
            "__QS_CORE__": (WEB / CORE).read_text(encoding="utf-8"),
            "__QS_APP__": (WEB / APP).read_text(encoding="utf-8"),
        },
    )
    return page, PageSummary(lexicon, len(page.encode("utf-8")))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the Quikscript Desk page from the lexicon"
    )
    parser.add_argument("--out", type=Path, default=repo_root() / SITE / PAGE)
    parser.add_argument(
        "--check",
        action="store_true",
        help="rebuild in memory and fail if what is on disk differs",
    )
    args = parser.parse_args(argv)

    page, summary = build()
    if not args.check:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(page, encoding="utf-8", newline="\n")
        print(f"wrote {args.out}")
        print()
        print(summary.report())
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
