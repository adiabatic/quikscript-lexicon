from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from qslex.elements import elements
from qslex.letters import Letter, Letters, names, parse, unknown_names
from qslex.tables import rows_of

SIGNS_FILE = "word-signs.tsv"
SIGNS_HEADER = ["word", "pos", "tier", "senior", "junior", "full", "authority", "note"]
TIERS = {"core", "standard", "abbreviation"}
SIGN_AUTHORITIES = {"junior-contractions", "common-words"}

CONTRACTIONS_FILE = "contractions.tsv"
CONTRACTIONS_HEADER = ["word", "pos", "kind", "contraction", "authority", "note"]
KINDS = {"word", "clitic"}
CONTRACTION_AUTHORITIES = {"senior-contractions", "terminal-ing"}

# The core eight the Manual sanctions for Junior writing too, in its own order.
CORE_EIGHT = ("the", "of", "and", "to", "it", "is", "for", "be")


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
    for lineno, source, row in rows_of(path, SIGNS_FILE, SIGNS_HEADER):
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
    for lineno, source, row in rows_of(path, CONTRACTIONS_FILE, CONTRACTIONS_HEADER):
        entry = Contraction(*row)
        if entry.kind not in KINDS:
            raise ValueError(
                f"{source}:{lineno}: kind must be one of {sorted(KINDS)}, "
                f"got {entry.kind!r}"
            )
        if entry.authority not in CONTRACTION_AUTHORITIES:
            raise ValueError(
                f"{source}:{lineno}: {entry.authority!r} is not a Manual anchor "
                f"for this table (have {sorted(CONTRACTION_AUTHORITIES)})"
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


def _lookup(signs: Signs, part: str, pos: str, single: bool) -> Sign | None:
    """A phrase entry's tag belongs to the phrase, so only general rows apply inside."""
    return sign_for(signs, part, pos) if single else signs.get((part, ""))


def apply_signs(
    latin: str, pos: str, letters: Letters, signs: Signs
) -> tuple[Letters, Letters, tuple[str, ...], tuple[tuple[str, str], ...]]:
    """Substitute the Manual's word signs and standard outlines into a spelling.

    A single-word entry consults its own part-of-speech tag; a phrase entry is matched word by word, at the boundaries `qslex.elements` finds. Nothing is substituted unless the Latin words and the spelling's runs are the same shape, which is what keeps to-day (one run, three Latin parts) and dhs (one Latin part, seven runs) intact. Both columns come out of one alignment, because a row with no junior form of its own writes its senior spelling into both. Returns the two spellings, the words the senior one changed, and the rows it consulted.
    """
    pairs = elements(latin, letters)
    if pairs is None:
        return letters, letters, (), ()
    single = len(pairs) == 1
    senior: list[Letter] = []
    junior: list[Letter] = []
    applied: list[str] = []
    consulted: list[tuple[str, str]] = []
    for part, run in pairs:
        sign = _lookup(signs, part, pos, single)
        if sign is None:
            senior.extend(run)
            junior.extend(run)
            continue
        consulted.append((sign.word, sign.pos))
        spelling = parse(sign.senior)
        if names(spelling) == names(run):
            senior.extend(run)
        else:
            senior.extend(spelling)
            applied.append(part)
        if sign.junior:
            spelling = parse(sign.junior)
        junior.extend(run if names(spelling) == names(run) else spelling)
    return tuple(senior), tuple(junior), tuple(applied), tuple(consulted)
