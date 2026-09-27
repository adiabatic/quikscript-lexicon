from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from qslex.letters import unknown_names
from qslex.tables import rows_of

PASSAGES_FILE = "manual-passages.tsv"
PASSAGES_HEADER = ["passage", "index", "latin", "spelling", "outcome", "ours", "note"]

SENIOR = ("senior", "x-letter")
JUNIOR = ("junior",)
UNREPRODUCED = frozenset({"differs", "absent"})

# Separates the spellings in a row’s `ours` column when the lexicon has more than one spelling for the word.
ALTERNATIVES = " / "


@dataclass(frozen=True)
class Specimen:
    level: str
    words: int

    @property
    def columns(self) -> tuple[str, ...]:
        return JUNIOR if self.level == "junior" else SENIOR

    @property
    def outcomes(self) -> frozenset[str]:
        allowed = set(self.columns) | UNREPRODUCED
        if self.level == "senior":
            allowed.add("contraction")
        return frozenset(allowed)


# Every specimen passage the Manual prints, keyed by its anchor in the AMS transcription. The transcription gives each Senior passage’s Latin text in a `data-orthodox` attribute. The four Junior nursery rhymes have no such attribute, so their Latin was transcribed by hand. `load_passages` fails if a passage has a different number of rows than its word count here. The counts are of the words a passage spells, not its tokens. A punctuation mark that stands alone is dropped and leaves a gap in the index.
SPECIMENS: dict[str, Specimen] = {
    "no-how": Specimen("senior", 56),
    "parental-advice": Specimen("senior", 51),
    "gown-shop": Specimen("senior", 64),
    "rip-van-winkle": Specimen("senior", 120),
    "senior-examples-1": Specimen("senior", 134),
    "senior-examples-2": Specimen("senior", 51),
    "senior-examples-3": Specimen("senior", 66),
    "bo-peep": Specimen("junior", 25),
    "jack-horner": Specimen("junior", 29),
    "ride-a-cock-horse": Specimen("junior", 31),
    "marys-lamb": Specimen("junior", 47),
}


@dataclass(frozen=True)
class PassageWord:
    passage: str
    index: int
    latin: str
    spelling: str
    outcome: str
    ours: str
    note: str

    @property
    def columns(self) -> tuple[str, ...]:
        return SPECIMENS[self.passage].columns


def load_passages(path: Path | None = None) -> tuple[PassageWord, ...]:
    """The Manual’s specimen passages, word by word, with each word’s outcome.

    An outcome names the column that reproduces the Manual’s spelling, or says why none does. `contraction` means Read used a contraction that `contractions.tsv` lists, whatever that row’s `authority`. The lexicon applies those contractions to no column. `absent` means ReadLex has no entry for the word. `differs` means the Manual and the lexicon disagree. A `differs` row records the lexicon’s spelling in its `ours` column, and the validator fails if that spelling changes.
    """
    words: list[PassageWord] = []
    last: dict[str, int] = {}
    counts: dict[str, int] = dict.fromkeys(SPECIMENS, 0)
    for lineno, source, row in rows_of(path, PASSAGES_FILE, PASSAGES_HEADER):
        passage, index, latin, spelling, outcome, ours, note = row
        specimen = SPECIMENS.get(passage)
        if specimen is None:
            raise ValueError(f"{source}:{lineno}: unknown passage {passage!r}")
        try:
            position = int(index)
        except ValueError as error:
            raise ValueError(f"{source}:{lineno}: {error}") from error
        if position <= last.get(passage, -1):
            raise ValueError(
                f"{source}:{lineno}: {passage} word {position} is out of order"
            )
        last[passage] = position
        counts[passage] += 1
        if outcome not in specimen.outcomes:
            raise ValueError(
                f"{source}:{lineno}: a {specimen.level} passage cannot have "
                f"outcome {outcome!r} (have {sorted(specimen.outcomes)})"
            )
        if not latin:
            raise ValueError(f"{source}:{lineno}: no Latin word")
        for label, value in (("spelling", spelling), ("ours", ours)):
            unknown = unknown_names(value.replace(ALTERNATIVES, ""))
            if unknown:
                raise ValueError(
                    f"{source}:{lineno}: unknown letter names in {label}: {unknown}"
                )
        if not spelling.startswith("·"):
            raise ValueError(
                f"{source}:{lineno}: spelling must be ·-prefixed: {spelling!r}"
            )
        if bool(ours) != (outcome == "differs"):
            raise ValueError(
                f"{source}:{lineno}: only a differing word records what this "
                f"lexicon spells instead"
            )
        if bool(note) != (outcome in UNREPRODUCED):
            raise ValueError(
                f"{source}:{lineno}: a {outcome!r} word needs a note saying why, "
                f"and no other kind takes one"
            )
        words.append(
            PassageWord(passage, position, latin, spelling, outcome, ours, note)
        )
    wrong = {p: n for p, n in counts.items() if n != SPECIMENS[p].words}
    if wrong:
        raise ValueError(
            f"{PASSAGES_FILE} has "
            + ", ".join(
                f"{n} words of {p} (expected {SPECIMENS[p].words})"
                for p, n in sorted(wrong.items())
            )
        )
    return tuple(words)
