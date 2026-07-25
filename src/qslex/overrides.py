from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from qslex.mapping import Mapping, open_data

POSITIVE_INTEGER = re.compile(r"[1-9][0-9]*\Z")

OVERRIDES_FILE = "ipa-overrides.tsv"
OVERRIDES_HEADER = [
    "ipa",
    "token",
    "occurrence",
    "condition",
    "words",
    "authority",
    "note",
]
ALL_OCCURRENCES = "*"


@dataclass(frozen=True)
class Override:
    ipa: str
    token: str
    occurrence: str
    condition: str
    words: str
    authority: str
    note: str

    def applies_to(self, occurrence: int) -> bool:
        return self.occurrence in (ALL_OCCURRENCES, str(occurrence))

    @property
    def declared_words(self) -> tuple[str, ...]:
        return tuple(w.strip() for w in self.words.split(",") if w.strip())


Overrides = dict[str, tuple[Override, ...]]


def load_overrides(mapping: Mapping, path: Path | None = None) -> Overrides:
    rules: list[Override] = []
    with open_data(path, OVERRIDES_FILE) as (f, source):
        reader = csv.reader(f, delimiter="\t")
        header = next(reader)
        if header != OVERRIDES_HEADER:
            raise ValueError(f"unexpected header in {source}: {header}")
        for lineno, row in enumerate(reader, start=2):
            if len(row) != len(OVERRIDES_HEADER):
                raise ValueError(
                    f"{source}:{lineno}: expected {len(OVERRIDES_HEADER)} fields, "
                    f"got {len(row)}"
                )
            rule = Override(*row)
            conditions = mapping.lookup.get(rule.token)
            if conditions is None:
                raise ValueError(f"{source}:{lineno}: unknown token {rule.token!r}")
            if "" in conditions:
                raise ValueError(
                    f"{source}:{lineno}: {rule.token!r} is unconditional; "
                    f"nothing to override"
                )
            if rule.condition not in conditions:
                raise ValueError(
                    f"{source}:{lineno}: {rule.token!r} has no condition "
                    f"{rule.condition!r} (have {sorted(conditions)})"
                )
            if rule.token not in rule.ipa:
                raise ValueError(
                    f"{source}:{lineno}: {rule.ipa!r} does not contain {rule.token!r}"
                )
            if rule.occurrence != ALL_OCCURRENCES and not POSITIVE_INTEGER.match(
                rule.occurrence
            ):
                raise ValueError(
                    f"{source}:{lineno}: occurrence must be {ALL_OCCURRENCES!r} or a "
                    f"1-based integer, got {rule.occurrence!r}"
                )
            if not rule.declared_words:
                raise ValueError(f"{source}:{lineno}: no words declared")
            rules.append(rule)

    by_ipa: Overrides = {}
    seen: set[tuple[str, str, str]] = set()
    for rule in rules:
        key = (rule.ipa, rule.token, rule.occurrence)
        if key in seen:
            raise ValueError(f"duplicate override for {key}")
        seen.add(key)
        by_ipa[rule.ipa] = by_ipa.get(rule.ipa, ()) + (rule,)
    return by_ipa
