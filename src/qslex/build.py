from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from qslex.converter import (
    TagMap,
    converter,
    load_penn,
    load_phrase_exceptions,
    phrases,
)
from qslex.csur import CODEPOINT_OF
from qslex.hunspell import affix, dictionary, spellings
from qslex.letters import VOWELS, parse, render_qs
from qslex.mapping import Mapping, load_mapping
from qslex.overrides import load_overrides
from qslex.quirks import load_quirks, normalize
from qslex.readlex import (
    CORPUS_COMMIT,
    CORPUS_SHA256,
    CORPUS_URL,
    Row,
    load_rows,
    repo_root,
)
from qslex.rules import Context, load_tables, spell
from qslex.tokenizer import tokenize
from qslex.variants import load_var_tags, select

ARTIFACTS = "lexicon"
LEXICON_JSON = "quikscript-lexicon.json"
LEXICON_TSV = "quikscript-lexicon.tsv"
PHRASES_TXT = "qs_converter_phrases.txt"
HUNSPELL_DIC = "en-Qaas.dic"
HUNSPELL_AFF = "en-Qaas.aff"

TSV_HEADER = ("Latn", "qs", "qs_junior", "qs_x", "Shaw", "pos", "ipa", "freq")
LETTERS_HEADER = ("codepoint", "qs", "name", "class", "ipa")

SCHEMA_VERSION = 1
PUA_BLOCK = "U+E650–U+E67E"

X_LETTERS = frozenset({"Excite", "Exam"})


@dataclass(frozen=True)
class Entry:
    headword: str
    latin: str
    qs: str
    junior: str
    x_letter: str
    shavian: str
    pos: str
    ipa: str
    frequency: int

    def row(self) -> tuple[str, ...]:
        return (
            self.latin,
            self.qs,
            self.junior,
            self.x_letter,
            self.shavian,
            self.pos,
            self.ipa,
            str(self.frequency),
        )

    def record(self) -> dict[str, str | int]:
        out: dict[str, str | int] = {"Latn": self.latin, "qs": self.qs}
        if self.junior:
            out["qs_junior"] = self.junior
        if self.x_letter:
            out["qs_x"] = self.x_letter
        out["Shaw"] = self.shavian
        out["pos"] = self.pos
        out["ipa"] = self.ipa
        out["freq"] = self.frequency
        return out


@dataclass(frozen=True)
class Coverage:
    """What the build touched, for the log.

    Every number is pinned and adjudicated in qslex.validate, so this is a convenience for whoever is watching a change land rather than a check of its own. The tally is done in `report`, so a build that prints nothing counts nothing.
    """

    read: int
    spelled: tuple[Entry, ...]

    def report(self) -> str:
        junior = sum(1 for entry in self.spelled if entry.junior)
        x_letter = sum(1 for entry in self.spelled if entry.x_letter)
        return (
            f"converted {len(self.spelled)} corpus rows, "
            f"skipped {self.read - len(self.spelled)}\n"
            f"sparse columns: {junior} junior, {x_letter} x-letter"
        )


def convert(rows: Iterable[Row], mapping: Mapping) -> tuple[Entry, ...]:
    """Every kept row spelled, in corpus order.

    Nothing here decides how a word is spelled: the mapping, the rules and the word signs have all already run by the time `spell` returns, and this only renders what they produced into the PUA encoding the artifacts carry.

    The IPA carried out is the quirk-normalized string, not the corpus’s own, so that every row explains its own spelling. Upstream’s unrepaired IPA stays available in the vendored corpus, which is where anyone diffing against ReadLex should look.
    """
    quirks = load_quirks()
    overrides = load_overrides(mapping)
    tables = load_tables()
    out: list[Entry] = []
    for row in rows:
        ipa, _ = normalize(row.ipa, quirks)
        tokens = tokenize(ipa, mapping, overrides)
        context = Context(row.word.lower(), row.pos, ipa, tuple(tokens))
        result = spell(context, tables)
        out.append(
            Entry(
                headword=row.headword,
                latin=row.word,
                qs=render_qs(parse(result.senior)),
                junior=render_qs(parse(result.junior)) if result.junior else "",
                x_letter=render_qs(parse(result.x_letter)) if result.x_letter else "",
                shavian=row.shavian,
                pos=row.pos,
                ipa=ipa,
                frequency=row.frequency,
            )
        )
    return tuple(out)


def _nested(value: object) -> str:
    """A small top-level value, its own lines pushed in by one step."""
    return json.dumps(value, ensure_ascii=False, indent=4).replace("\n", "\n    ")


def _per_line(items: Iterable[str], brackets: str) -> str:
    """A large top-level collection, one element to a line."""
    body = ",\n".join(f"        {item}" for item in items)
    if not body:
        return brackets
    return f"{brackets[0]}\n{body}\n    {brackets[1]}"


def lexicon_json(
    entries: Iterable[Entry],
    mapping: Mapping,
    penn: dict[str, TagMap],
    listed: Iterable[str],
) -> str:
    """The master, and the only JSON this repository ships.

    Everything else in `lexicon/` is a projection of this file, so it carries the three things a projection needs that the entries alone cannot give: the letter table the PUA text is read with, the C5-to-Penn map the converter shape’s tagged rows are keyed by, and the phrase list, which no property of the entries can reveal because it is the orthographic rules, not the data, that decide what fails to compose. Holding this one file is holding the lexicon.

    Two of the three duplicate `c5-to-penn.tsv` and the phrases file. They cannot drift from them: all three are written by this one pass, and `make check` rebuilds and byte-compares every one of them. The letter table ships nowhere else.

    One headword to a line, rather than a field to a line. The file is generated, so the useful diff is which entries moved, and that reads as one changed line each.
    """
    grouped: dict[str, list[dict[str, str | int]]] = {}
    for entry in entries:
        grouped.setdefault(entry.headword, []).append(entry.record())
    phrase_list = tuple(listed)
    meta = {
        "version": SCHEMA_VERSION,
        "source": {
            "repo": CORPUS_URL,
            "commit": CORPUS_COMMIT,
            "sha256": CORPUS_SHA256,
        },
        "encoding": {"block": PUA_BLOCK},
        "counts": {
            "headwords": len(grouped),
            "entries": sum(len(group) for group in grouped.values()),
            "phrases": len(phrase_list),
        },
    }
    sections = (
        ("meta", _nested(meta)),
        (
            "letters",
            _per_line(
                (
                    json.dumps(
                        dict(zip(LETTERS_HEADER, row, strict=True)), ensure_ascii=False
                    )
                    for row in letters_rows(mapping)
                ),
                "[]",
            ),
        ),
        ("c5_to_penn", _nested({c5: tag.penn for c5, tag in penn.items()})),
        (
            "phrases",
            _per_line(
                (json.dumps(phrase, ensure_ascii=False) for phrase in phrase_list), "[]"
            ),
        ),
        (
            "entries",
            _per_line(
                (
                    f"{json.dumps(headword, ensure_ascii=False)}: "
                    f"{json.dumps(group, ensure_ascii=False)}"
                    for headword, group in grouped.items()
                ),
                "{}",
            ),
        ),
    )
    body = ",\n".join(f"    {json.dumps(name)}: {value}" for name, value in sections)
    return "{\n" + body + "\n}\n"


def lexicon_tsv(entries: Iterable[Entry]) -> str:
    """The flat projection, deduplicated.

    Two headwords can list the same inflected form — ax and axe both own axed — so the flattening has to collapse them. Upstream’s own TSV shipped those rows twice (Shavian-info/readlex#124); this is the single place where that can happen, because every artifact is projected from the grouped form rather than emitted beside it.
    """
    lines = ["\t".join(TSV_HEADER)]
    seen: set[tuple[str, ...]] = set()
    for entry in entries:
        row = entry.row()
        if row in seen:
            continue
        seen.add(row)
        lines.append("\t".join(row))
    return "\n".join(lines) + "\n"


def letters_rows(mapping: Mapping) -> tuple[tuple[str, ...], ...]:
    """The decoder ring: PUA text is opaque without a Quikscript font, so name it."""
    sources: dict[str, list[str]] = {name: [] for name in CODEPOINT_OF}
    for entry in mapping.entries:
        for name in entry.letters:
            if entry.ipa not in sources[name]:
                sources[name].append(entry.ipa)
    rows: list[tuple[str, ...]] = []
    for name, codepoint in CODEPOINT_OF.items():
        if name in X_LETTERS:
            kind = "x-letter"
        elif name in VOWELS:
            kind = "vowel"
        else:
            kind = "consonant"
        rows.append(
            (
                f"U+{codepoint:04X}",
                chr(codepoint),
                name,
                kind,
                " ".join(sources[name]),
            )
        )
    return tuple(rows)


def artifacts(entries: tuple[Entry, ...], mapping: Mapping) -> dict[str, str]:
    """The five files, every one of them a projection of the same entries.

    The converter shape is built here and not written: `phrases` is derived from it, and the master carries everything the shape itself is rebuilt from, so shipping it as a second JSON would only be shipping the master’s own data twice.
    """
    penn = load_penn()
    rows = converter(
        ((e.latin, e.pos, e.qs, e.junior, e.x_letter) for e in entries), penn
    )
    listed = phrases(rows, load_phrase_exceptions())
    checkable = spellings((e.qs, e.junior, e.x_letter) for e in entries)
    return {
        LEXICON_JSON: lexicon_json(entries, mapping, penn, listed),
        LEXICON_TSV: lexicon_tsv(entries),
        PHRASES_TXT: "\n".join(listed) + "\n",
        HUNSPELL_DIC: dictionary(checkable),
        HUNSPELL_AFF: affix(checkable),
    }


def build(
    path: Path | None = None, verify: bool = True
) -> tuple[dict[str, str], Coverage]:
    mapping = load_mapping()
    rows = load_rows(path, verify=verify)
    entries = convert(select(load_var_tags(), rows), mapping)
    return artifacts(entries, mapping), Coverage(len(rows), entries)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the Quikscript lexicon from the vendored ReadLex corpus"
    )
    parser.add_argument("readlex", nargs="?", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=repo_root() / ARTIFACTS)
    parser.add_argument(
        "--check",
        action="store_true",
        help="rebuild in memory and fail if what is on disk differs",
    )
    parser.add_argument("--no-verify-digest", action="store_true")
    args = parser.parse_args(argv)

    built, coverage = build(args.readlex, verify=not args.no_verify_digest)
    if not args.check:
        args.out.mkdir(parents=True, exist_ok=True)
        for name, text in built.items():
            (args.out / name).write_text(text, encoding="utf-8", newline="\n")
            print(f"wrote {args.out / name}")
        print()
        print(coverage.report())
        return 0

    stale: list[str] = []
    for name, text in built.items():
        path = args.out / name
        if not path.is_file():
            stale.append(f"{path} is missing")
        elif path.read_text(encoding="utf-8") != text:
            stale.append(f"{path} differs from a fresh build")
    for line in stale:
        print(line)
    if stale:
        print(f"\nFAILED: {len(stale)} artifact(s) out of date; run `make artifacts`")
        return 1
    print(f"OK: {len(built)} artifacts match a fresh build")
    return 0


if __name__ == "__main__":
    sys.exit(main())
