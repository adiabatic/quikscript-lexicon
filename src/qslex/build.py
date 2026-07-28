from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from qslex.converter import converter, load_penn, load_phrase_exceptions, phrases
from qslex.csur import CODEPOINT_OF
from qslex.hunspell import affix, dictionary, spellings
from qslex.letters import VOWELS, parse, render_qs
from qslex.mapping import Mapping, load_mapping
from qslex.overrides import load_overrides
from qslex.quirks import load_quirks, normalize
from qslex.readlex import Row, load_rows, repo_root
from qslex.rules import Context, load_tables, spell
from qslex.tokenizer import tokenize
from qslex.variants import load_var_tags, select

ARTIFACTS = "lexicon"
LEXICON_JSON = "quikscript-lexicon.json"
LEXICON_TSV = "quikscript-lexicon.tsv"
CONVERTER_JSON = "qs_converter.json"
PHRASES_TXT = "qs_converter_phrases.txt"
LETTERS_TSV = "letters.tsv"
HUNSPELL_DIC = "en-Qaas.dic"
HUNSPELL_AFF = "en-Qaas.aff"

TSV_HEADER = ("Latn", "qs", "qs_junior", "qs_x", "Shaw", "pos", "ipa", "freq")
LETTERS_HEADER = ("codepoint", "qs", "name", "class", "ipa")

LIGATURES = frozenset({"Excite", "Exam"})


@dataclass(frozen=True)
class Entry:
    headword: str
    latin: str
    qs: str
    junior: str
    ligature: str
    shavian: str
    pos: str
    ipa: str
    frequency: int

    def row(self) -> tuple[str, ...]:
        return (
            self.latin,
            self.qs,
            self.junior,
            self.ligature,
            self.shavian,
            self.pos,
            self.ipa,
            str(self.frequency),
        )

    def record(self) -> dict[str, str | int]:
        out: dict[str, str | int] = {"Latn": self.latin, "qs": self.qs}
        if self.junior:
            out["qs_junior"] = self.junior
        if self.ligature:
            out["qs_x"] = self.ligature
        out["Shaw"] = self.shavian
        out["pos"] = self.pos
        out["ipa"] = self.ipa
        out["freq"] = self.frequency
        return out


@dataclass(frozen=True)
class Coverage:
    """What the build touched, for the log.

    Every number is pinned and adjudicated in qslex.validate, so this is a convenience
    for whoever is watching a change land rather than a check of its own. The tally is
    done in `report`, so a build that prints nothing counts nothing.
    """

    read: int
    spelt: tuple[Entry, ...]

    def report(self) -> str:
        junior = sum(1 for entry in self.spelt if entry.junior)
        ligature = sum(1 for entry in self.spelt if entry.ligature)
        return (
            f"converted {len(self.spelt)} corpus rows, "
            f"skipped {self.read - len(self.spelt)}\n"
            f"sparse columns: {junior} junior, {ligature} ligature"
        )


def convert(rows: Iterable[Row], mapping: Mapping) -> tuple[Entry, ...]:
    """Every kept row spelt, in corpus order.

    Nothing here decides how a word is spelt: the mapping, the rules and the word signs
    have all already run by the time `spell` returns, and this only renders what they
    produced into the PUA encoding the artifacts carry.

    The IPA carried out is the quirk-normalised string, not the corpus's own, so that
    every row explains its own spelling. Upstream's unrepaired IPA stays available in
    the vendored corpus, which is where anyone diffing against ReadLex should look.
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
                ligature=render_qs(parse(result.ligature)) if result.ligature else "",
                shavian=row.shavian,
                pos=row.pos,
                ipa=ipa,
                frequency=row.frequency,
            )
        )
    return tuple(out)


def lexicon_json(entries: Iterable[Entry]) -> str:
    grouped: dict[str, list[dict[str, str | int]]] = {}
    for entry in entries:
        grouped.setdefault(entry.headword, []).append(entry.record())
    return json.dumps(grouped, ensure_ascii=False, indent=4) + "\n"


def lexicon_tsv(entries: Iterable[Entry]) -> str:
    """The flat projection, deduplicated.

    Two headwords can list the same inflected form — ax and axe both own axed — so the
    flattening has to collapse them. Upstream's own TSV shipped those rows twice
    (Shavian-info/readlex#124); this is the single place where that can happen, because
    every artifact is projected from the grouped form rather than emitted beside it.
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


def letters_tsv(mapping: Mapping) -> str:
    """The decoder ring: PUA text is opaque without a Quikscript font, so name it."""
    sources: dict[str, list[str]] = {name: [] for name in CODEPOINT_OF}
    for entry in mapping.entries:
        for name in entry.letters:
            if entry.ipa not in sources[name]:
                sources[name].append(entry.ipa)
    lines = ["\t".join(LETTERS_HEADER)]
    for name, codepoint in CODEPOINT_OF.items():
        if name in LIGATURES:
            kind = "ligature"
        elif name in VOWELS:
            kind = "vowel"
        else:
            kind = "consonant"
        lines.append(
            "\t".join(
                (
                    f"U+{codepoint:04X}",
                    chr(codepoint),
                    name,
                    kind,
                    " ".join(sources[name]),
                )
            )
        )
    return "\n".join(lines) + "\n"


def artifacts(entries: tuple[Entry, ...], mapping: Mapping) -> dict[str, str]:
    rows = converter(
        ((e.latin, e.pos, e.qs, e.junior, e.ligature) for e in entries), load_penn()
    )
    listed = phrases(rows, load_phrase_exceptions())
    checkable = spellings((e.qs, e.junior, e.ligature) for e in entries)
    return {
        LEXICON_JSON: lexicon_json(entries),
        LEXICON_TSV: lexicon_tsv(entries),
        CONVERTER_JSON: json.dumps(rows, ensure_ascii=False, indent=4) + "\n",
        PHRASES_TXT: "\n".join(listed) + "\n",
        LETTERS_TSV: letters_tsv(mapping),
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
