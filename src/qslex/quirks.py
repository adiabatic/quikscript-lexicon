from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from qslex.mapping import repo_root

QUIRKS_HEADER = ["scope", "match", "replacement", "words", "note"]
SCOPES = {"row", "sub", "regex"}


@dataclass(frozen=True)
class QuirkRule:
    scope: str
    match: str
    replacement: str
    words: str
    note: str


def default_quirks_path() -> Path:
    return repo_root() / "data" / "ipa-quirks.tsv"


def load_quirks(path: Path | None = None) -> tuple[QuirkRule, ...]:
    path = path if path is not None else default_quirks_path()
    rules: list[QuirkRule] = []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.reader(f, delimiter="\t")
        header = next(reader)
        if header != QUIRKS_HEADER:
            raise ValueError(f"unexpected header in {path}: {header}")
        for lineno, row in enumerate(reader, start=2):
            if len(row) != len(QUIRKS_HEADER):
                raise ValueError(
                    f"{path}:{lineno}: expected {len(QUIRKS_HEADER)} fields"
                )
            rule = QuirkRule(*row)
            if rule.scope not in SCOPES:
                raise ValueError(f"{path}:{lineno}: unknown scope {rule.scope!r}")
            rules.append(rule)
    return tuple(rules)


def normalize(ipa: str, rules: tuple[QuirkRule, ...]) -> tuple[str, tuple[int, ...]]:
    applied: list[int] = []
    for index, rule in enumerate(rules):
        if rule.scope == "row":
            if ipa == rule.match:
                ipa = rule.replacement
                applied.append(index)
        elif rule.scope == "sub":
            if rule.match in ipa:
                ipa = ipa.replace(rule.match, rule.replacement)
                applied.append(index)
        else:
            ipa, count = re.subn(rule.match, rule.replacement, ipa)
            if count:
                applied.append(index)
    return ipa, tuple(applied)
