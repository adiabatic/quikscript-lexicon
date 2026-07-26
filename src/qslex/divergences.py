from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from qslex.tables import rows_of

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
    for lineno, source, row in rows_of(path, DIVERGENCES_FILE, DIVERGENCES_HEADER):
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
