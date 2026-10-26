from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from qslex.added import added_rows, load_added_words
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

SCHEMA_VERSION = 2
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
class BuildSummary:
    """Counts printed after a build.

    They are informational. `qslex.readlex` checks the corpus row count when it loads the corpus, and qslex.validate checks the kept rows and the junior rows. Nothing checks the X-letter row count or the number of added words. `report` does the counting, so a build that prints nothing (`--check`) counts nothing.
    """

    read: int
    added: int
    spelled: tuple[Entry, ...]

    def report(self) -> str:
        corpus = len(self.spelled) - self.added
        junior = sum(1 for entry in self.spelled if entry.junior)
        x_letter = sum(1 for entry in self.spelled if entry.x_letter)
        return (
            f"converted {corpus} corpus rows, skipped {self.read - corpus}\n"
            f"added beyond the corpus: {self.added}\n"
            f"sparse columns: {junior} junior, {x_letter} x-letter"
        )


def convert(rows: Iterable[Row], mapping: Mapping) -> tuple[Entry, ...]:
    """Spells each row it is given, in order.

    This function makes no spelling decisions. The mapping, the rules and the word signs have all run by the time `spell` returns, and this function renders their result in the PUA encoding the artifacts use.

    The IPA written out is the quirk-normalized string rather than the corpus’s, so that each row’s IPA matches its spelling. Upstream’s unrepaired IPA is in the vendored corpus. Compare against that when diffing with ReadLex.
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
    """A small top-level value as indented JSON, with every line after the first indented one more level."""
    return json.dumps(value, ensure_ascii=False, indent=4).replace("\n", "\n    ")


def _per_line(items: Iterable[str], brackets: str) -> str:
    """A large top-level collection, one element per line."""
    body = ",\n".join(f"        {item}" for item in items)
    if not body:
        return brackets
    return f"{brackets[0]}\n{body}\n    {brackets[1]}"


def lexicon_json(
    entries: Iterable[Entry],
    mapping: Mapping,
    penn: dict[str, TagMap],
    listed: Iterable[str],
    added: int,
) -> str:
    """`lexicon/quikscript-lexicon.json`, the only JSON file in `lexicon/`.

    Every other generated file in `lexicon/` can be derived from this one, because it also contains three things the entries do not. These are the letter table for reading the PUA text, the C5-to-Penn map that keys the converter table’s tagged rows, and the phrase list. The phrase list depends on `phrase-exceptions.tsv` as well as the entries, so it cannot be rebuilt from the entries alone.

    Two of the three have copies elsewhere. `c5_to_penn` is built from `src/qslex/data/c5-to-penn.tsv`, a hand-edited input that the build reads, and tests/test_build.py checks that the two are equal. `phrases` has the same lines as `qs_converter_phrases.txt`, which this build writes from the same list. The letter table is in no other file.

    `meta.counts` includes the number of added words, because `meta.source` names the corpus and the corpus no longer accounts for every entry. `added-words.tsv` lists which entries they are.

    The file has one headword per line rather than one field per line. A diff of the generated file then shows one changed line per changed headword.
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
            "added": added,
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
    """`lexicon/quikscript-lexicon.tsv`, one line per entry, with duplicate lines removed.

    Two headwords can list the same inflected form (ax and axe both list axed), so identical rows are written once. Upstream’s own TSV listed such rows twice (Shavian-info/readlex#124).
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
    """The rows of the lexicon JSON’s `letters` table, which maps each codepoint to its letter name, class and IPA, so PUA text can be read without a Quikscript font."""
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


def artifacts(
    entries: tuple[Entry, ...], mapping: Mapping, added: int
) -> dict[str, str]:
    """The five files, all generated from the same entries.

    The converter table (Latin word to tagged spellings, in readlex_converter.json’s format) is built here but not written. `phrases` is derived from it. The lexicon JSON contains everything needed to rebuild it, so writing it as a second JSON file would repeat the lexicon JSON’s data.
    """
    penn = load_penn()
    rows = converter(
        ((e.latin, e.pos, e.qs, e.junior, e.x_letter) for e in entries), penn
    )
    listed = phrases(rows, load_phrase_exceptions())
    checkable = spellings((e.qs, e.junior, e.x_letter) for e in entries)
    return {
        LEXICON_JSON: lexicon_json(entries, mapping, penn, listed, added),
        LEXICON_TSV: lexicon_tsv(entries),
        PHRASES_TXT: "\n".join(listed) + "\n",
        HUNSPELL_DIC: dictionary(checkable),
        HUNSPELL_AFF: affix(checkable),
    }


def build(
    path: Path | None = None, verify: bool = True
) -> tuple[dict[str, str], BuildSummary]:
    """The corpus rows the row policy keeps, followed by the added words.

    The added words go after the corpus rows rather than among them. The lexicon JSON’s headwords then stay in corpus order, an upstream update diffs cleanly, and the added headwords are together at the end.
    """
    mapping = load_mapping()
    rows = load_rows(path, verify=verify)
    added = added_rows(load_added_words())
    entries = convert(select(load_var_tags(), rows) + added, mapping)
    return artifacts(entries, mapping, len(added)), BuildSummary(
        len(rows), len(added), entries
    )


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

    built, summary = build(args.readlex, verify=not args.no_verify_digest)
    if not args.check:
        args.out.mkdir(parents=True, exist_ok=True)
        for name, text in built.items():
            (args.out / name).write_text(text, encoding="utf-8", newline="\n")
            print(f"wrote {args.out / name}")
        print()
        print(summary.report())
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
