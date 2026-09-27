from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from qslex.elements import DIVIDERS, components
from qslex.tables import rows_of

PENN_FILE = "c5-to-penn.tsv"
PENN_HEADER = ["c5", "penn", "evidence", "note"]
EVIDENCE = {"upstream", "standard"}

EXCEPTIONS_FILE = "phrase-exceptions.tsv"
EXCEPTIONS_HEADER = ["entry", "reason", "note"]
REASONS = {"html-entity", "tokenizer-split"}

FALLBACK = "0"
JOIN = "⬌"

# The Penn tags a row may have, and the order the tagged rows are written in. NNP comes first because latin2shaw.py, like the transliterator here, lets an NNP token fall back to the NN row and takes the first row that matches. Upstream’s file writes NN first, so that fallback is taken before the NNP row is reached, and the proper-noun spellings of derby, reading, slough and other words are never used. The tags after NNP are in alphabetical order, because no other tag’s position changes which row is chosen.
PROPER_NOUN = "NNP"
PENN_TAGS = frozenset(
    {
        "DT",
        "FW",
        "IN",
        "JJ",
        "JJR",
        "JJS",
        "MD",
        "NN",
        "NNP",
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
    }
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
    """C5 to Penn Treebank tags, for the transliterator’s part-of-speech lookup.

    Only heteronyms and the tagged rows of contractions.tsv need a Penn tag. A word with one spelling needs no tagged row, so most of the corpus’s 104 C5 tags have no Penn equivalent here. The `upstream` rows are the mappings required to reproduce readlex_converter.json exactly. The `standard` rows are tags that upstream’s file cannot tell apart from another tag, or never needs. They map to the conventional Penn tag, and each note says which case applies.
    """
    known: dict[str, TagMap] = {}
    for lineno, source, row in rows_of(path, PENN_FILE, PENN_HEADER):
        entry = TagMap(*row)
        if entry.evidence not in EVIDENCE:
            raise ValueError(
                f"{source}:{lineno}: evidence must be one of {sorted(EVIDENCE)}, "
                f"got {entry.evidence!r}"
            )
        if entry.penn not in PENN_TAGS:
            raise ValueError(
                f"{source}:{lineno}: {entry.penn!r} is not a Penn tag "
                f"this table uses (have {sorted(PENN_TAGS)})"
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
    for lineno, source, row in rows_of(path, EXCEPTIONS_FILE, EXCEPTIONS_HEADER):
        entry = PhraseException(*row)
        if entry.reason not in REASONS:
            raise ValueError(
                f"{source}:{lineno}: reason must be one of {sorted(REASONS)}, "
                f"got {entry.reason!r}"
            )
        if not entry.note:
            raise ValueError(f"{source}:{lineno}: every exception needs a note")
        if entry.entry in seen:
            raise ValueError(f"{source}:{lineno}: duplicate row for {entry.entry!r}")
        seen.add(entry.entry)
        out.append(entry)
    return tuple(out)


def _forms(spellings: dict[str, tuple[str, str]]) -> dict[str, str]:
    """One row’s three columns, with the ⬌-joined alternatives in the same order in each."""
    order = sorted(spellings)
    senior = JOIN.join(order)
    junior = JOIN.join(spellings[s][0] for s in order)
    x_letter = JOIN.join(spellings[s][1] for s in order)
    row = {"qs": senior}
    if junior != senior:
        row["qs_junior"] = junior
    if x_letter != senior:
        row["qs_x"] = x_letter
    return row


def _collect(
    entries: Iterable[tuple[str, str, str, str]],
) -> dict[str, tuple[str, str]]:
    spellings: dict[str, tuple[str, str]] = {}
    for _, senior, junior, x_letter in entries:
        forms = (junior or senior, x_letter or senior)
        previous = spellings.setdefault(senior, forms)
        if previous != forms:
            raise ConverterError(
                f"{senior!r} has two different junior/x-letter forms, "
                f"{previous} and {forms}, so the alternatives cannot be lined up"
            )
    return spellings


def converter(
    entries: Iterable[tuple[str, str, str, str, str]], penn: dict[str, TagMap]
) -> dict[str, list[dict[str, str]]]:
    """Latin to spellings, keyed by lowercased Latin for the transliterator’s lookup.

    Tagged rows are written only where a part of speech can choose between spellings: the word must have more than one spelling and more than one Penn tag. The `0` row is the fallback for every tag. It is always written last, because the transliterator takes the first row that matches the token’s tag and otherwise uses the last row.
    """
    grouped: dict[str, list[tuple[str, str, str, str]]] = {}
    for latin, pos, senior, junior, x_letter in entries:
        grouped.setdefault(latin.lower(), []).append((pos, senior, junior, x_letter))

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
                        f"{latin!r} is spelled more than one way and has the C5 tag "
                        f"{pos!r}, which {PENN_FILE} has no Penn equivalent for"
                    )
                continue
            by_tag.setdefault(mapped.penn, []).append(entry)

        rows: list[dict[str, str]] = []
        whole = _collect(group)
        if len(whole) > 1 and len(by_tag) > 1:
            for tag in sorted(by_tag, key=lambda t: (t != PROPER_NOUN, t)):
                rows.append({**_forms(_collect(by_tag[tag])), "tag": tag})
        rows.append({**_forms(whole), "tag": FALLBACK})
        out[latin] = rows
    return out


def _composes(entry: str, fallback: dict[str, str]) -> bool:
    """Whether spelling the pieces separately gives the spelling of the whole entry.

    An entry that does not compose must be matched as a unit before the text is tokenized. Tokenizing it first would spell its pieces and give a different result. A single word with an apostrophe never composes, because the tokenizer splits off the clitic and no lexicon entry spells the clitic on its own.
    """
    pieces = components(entry)
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
