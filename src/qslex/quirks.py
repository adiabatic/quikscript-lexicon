from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from qslex.mapping import open_data

QUIRKS_FILE = "ipa-quirks.tsv"
QUIRKS_HEADER = ["scope", "match", "replacement", "words", "note"]
SCOPES = {"row", "sub", "regex"}


@dataclass(frozen=True)
class QuirkRule:
    scope: str
    match: str
    replacement: str
    words: str
    note: str

    @property
    def declared_words(self) -> tuple[str, ...]:
        return tuple(w.strip() for w in self.words.split(",") if w.strip())


def load_quirks(path: Path | None = None) -> tuple[QuirkRule, ...]:
    rules: list[QuirkRule] = []
    with open_data(path, QUIRKS_FILE) as (f, source):
        reader = csv.reader(f, delimiter="\t")
        header = next(reader)
        if header != QUIRKS_HEADER:
            raise ValueError(f"unexpected header in {source}: {header}")
        for lineno, row in enumerate(reader, start=2):
            if len(row) != len(QUIRKS_HEADER):
                raise ValueError(
                    f"{source}:{lineno}: expected {len(QUIRKS_HEADER)} fields"
                )
            rule = QuirkRule(*row)
            if rule.scope not in SCOPES:
                raise ValueError(f"{source}:{lineno}: unknown scope {rule.scope!r}")
            if not rule.match:
                raise ValueError(f"{source}:{lineno}: empty match")
            if not rule.declared_words:
                raise ValueError(f"{source}:{lineno}: no words declared")
            if rule.scope == "regex":
                try:
                    re.compile(rule.match)
                except re.error as error:
                    raise ValueError(
                        f"{source}:{lineno}: bad regex: {error}"
                    ) from error
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
