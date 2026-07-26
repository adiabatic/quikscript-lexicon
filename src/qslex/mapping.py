from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from qslex.csur import CODEPOINT_OF
from qslex.tables import rows_of

MAPPING_FILE = "ipa-to-qs.tsv"

HEADER = [
    "ipa",
    "condition",
    "qs",
    "codepoints",
    "letters",
    "kind",
    "example",
    "authority",
]
KINDS = {
    "consonant",
    "rhotic",
    "vowel",
    "sequence",
    "marker",
    "tag",
    "word-sign",
    "structural",
    "hiatus",
}
CONDITION_SETS = [{""}, {"stressed", "unstressed"}, {"pre-r", "no-r"}]


@dataclass(frozen=True)
class MapEntry:
    ipa: str
    condition: str
    qs: str
    codepoints: tuple[int, ...]
    letters: tuple[str, ...]
    kind: str
    example: str
    authority: str


@dataclass(frozen=True)
class Mapping:
    entries: tuple[MapEntry, ...]
    lookup: dict[str, dict[str, MapEntry]]
    tokens_by_length: tuple[str, ...]


def load_mapping(path: Path | None = None) -> Mapping:
    entries: list[MapEntry] = []
    for lineno, source, row in rows_of(path, MAPPING_FILE, HEADER):
        ipa, condition, qs, cps, letters, kind, example, authority = row
        if not ipa:
            raise ValueError(f"{source}:{lineno}: empty ipa token")
        names = tuple(n for n in letters.split("·") if n)
        if letters and not letters.startswith("·"):
            raise ValueError(
                f"{source}:{lineno}: letters must be ·-prefixed: {letters!r}"
            )
        for cp in cps.split():
            if not cp.startswith("U+"):
                raise ValueError(
                    f"{source}:{lineno}: codepoint must be U+-prefixed: {cp!r}"
                )
        try:
            codepoints = tuple(int(c.removeprefix("U+"), 16) for c in cps.split())
        except ValueError as error:
            raise ValueError(f"{source}:{lineno}: bad codepoint: {error}") from error
        entry = MapEntry(
            ipa, condition, qs, codepoints, names, kind, example, authority
        )
        if kind not in KINDS:
            raise ValueError(f"{source}:{lineno}: unknown kind {kind!r}")
        if kind in {"marker", "structural", "hiatus"} and (names or codepoints):
            raise ValueError(f"{source}:{lineno}: {kind} row must map to no letters")
        unknown = [n for n in names if n not in CODEPOINT_OF]
        if unknown:
            raise ValueError(f"{source}:{lineno}: unknown letter names {unknown}")
        if codepoints != tuple(CODEPOINT_OF[n] for n in names):
            raise ValueError(f"{source}:{lineno}: codepoints do not match letter names")
        if qs != "".join(chr(c) for c in codepoints):
            raise ValueError(f"{source}:{lineno}: qs string does not match codepoints")
        entries.append(entry)

    lookup: dict[str, dict[str, MapEntry]] = {}
    for entry in entries:
        conditions = lookup.setdefault(entry.ipa, {})
        if entry.condition in conditions:
            raise ValueError(
                f"duplicate mapping row for {entry.ipa!r} / {entry.condition!r}"
            )
        conditions[entry.condition] = entry
    for ipa, conditions in lookup.items():
        if set(conditions) not in CONDITION_SETS:
            raise ValueError(
                f"incoherent condition set for {ipa!r}: {sorted(conditions)}"
            )

    tokens = tuple(sorted(lookup, key=len, reverse=True))
    return Mapping(tuple(entries), lookup, tokens)
