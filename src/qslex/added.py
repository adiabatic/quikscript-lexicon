from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from qslex.letters import unknown_names
from qslex.readlex import Row
from qslex.tables import rows_of

ADDED_FILE = "added-words.tsv"
ADDED_HEADER = ["word", "pos", "ipa", "shavian", "freq", "qs", "source", "note"]

SHAVIAN_BLOCK = range(0x10450, 0x10480)


@dataclass(frozen=True)
class AddedWord:
    """An entry the lexicon has that ReadLex does not.

    It has a corpus row’s word, part-of-speech tag, IPA, Shavian and frequency, plus `qs`, `source` and `note`. The segment mapping and Read’s rules spell it from the corpus-row fields, as they spell every corpus row. `qs` is the expected Senior spelling. The build never reads it, and the validator fails if the rules stop producing it.
    """

    word: str
    pos: str
    ipa: str
    shavian: str
    frequency: int
    qs: str
    source: str
    note: str

    @property
    def headword(self) -> str:
        """Upstream’s key format, so a consumer grouping the lexicon JSON cannot tell added entries from corpus entries by their keys."""
        return f"{self.word}_{self.pos}_{self.shavian}"

    @property
    def row(self) -> Row:
        """The entry as a corpus `Row` with an empty `var` tag.

        An added row belongs to no accent, so `var` is empty rather than `RRP`. The build adds these rows after the row policy has run. `variants.kept` raises on an empty tag, so an added row that reached the row policy would fail the build instead of being counted in the per-tag row counts in var-tags.tsv.
        """
        return Row(
            headword=self.headword,
            word=self.word,
            shavian=self.shavian,
            pos=self.pos,
            ipa=self.ipa,
            frequency=self.frequency,
            var="",
        )


def load_added_words(path: Path | None = None) -> tuple[AddedWord, ...]:
    added: list[AddedWord] = []
    seen: set[tuple[str, str]] = set()
    for lineno, source, row in rows_of(path, ADDED_FILE, ADDED_HEADER):
        word, pos, ipa, shavian, freq, qs, authority, note = row
        if not word or not pos or not ipa:
            raise ValueError(f"{source}:{lineno}: word, pos and ipa are all required")
        if word != word.lower():
            raise ValueError(
                f"{source}:{lineno}: {word!r} must be lowercase, as every corpus row is"
            )
        try:
            frequency = int(freq)
        except ValueError as error:
            raise ValueError(
                f"{source}:{lineno}: freq must be a number: {error}"
            ) from error
        if not shavian or any(ord(c) not in SHAVIAN_BLOCK for c in shavian):
            raise ValueError(
                f"{source}:{lineno}: shavian must be written in the Shavian block, "
                f"got {shavian!r}"
            )
        if not qs.startswith("·"):
            raise ValueError(f"{source}:{lineno}: qs must be ·-prefixed: {qs!r}")
        unknown = unknown_names(qs)
        if unknown:
            raise ValueError(f"{source}:{lineno}: unknown letter names {unknown}")
        if not authority:
            raise ValueError(
                f"{source}:{lineno}: a word the corpus does not carry needs a source "
                f"saying where it comes from"
            )
        if not note:
            raise ValueError(f"{source}:{lineno}: every added word needs a note")
        if (word, pos) in seen:
            raise ValueError(f"{source}:{lineno}: duplicate row for {(word, pos)}")
        seen.add((word, pos))
        added.append(AddedWord(word, pos, ipa, shavian, frequency, qs, authority, note))
    return tuple(added)


def added_rows(added: tuple[AddedWord, ...]) -> tuple[Row, ...]:
    return tuple(entry.row for entry in added)
