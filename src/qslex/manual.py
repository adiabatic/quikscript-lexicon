from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from qslex.letters import unknown_names
from qslex.rules import RULE_IDS
from qslex.tables import rows_of

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
COLUMNS = {"senior", "x-letter"}
KINDS = {"word", "terminal", "prefix"}
SOURCES = {"manual", "derived", "modernised"}
X_LETTER_RULE = "section-2"
SIGN_ANCHORS = {"junior-contractions", "common-words"}
ANCHORS = set(RULE_IDS) | SIGN_ANCHORS | {X_LETTER_RULE}


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
    for lineno, source, row in rows_of(path, SPELLINGS_FILE, SPELLINGS_HEADER):
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
                f"{source}:{lineno}: spelling must be ·-prefixed: {example.spelling!r}"
            )
        unknown = unknown_names(example.spelling)
        if unknown:
            raise ValueError(f"{source}:{lineno}: unknown letter names {unknown}")
        if example.source != "manual" and not example.note:
            raise ValueError(
                f"{source}:{lineno}: a {example.source} spelling needs a note "
                f"saying how it was derived"
            )
        if example.column == "x-letter" and example.rule != X_LETTER_RULE:
            raise ValueError(
                f"{source}:{lineno}: an x-letter spelling belongs to "
                f"{X_LETTER_RULE!r}, not {example.rule!r}"
            )
        key = (example.word, example.pos, example.column, example.rule)
        if key in seen:
            raise ValueError(f"{source}:{lineno}: duplicate row for {key}")
        seen.add(key)
        examples.append(example)
    return tuple(examples)
