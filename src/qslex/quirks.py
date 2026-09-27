from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from qslex.tables import HasWordList, rows_of

QUIRKS_FILE = "ipa-quirks.tsv"
QUIRKS_HEADER = ["scope", "match", "replacement", "words", "note"]
SCOPES = {"row", "sub", "regex"}


@dataclass(frozen=True)
class QuirkRule(HasWordList):
    scope: str
    match: str
    replacement: str
    words: str
    note: str


def load_quirks(path: Path | None = None) -> tuple[QuirkRule, ...]:
    rules: list[QuirkRule] = []
    for lineno, source, row in rows_of(path, QUIRKS_FILE, QUIRKS_HEADER):
        rule = QuirkRule(*row)
        if rule.scope not in SCOPES:
            raise ValueError(f"{source}:{lineno}: unknown scope {rule.scope!r}")
        if not rule.match:
            raise ValueError(f"{source}:{lineno}: empty match")
        if not rule.listed_words:
            raise ValueError(f"{source}:{lineno}: no words listed")
        if rule.scope == "regex":
            try:
                re.compile(rule.match)
            except re.error as error:
                raise ValueError(f"{source}:{lineno}: bad regex: {error}") from error
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
