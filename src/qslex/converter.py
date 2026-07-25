from __future__ import annotations

import csv
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from qslex.mapping import open_data

PENN_FILE = "c5-to-penn.tsv"
PENN_HEADER = ["c5", "penn", "evidence", "note"]
EVIDENCE = {"upstream", "standard"}

EXCEPTIONS_FILE = "phrase-exceptions.tsv"
EXCEPTIONS_HEADER = ["entry", "reason", "note"]
REASONS = {"html-entity", "tokenizer-split"}

FALLBACK = "0"
JOIN = "⬌"
BOUNDARY = re.compile(r"([ -])")
DIVIDERS = frozenset(" -")

# The order tagged rows are written in. Proper nouns come first on purpose: a consumer
# that falls back from NNP to the NN row — which is what latin2shaw.py does — reaches
# that fallback before the exact NNP row if NN is written first, so upstream's own file
# makes the proper-noun spelling of august, derby, reading, slough and 23 others
# unreachable. Everything after NNP is alphabetical, because nothing else needs an
# opinion and an arbitrary order would only invite one.
PENN_ORDER = (
    "NNP",
    "DT",
    "FW",
    "IN",
    "JJ",
    "JJR",
    "JJS",
    "MD",
    "NN",
    "NNS",
    "PRP",
    "RB",
    "SYM",
    "UH",
    "VB",
    "VBD",
    "VBG",
    "VBN",
    "VBP",
    "VBZ",
    "WP",
)


@dataclass(frozen=True)
class TagMap:
    c5: str
    penn: str
    evidence: str
    note: str


@dataclass(frozen=True)
class PhraseException:
    entry: str
    reason: str
    note: str


class ConverterError(ValueError):
    pass


def load_penn(path: Path | None = None) -> dict[str, TagMap]:
    """C5 to Penn Treebank, for the transliterator's part-of-speech lookup.

    Only heteronyms consult this: a word with one spelling needs no tagged row, so most
    of the corpus's 104 C5 tags never need a Penn equivalent and none is invented for
    them. The `upstream` rows are the ones forced by reproducing readlex_converter.json
    exactly; the `standard` rows are pairs upstream's file cannot separate, or does not
    reach, where the conventional correspondence is used and said to be used.
    """
    known: dict[str, TagMap] = {}
    with open_data(path, PENN_FILE) as (f, source):
        reader = csv.reader(f, delimiter="\t")
        header = next(reader)
        if header != PENN_HEADER:
            raise ValueError(f"unexpected header in {source}: {header}")
        for lineno, row in enumerate(reader, start=2):
            if len(row) != len(PENN_HEADER):
                raise ValueError(
                    f"{source}:{lineno}: expected {len(PENN_HEADER)} fields, "
                    f"got {len(row)}"
                )
            entry = TagMap(*row)
            if entry.evidence not in EVIDENCE:
                raise ValueError(
                    f"{source}:{lineno}: evidence must be one of {sorted(EVIDENCE)}, "
                    f"got {entry.evidence!r}"
                )
            if entry.penn not in PENN_ORDER:
                raise ValueError(
                    f"{source}:{lineno}: {entry.penn!r} has no place in the row order"
                )
            if not entry.note:
                raise ValueError(f"{source}:{lineno}: every mapping needs a note")
            if entry.c5 in known:
                raise ValueError(f"{source}:{lineno}: duplicate row for {entry.c5!r}")
            known[entry.c5] = entry
    return known


def load_phrase_exceptions(path: Path | None = None) -> tuple[PhraseException, ...]:
    out: list[PhraseException] = []
    seen: set[str] = set()
    with open_data(path, EXCEPTIONS_FILE) as (f, source):
        reader = csv.reader(f, delimiter="\t")
        header = next(reader)
        if header != EXCEPTIONS_HEADER:
            raise ValueError(f"unexpected header in {source}: {header}")
        for lineno, row in enumerate(reader, start=2):
            if len(row) != len(EXCEPTIONS_HEADER):
                raise ValueError(
                    f"{source}:{lineno}: expected {len(EXCEPTIONS_HEADER)} fields, "
                    f"got {len(row)}"
                )
            entry = PhraseException(*row)
            if entry.reason not in REASONS:
                raise ValueError(
                    f"{source}:{lineno}: reason must be one of {sorted(REASONS)}, "
                    f"got {entry.reason!r}"
                )
            if not entry.note:
                raise ValueError(f"{source}:{lineno}: every exception needs a note")
            if entry.entry in seen:
                raise ValueError(
                    f"{source}:{lineno}: duplicate row for {entry.entry!r}"
                )
            seen.add(entry.entry)
            out.append(entry)
    return tuple(out)


def _forms(spellings: dict[str, tuple[str, str]]) -> dict[str, str]:
    """One row's three columns, alternatives joined in one order across all of them."""
    order = sorted(spellings)
    senior = JOIN.join(order)
    junior = JOIN.join(spellings[s][0] for s in order)
    ligature = JOIN.join(spellings[s][1] for s in order)
    row = {"qs": senior}
    if junior != senior:
        row["qs_junior"] = junior
    if ligature != senior:
        row["qs_x"] = ligature
    return row


def _collect(
    entries: Iterable[tuple[str, str, str, str]],
) -> dict[str, tuple[str, str]]:
    spellings: dict[str, tuple[str, str]] = {}
    for _, senior, junior, ligature in entries:
        forms = (junior or senior, ligature or senior)
        previous = spellings.setdefault(senior, forms)
        if previous != forms:
            raise ConverterError(
                f"{senior!r} carries two different junior/ligature forms, "
                f"{previous} and {forms}, so the alternatives cannot be lined up"
            )
    return spellings


def converter(
    entries: Iterable[tuple[str, str, str, str, str]], penn: dict[str, TagMap]
) -> dict[str, list[dict[str, str]]]:
    """Latin to spellings, keyed for the transliterator rather than for a reader.

    Tagged rows are written only where they can settle something: a word needs both
    more than one spelling and more than one Penn tag before a part of speech can
    choose between them. The `0` row is the universal fallback and is always written
    last, because the consumer takes the first row that matches.
    """
    grouped: dict[str, list[tuple[str, str, str, str]]] = {}
    for latin, pos, senior, junior, ligature in entries:
        grouped.setdefault(latin.lower(), []).append((pos, senior, junior, ligature))

    out: dict[str, list[dict[str, str]]] = {}
    for latin in sorted(grouped):
        group = grouped[latin]
        by_tag: dict[str, list[tuple[str, str, str, str]]] = {}
        for entry in group:
            pos = entry[0]
            mapped = penn.get(pos)
            if mapped is None:
                if len({e[1] for e in group}) > 1:
                    raise ConverterError(
                        f"{latin!r} is spelt more than one way and carries the C5 tag "
                        f"{pos!r}, which {PENN_FILE} has no Penn equivalent for"
                    )
                continue
            by_tag.setdefault(mapped.penn, []).append(entry)

        rows: list[dict[str, str]] = []
        whole = _collect(group)
        if len(whole) > 1 and len(by_tag) > 1:
            for tag in PENN_ORDER:
                if tag in by_tag:
                    rows.append({**_forms(_collect(by_tag[tag])), "tag": tag})
        rows.append({**_forms(whole), "tag": FALLBACK})
        out[latin] = rows
    return out


def _composes(entry: str, fallback: dict[str, str]) -> bool:
    """Whether spelling the pieces separately spells the whole entry.

    An entry that does not compose has to be matched as one unit before the text is
    tokenized, because tokenizing it first would spell its pieces and get a different
    answer. A single word with an apostrophe never composes: the tokenizer splits the
    clitic off, and no lexicon entry covers the halves.
    """
    pieces = BOUNDARY.split(entry)
    if len(pieces) == 1:
        return "'" not in entry
    built: list[str] = []
    for piece in pieces:
        if piece in DIVIDERS:
            built.append(piece)
            continue
        if piece not in fallback:
            return False
        built.append(fallback[piece])
    return "".join(built) == fallback[entry]


def phrases(
    rows: dict[str, list[dict[str, str]]], exceptions: Iterable[PhraseException]
) -> tuple[str, ...]:
    fallback = {latin: value[-1]["qs"] for latin, value in rows.items()}
    found = {latin for latin in rows if not _composes(latin, fallback)}
    found.update(exception.entry for exception in exceptions)
    return tuple(sorted(found))
