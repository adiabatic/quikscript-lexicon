from __future__ import annotations

import csv
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from qslex.mapping import open_data
from qslex.readlex import Row

TAGS_FILE = "var-tags.tsv"
TAGS_HEADER = ["tag", "canonical", "policy", "rows", "words", "note"]
POLICIES = {"keep", "drop"}

# The four tags upstream's README and data model actually sanction. Anything else is a
# defect, so it has to enumerate the words it touches: that bounds the damage, gives
# the upstream report its row list, and makes an upstream fix show up here as a rule
# that stopped matching rather than as a silent change of contents.
DOCUMENTED = frozenset({"RRP", "TrapBath", "GenAm", "GenAus"})


@dataclass(frozen=True)
class VarTag:
    tag: str
    canonical: str
    policy: str
    rows: int
    words: str
    note: str

    @property
    def declared_words(self) -> tuple[str, ...]:
        return tuple(w.strip() for w in self.words.split(",") if w.strip())

    @property
    def kept(self) -> bool:
        return self.policy == "keep"


Tags = dict[str, VarTag]


def load_var_tags(path: Path | None = None) -> Tags:
    known: Tags = {}
    with open_data(path, TAGS_FILE) as (f, source):
        reader = csv.reader(f, delimiter="\t")
        header = next(reader)
        if header != TAGS_HEADER:
            raise ValueError(f"unexpected header in {source}: {header}")
        for lineno, row in enumerate(reader, start=2):
            if len(row) != len(TAGS_HEADER):
                raise ValueError(
                    f"{source}:{lineno}: expected {len(TAGS_HEADER)} fields, "
                    f"got {len(row)}"
                )
            tag, canonical, policy, rows, words, note = row
            if not tag:
                raise ValueError(f"{source}:{lineno}: empty tag")
            if policy not in POLICIES:
                raise ValueError(
                    f"{source}:{lineno}: policy must be one of {sorted(POLICIES)}, "
                    f"got {policy!r}"
                )
            try:
                count = int(rows)
            except ValueError as error:
                raise ValueError(
                    f"{source}:{lineno}: rows must be a number: {error}"
                ) from error
            entry = VarTag(tag, canonical, policy, count, words, note)
            if tag in known:
                raise ValueError(f"{source}:{lineno}: duplicate row for {tag!r}")
            if tag not in DOCUMENTED and not entry.declared_words:
                raise ValueError(
                    f"{source}:{lineno}: {tag!r} is not one of upstream's documented "
                    f"tags {sorted(DOCUMENTED)}, so it must declare the words it covers"
                )
            if not note:
                raise ValueError(f"{source}:{lineno}: every tag needs a note")
            known[tag] = entry
    for entry in known.values():
        if entry.canonical not in known:
            raise ValueError(
                f"{TAGS_FILE}: {entry.tag!r} normalises to {entry.canonical!r}, "
                f"which has no row of its own"
            )
        if known[entry.canonical].policy != entry.policy:
            raise ValueError(
                f"{TAGS_FILE}: {entry.tag!r} normalises to {entry.canonical!r} but "
                f"they disagree on policy"
            )
    return known


def canonical(tags: Tags, tag: str) -> str:
    entry = tags.get(tag)
    if entry is None:
        raise ValueError(
            f"{TAGS_FILE} has no policy for the variant tag {tag!r}; the corpus has "
            f"grown a tag nobody has ruled on"
        )
    return entry.canonical


def kept(tags: Tags, tag: str) -> bool:
    """Whether a row wearing this tag belongs to the RRP family the lexicon spells."""
    return tags[canonical(tags, tag)].kept


def select(tags: Tags, rows: Iterable[Row]) -> tuple[Row, ...]:
    return tuple(row for row in rows if kept(tags, row.var))
