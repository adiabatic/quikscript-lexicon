from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from qslex.letters import unknown_names
from qslex.mapping import open_data
from qslex.rules import RULE_IDS

SPELLINGS_FILE = "manual-spellings.tsv"
SPELLINGS_HEADER = [
    "word",
    "pos",
    "column",
    "kind",
    "spelling",
    "source",
    "rule",
    "note",
]
COLUMNS = {"senior", "ligature"}
KINDS = {"word", "terminal", "prefix"}
SOURCES = {"manual", "derived", "modernised"}
LIGATURE_RULE = "section-2"
SIGN_ANCHORS = {"junior-contractions", "common-words"}
ANCHORS = set(RULE_IDS) | SIGN_ANCHORS | {LIGATURE_RULE}


@dataclass(frozen=True)
class Example:
    word: str
    pos: str
    column: str
    kind: str
    spelling: str
    source: str
    rule: str
    note: str

    def matches(self, produced: str) -> bool:
        if self.kind == "terminal":
            return produced.endswith(self.spelling)
        if self.kind == "prefix":
            return produced.startswith(self.spelling)
        return produced == self.spelling


def load_examples(path: Path | None = None) -> tuple[Example, ...]:
    examples: list[Example] = []
    seen: set[tuple[str, str, str, str]] = set()
    with open_data(path, SPELLINGS_FILE) as (f, source):
        reader = csv.reader(f, delimiter="\t")
        header = next(reader)
        if header != SPELLINGS_HEADER:
            raise ValueError(f"unexpected header in {source}: {header}")
        for lineno, row in enumerate(reader, start=2):
            if len(row) != len(SPELLINGS_HEADER):
                raise ValueError(
                    f"{source}:{lineno}: expected {len(SPELLINGS_HEADER)} fields, "
                    f"got {len(row)}"
                )
            example = Example(*row)
            if example.column not in COLUMNS:
                raise ValueError(
                    f"{source}:{lineno}: column must be one of {sorted(COLUMNS)}, "
                    f"got {example.column!r}"
                )
            if example.kind not in KINDS:
                raise ValueError(
                    f"{source}:{lineno}: kind must be one of {sorted(KINDS)}, "
                    f"got {example.kind!r}"
                )
            if example.source not in SOURCES:
                raise ValueError(
                    f"{source}:{lineno}: source must be one of {sorted(SOURCES)}, "
                    f"got {example.source!r}"
                )
            if example.rule not in ANCHORS:
                raise ValueError(
                    f"{source}:{lineno}: {example.rule!r} is not a rule anchor"
                )
            if not example.spelling.startswith("·"):
                raise ValueError(
                    f"{source}:{lineno}: spelling must be ·-prefixed: "
                    f"{example.spelling!r}"
                )
            unknown = unknown_names(example.spelling)
            if unknown:
                raise ValueError(f"{source}:{lineno}: unknown letter names {unknown}")
            if example.source != "manual" and not example.note:
                raise ValueError(
                    f"{source}:{lineno}: a {example.source} spelling needs a note "
                    f"saying how it was reached"
                )
            if example.column == "ligature" and example.rule != LIGATURE_RULE:
                raise ValueError(
                    f"{source}:{lineno}: a ligature spelling belongs to "
                    f"{LIGATURE_RULE!r}, not {example.rule!r}"
                )
            key = (example.word, example.pos, example.column, example.rule)
            if key in seen:
                raise ValueError(f"{source}:{lineno}: duplicate row for {key}")
            seen.add(key)
            examples.append(example)
    return tuple(examples)
