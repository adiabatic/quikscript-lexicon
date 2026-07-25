from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from qslex.mapping import open_data

DIVERGENCES_FILE = "shavian-divergences.tsv"
DIVERGENCES_HEADER = ["word", "ipa", "condition", "shavian", "family", "authority"]
CONDITIONS = {"stressed", "unstressed", "none"}


@dataclass(frozen=True)
class Divergence:
    word: str
    ipa: str
    condition: str
    shavian: str
    family: str
    authority: str


def load_divergences(path: Path | None = None) -> dict[tuple[str, str], Divergence]:
    known: dict[tuple[str, str], Divergence] = {}
    with open_data(path, DIVERGENCES_FILE) as (f, source):
        reader = csv.reader(f, delimiter="\t")
        header = next(reader)
        if header != DIVERGENCES_HEADER:
            raise ValueError(f"unexpected header in {source}: {header}")
        for lineno, row in enumerate(reader, start=2):
            if len(row) != len(DIVERGENCES_HEADER):
                raise ValueError(
                    f"{source}:{lineno}: expected {len(DIVERGENCES_HEADER)} fields, "
                    f"got {len(row)}"
                )
            entry = Divergence(*row)
            if not entry.authority:
                raise ValueError(
                    f"{source}:{lineno}: a divergence from Shavian needs an authority"
                )
            if not entry.word or not entry.ipa:
                raise ValueError(f"{source}:{lineno}: word and ipa are both required")
            if entry.condition not in CONDITIONS:
                raise ValueError(
                    f"{source}:{lineno}: condition must be one of "
                    f"{sorted(CONDITIONS)}, got {entry.condition!r}"
                )
            if not entry.shavian or not entry.family:
                raise ValueError(f"{source}:{lineno}: shavian and family are required")
            if (entry.word, entry.ipa) in known:
                raise ValueError(
                    f"{source}:{lineno}: duplicate row for {entry.word!r} {entry.ipa!r}"
                )
            known[(entry.word, entry.ipa)] = entry
    return known
