from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from qslex.csur import CODEPOINT_OF

HEADER = ["ipa", "condition", "qs", "codepoints", "letters", "kind", "example", "authority"]
KINDS = {"consonant", "rhotic", "vowel", "sequence", "marker", "tag", "word-sign", "structural"}
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


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_mapping_path() -> Path:
    return repo_root() / "data" / "ipa-to-qs.tsv"


def load_mapping(path: Path | None = None) -> Mapping:
    path = path if path is not None else default_mapping_path()
    entries: list[MapEntry] = []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.reader(f, delimiter="\t")
        header = next(reader)
        if header != HEADER:
            raise ValueError(f"unexpected header in {path}: {header}")
        for lineno, row in enumerate(reader, start=2):
            if len(row) != len(HEADER):
                raise ValueError(f"{path}:{lineno}: expected {len(HEADER)} fields, got {len(row)}")
            ipa, condition, qs, cps, letters, kind, example, authority = row
            names = tuple(n for n in letters.split("·") if n)
            codepoints = tuple(int(c[2:], 16) for c in cps.split())
            entry = MapEntry(ipa, condition, qs, codepoints, names, kind, example, authority)
            if kind not in KINDS:
                raise ValueError(f"{path}:{lineno}: unknown kind {kind!r}")
            unknown = [n for n in names if n not in CODEPOINT_OF]
            if unknown:
                raise ValueError(f"{path}:{lineno}: unknown letter names {unknown}")
            if codepoints != tuple(CODEPOINT_OF[n] for n in names):
                raise ValueError(f"{path}:{lineno}: codepoints do not match letter names")
            if qs != "".join(chr(c) for c in codepoints):
                raise ValueError(f"{path}:{lineno}: qs string does not match codepoints")
            entries.append(entry)

    lookup: dict[str, dict[str, MapEntry]] = {}
    for entry in entries:
        conditions = lookup.setdefault(entry.ipa, {})
        if entry.condition in conditions:
            raise ValueError(f"duplicate mapping row for {entry.ipa!r} / {entry.condition!r}")
        conditions[entry.condition] = entry
    for ipa, conditions in lookup.items():
        if set(conditions) not in CONDITION_SETS:
            raise ValueError(f"incoherent condition set for {ipa!r}: {sorted(conditions)}")

    tokens = tuple(sorted(lookup, key=len, reverse=True))
    return Mapping(tuple(entries), lookup, tokens)
