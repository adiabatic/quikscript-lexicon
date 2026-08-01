from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from qslex.letters import unknown_names
from qslex.tables import rows_of

PASSAGES_FILE = "manual-passages.tsv"
PASSAGES_HEADER = ["passage", "index", "latin", "spelling", "verdict", "ours", "note"]

SENIOR = ("senior", "x-letter")
JUNIOR = ("junior",)
UNREPRODUCED = frozenset({"differs", "absent"})

# A word with more than one spelling in the lexicon has them all recorded, joined.
ALTERNATIVES = " / "


@dataclass(frozen=True)
class Specimen:
    level: str
    words: int

    @property
    def columns(self) -> tuple[str, ...]:
        return JUNIOR if self.level == "junior" else SENIOR

    @property
    def verdicts(self) -> frozenset[str]:
        allowed = set(self.columns) | UNREPRODUCED
        if self.level == "senior":
            allowed.add("contraction")
        return frozenset(allowed)


# Every specimen passage the Manual prints, keyed by its anchor in the AMS
# transcription. The Senior ones carry a Latin transcription of their own, in the
# `data-orthodox` attribute; the four Junior nursery rhymes do not, and their Latin was
# transcribed by hand. The word counts are pinned so that a passage cannot quietly lose
# rows: they count the words a passage spells, not its tokens, so a punctuation mark
# standing alone is dropped and leaves a gap in the index.
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
    verdict: str
    ours: str
    note: str

    @property
    def columns(self) -> tuple[str, ...]:
        return SPECIMENS[self.passage].columns


def load_passages(path: Path | None = None) -> tuple[PassageWord, ...]:
    """The Manual's specimen passages, word by word, with each word's verdict.

    A verdict names the column that reproduces the Manual's spelling, or says why
    nothing does: `contraction` where Read reached for one of the contractions
    `contractions.tsv` carries, under either of its Manual anchors, which this lexicon
    applies to no column; `absent` where ReadLex has no entry for the word at all;
    `differs` where the two genuinely disagree, in which case the row pins what this
    lexicon produces so that the disagreement cannot drift unnoticed.
    """
    words: list[PassageWord] = []
    last: dict[str, int] = {}
    counts: dict[str, int] = dict.fromkeys(SPECIMENS, 0)
    for lineno, source, row in rows_of(path, PASSAGES_FILE, PASSAGES_HEADER):
        passage, index, latin, spelling, verdict, ours, note = row
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
        if verdict not in specimen.verdicts:
            raise ValueError(
                f"{source}:{lineno}: a {specimen.level} passage cannot have "
                f"verdict {verdict!r} (have {sorted(specimen.verdicts)})"
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
        if bool(ours) != (verdict == "differs"):
            raise ValueError(
                f"{source}:{lineno}: only a differing word records what this "
                f"lexicon spells instead"
            )
        if bool(note) != (verdict in UNREPRODUCED):
            raise ValueError(
                f"{source}:{lineno}: a {verdict!r} word needs a note saying why, "
                f"and no other kind takes one"
            )
        words.append(
            PassageWord(passage, position, latin, spelling, verdict, ours, note)
        )
    wrong = {p: n for p, n in counts.items() if n != SPECIMENS[p].words}
    if wrong:
        raise ValueError(
            f"{PASSAGES_FILE} carries "
            + ", ".join(
                f"{n} words of {p} (expected {SPECIMENS[p].words})"
                for p, n in sorted(wrong.items())
            )
        )
    return tuple(words)
