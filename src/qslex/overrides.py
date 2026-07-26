from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from qslex.mapping import Mapping
from qslex.tables import Declares, rows_of

OVERRIDES_FILE = "ipa-overrides.tsv"
OVERRIDES_HEADER = [
    "ipa",
    "token",
    "condition",
    "words",
    "authority",
    "note",
]


@dataclass(frozen=True)
class Override(Declares):
    ipa: str
    token: str
    condition: str
    words: str
    authority: str
    note: str


Overrides = dict[str, Override]


def load_overrides(mapping: Mapping, path: Path | None = None) -> Overrides:
    rules: list[Override] = []
    for lineno, source, row in rows_of(path, OVERRIDES_FILE, OVERRIDES_HEADER):
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
        if not rule.declared_words:
            raise ValueError(f"{source}:{lineno}: no words declared")
        rules.append(rule)

    by_ipa: Overrides = {}
    for rule in rules:
        if rule.ipa in by_ipa:
            raise ValueError(f"duplicate override for {rule.ipa!r}")
        by_ipa[rule.ipa] = rule
    return by_ipa
