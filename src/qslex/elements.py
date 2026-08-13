from __future__ import annotations

import re

from qslex.letters import Letter, Letters

BOUNDARY = re.compile(r"([ -])")
DIVIDERS = frozenset(" -")


def components(latin: str) -> tuple[str, ...]:
    """A phrase entry’s words and the separators between them, in order.

    An entry that begins or ends with a separator keeps the empty word on that side, so the result lines up one for one with the runs of a spelling for the same entry.
    """
    return tuple(BOUNDARY.split(latin))


def chunks(ipa: str, count: int) -> tuple[str, ...]:
    """A phrase entry’s IPA cut into one chunk per word, or the whole string per word.

    ReadLex writes a phrase entry’s IPA with the same separators the Latin uses, so the two usually line up one for one; where they do not, the whole string stands for every word. That is the conservatism `elements` applies to the spelling, applied here to the sounds.
    """
    parts = tuple(BOUNDARY.split(ipa)[::2])
    return parts if len(parts) == count else (ipa,) * count


def runs(letters: Letters) -> tuple[Letters, ...]:
    """Split a spelling at the separators the tokenizer passed through."""
    out: list[Letters] = []
    current: list[Letter] = []
    for letter in letters:
        if letter.name in DIVIDERS:
            out.append(tuple(current))
            out.append((letter,))
            current = []
        else:
            current.append(letter)
    out.append(tuple(current))
    return tuple(out)


def divider(run: Letters) -> str:
    return run[0].name if len(run) == 1 and run[0].name in DIVIDERS else ""


def aligned(parts: tuple[str, ...], spelled: tuple[Letters, ...]) -> bool:
    """Whether the Latin words and the spelling’s runs are the same shape.

    Equal counts are not enough: a Latin hyphen facing a spelled space would let a rewrite cross a boundary that is not the one it matched.
    """
    if len(parts) != len(spelled):
        return False
    return all(
        (part if part in DIVIDERS else "") == divider(run)
        for part, run in zip(parts, spelled, strict=True)
    )


def elements(latin: str, letters: Letters) -> tuple[tuple[str, Letters], ...] | None:
    """An entry’s Latin parts paired with the runs of its spelling, or None.

    None where the two are not the same shape, which is what keeps to-day (one spelled run against three Latin parts) and dhs (one Latin part against seven runs) from being mangled. Both the orthographic rules and the word signs cut an entry up here, so that neither can disagree with the other about where its boundaries are.
    """
    parts = components(latin)
    spelled = runs(letters)
    if not aligned(parts, spelled):
        return None
    return tuple(zip(parts, spelled, strict=True))
