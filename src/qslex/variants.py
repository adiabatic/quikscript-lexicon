from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from qslex.readlex import Row
from qslex.tables import HasWordList, rows_of

TAGS_FILE = "var-tags.tsv"
TAGS_HEADER = ["tag", "canonical", "policy", "rows", "words", "note"]
POLICIES = {"keep", "drop"}

# The four tags that upstream’s README and data model document. Any other tag is a defect, so its row must list the words it covers. The validator fails if the tag appears on a word the row does not list. The list also gives the upstream bug report its words. When upstream fixes the tag, the validator fails on the listed words it no longer covers.
DOCUMENTED = frozenset({"RRP", "TrapBath", "GenAm", "GenAus"})


@dataclass(frozen=True)
class VarTag(HasWordList):
    tag: str
    canonical: str
    policy: str
    rows: int
    words: str
    note: str

    @property
    def kept(self) -> bool:
        return self.policy == "keep"


Tags = dict[str, VarTag]


def load_var_tags(path: Path | None = None) -> Tags:
    known: Tags = {}
    for lineno, source, row in rows_of(path, TAGS_FILE, TAGS_HEADER):
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
        if tag not in DOCUMENTED and not entry.listed_words:
            raise ValueError(
                f"{source}:{lineno}: {tag!r} is not one of upstream’s documented "
                f"tags {sorted(DOCUMENTED)}, so it must list the words it covers"
            )
        if not note:
            raise ValueError(f"{source}:{lineno}: every tag needs a note")
        known[tag] = entry
    for entry in known.values():
        if entry.canonical not in known:
            raise ValueError(
                f"{TAGS_FILE}: {entry.tag!r} normalizes to {entry.canonical!r}, "
                f"which has no row of its own"
            )
        if known[entry.canonical].policy != entry.policy:
            raise ValueError(
                f"{TAGS_FILE}: {entry.tag!r} normalizes to {entry.canonical!r} but "
                f"they disagree on policy"
            )
    return known


def kept(tags: Tags, tag: str) -> bool:
    """Whether a row with this tag belongs to the RRP family the lexicon spells.

    `load_var_tags` fails if a tag and the tag it normalizes to have different policies, so the row’s own policy is also the canonical tag’s policy.
    """
    entry = tags.get(tag)
    if entry is None:
        raise ValueError(
            f"{TAGS_FILE} has no policy for the variant tag {tag!r}, which appears "
            f"in the corpus"
        )
    return entry.kept


def select(tags: Tags, rows: Iterable[Row]) -> tuple[Row, ...]:
    return tuple(row for row in rows if kept(tags, row.var))
