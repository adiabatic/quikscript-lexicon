from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from qslex.letters import Letter, Letters, names, parse, unknown_names
from qslex.mapping import open_data

SIGNS_FILE = "word-signs.tsv"
SIGNS_HEADER = ["word", "pos", "tier", "senior", "junior", "full", "authority", "note"]
TIERS = {"core", "standard", "abbreviation"}
SIGN_AUTHORITIES = {"junior-contractions", "common-words"}

CONTRACTIONS_FILE = "contractions.tsv"
CONTRACTIONS_HEADER = ["word", "pos", "kind", "contraction", "authority", "note"]
KINDS = {"word", "clitic"}
CONTRACTION_AUTHORITY = "senior-contractions"

# The core eight the Manual sanctions for Junior writing too, in its own order.
CORE_EIGHT = ("the", "of", "and", "to", "it", "is", "for", "be")

BOUNDARY = re.compile(r"([ -])")
DIVIDERS = frozenset(" -")


@dataclass(frozen=True)
class Sign:
    word: str
    pos: str
    tier: str
    senior: str
    junior: str
    full: str
    authority: str
    note: str

    def column(self, name: str) -> str:
        return self.junior if name == "junior" and self.junior else self.senior


@dataclass(frozen=True)
class Contraction:
    word: str
    pos: str
    kind: str
    contraction: str
    authority: str
    note: str


Signs = dict[tuple[str, str], Sign]


def load_word_signs(path: Path | None = None) -> Signs:
    known: Signs = {}
    with open_data(path, SIGNS_FILE) as (f, source):
        reader = csv.reader(f, delimiter="\t")
        header = next(reader)
        if header != SIGNS_HEADER:
            raise ValueError(f"unexpected header in {source}: {header}")
        for lineno, row in enumerate(reader, start=2):
            if len(row) != len(SIGNS_HEADER):
                raise ValueError(
                    f"{source}:{lineno}: expected {len(SIGNS_HEADER)} fields, "
                    f"got {len(row)}"
                )
            sign = Sign(*row)
            if sign.tier not in TIERS:
                raise ValueError(
                    f"{source}:{lineno}: tier must be one of {sorted(TIERS)}, "
                    f"got {sign.tier!r}"
                )
            if sign.authority not in SIGN_AUTHORITIES:
                raise ValueError(
                    f"{source}:{lineno}: {sign.authority!r} is not a Manual anchor "
                    f"for this table (have {sorted(SIGN_AUTHORITIES)})"
                )
            if sign.full and sign.tier != "core":
                raise ValueError(
                    f"{source}:{lineno}: an uncontracted form is only recorded for "
                    f"the core eight, not for a {sign.tier} word"
                )
            for label, spelling in (
                ("senior", sign.senior),
                ("junior", sign.junior),
                ("full", sign.full),
            ):
                if label == "senior" and not spelling:
                    raise ValueError(f"{source}:{lineno}: no senior spelling")
                if spelling and not spelling.startswith("·"):
                    raise ValueError(
                        f"{source}:{lineno}: {label} spelling must be ·-prefixed: "
                        f"{spelling!r}"
                    )
                unknown = unknown_names(spelling)
                if unknown:
                    raise ValueError(
                        f"{source}:{lineno}: unknown letter names in {label}: {unknown}"
                    )
            if sign.junior == sign.senior:
                raise ValueError(
                    f"{source}:{lineno}: leave junior empty where it does not diverge"
                )
            key = (sign.word, sign.pos)
            if key in known:
                raise ValueError(f"{source}:{lineno}: duplicate row for {key}")
            if sign.pos and (sign.word, "") in known:
                raise ValueError(
                    f"{source}:{lineno}: {sign.word!r} already has a row for every "
                    f"part of speech, so a {sign.pos} row can never be reached"
                )
            known[key] = sign
    missing = [word for word in CORE_EIGHT if (word, "") not in known]
    if missing:
        raise ValueError(f"{SIGNS_FILE} is missing core word signs: {missing}")
    return known


def load_contractions(path: Path | None = None) -> tuple[Contraction, ...]:
    out: list[Contraction] = []
    seen: set[tuple[str, str]] = set()
    with open_data(path, CONTRACTIONS_FILE) as (f, source):
        reader = csv.reader(f, delimiter="\t")
        header = next(reader)
        if header != CONTRACTIONS_HEADER:
            raise ValueError(f"unexpected header in {source}: {header}")
        for lineno, row in enumerate(reader, start=2):
            if len(row) != len(CONTRACTIONS_HEADER):
                raise ValueError(
                    f"{source}:{lineno}: expected {len(CONTRACTIONS_HEADER)} fields, "
                    f"got {len(row)}"
                )
            entry = Contraction(*row)
            if entry.kind not in KINDS:
                raise ValueError(
                    f"{source}:{lineno}: kind must be one of {sorted(KINDS)}, "
                    f"got {entry.kind!r}"
                )
            if entry.authority != CONTRACTION_AUTHORITY:
                raise ValueError(
                    f"{source}:{lineno}: {entry.authority!r} is not "
                    f"{CONTRACTION_AUTHORITY!r}"
                )
            unknown = unknown_names(entry.contraction)
            if unknown:
                raise ValueError(f"{source}:{lineno}: unknown letter names {unknown}")
            if entry.kind == "clitic" and not entry.note:
                raise ValueError(
                    f"{source}:{lineno}: a clitic is generalised rather than listed, "
                    f"so it needs a note saying from what"
                )
            key = (entry.word, entry.pos)
            if key in seen:
                raise ValueError(f"{source}:{lineno}: duplicate row for {key}")
            seen.add(key)
            out.append(entry)
    return tuple(out)


def sign_for(signs: Signs, word: str, pos: str) -> Sign | None:
    """The row governing this word, preferring one tagged for its part of speech."""
    return signs.get((word, pos)) or signs.get((word, ""))


def components(latin: str) -> tuple[str, ...]:
    """A phrase entry's words and the separators between them, in order.

    An entry that begins or ends with a separator keeps the empty word on that side,
    so the result lines up one for one with the runs of a spelling for the same entry.
    """
    return tuple(BOUNDARY.split(latin))


def _lookup(signs: Signs, part: str, pos: str, single: bool) -> Sign | None:
    """A phrase entry's tag belongs to the phrase, so only general rows apply inside."""
    return sign_for(signs, part, pos) if single else signs.get((part, ""))


def _runs(letters: Letters) -> list[Letters]:
    """Split a spelling at the separators the tokenizer passed through."""
    runs: list[Letters] = []
    current: list[Letter] = []
    for letter in letters:
        if letter.name in DIVIDERS:
            runs.append(tuple(current))
            runs.append((letter,))
            current = []
        else:
            current.append(letter)
    runs.append(tuple(current))
    return runs


def _divider(run: Letters) -> str:
    return run[0].name if len(run) == 1 and run[0].name in DIVIDERS else ""


def _aligned(parts: tuple[str, ...], runs: list[Letters]) -> bool:
    """Whether the Latin words and the spelling's runs are the same shape.

    Equal counts are not enough: a Latin hyphen facing a spelt space would let a
    substitution cross a boundary that is not the one it matched.
    """
    if len(parts) != len(runs):
        return False
    return all(
        (part if part in DIVIDERS else "") == _divider(run)
        for part, run in zip(parts, runs, strict=True)
    )


def apply_signs(
    latin: str, pos: str, letters: Letters, signs: Signs, column: str
) -> tuple[Letters, tuple[str, ...], tuple[tuple[str, str], ...]]:
    """Substitute the Manual's word signs and standard outlines into a spelling.

    A single-word entry consults its own part-of-speech tag; a phrase entry is matched
    word by word. Nothing is substituted unless the Latin words and the spelling's runs
    are the same shape, which is what keeps to-day (one run, two Latin words) and dhs
    (one Latin word, four) intact. Returns the spelling, the words it changed, and the
    rows it consulted.
    """
    parts = components(latin)
    runs = _runs(letters)
    if not _aligned(parts, runs):
        return letters, (), ()
    single = len(parts) == 1
    out: list[Letter] = []
    applied: list[str] = []
    consulted: list[tuple[str, str]] = []
    for part, run in zip(parts, runs, strict=True):
        sign = _lookup(signs, part, pos, single)
        if sign is None:
            out.extend(run)
            continue
        consulted.append((sign.word, sign.pos))
        spelling = parse(sign.column(column))
        if names(spelling) == names(run):
            out.extend(run)
            continue
        out.extend(spelling)
        applied.append(part)
    return tuple(out), tuple(applied), tuple(consulted)
