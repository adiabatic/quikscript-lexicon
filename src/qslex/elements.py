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
    """Split a phrase entry’s IPA into one chunk per word.

    ReadLex writes a phrase entry’s IPA with the same separators as the Latin, so the counts usually match. When they do not, every word gets the whole IPA string.
    """
    parts = tuple(BOUNDARY.split(ipa)[::2])
    return parts if len(parts) == count else (ipa,) * count


def runs(letters: Letters) -> tuple[Letters, ...]:
    """Split a spelling at its spaces and hyphens, each of which becomes a run of its own."""
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
    """Whether the Latin parts and the spelling’s runs line up one for one, with the same separator at each boundary.

    Equal counts are not enough. If a hyphen in the Latin lined up with a space in the spelling, the runs would not correspond to the Latin parts, and a rewrite matched on one part could change letters that belong to another.
    """
    if len(parts) != len(spelled):
        return False
    return all(
        (part if part in DIVIDERS else "") == divider(run)
        for part, run in zip(parts, spelled, strict=True)
    )


def elements(latin: str, letters: Letters) -> tuple[tuple[str, Letters], ...] | None:
    """An entry’s Latin parts paired with the runs of its spelling, or None.

    Returns None if the Latin parts and the spelling’s runs do not line up one for one. The rules and the lint checks then treat the whole entry as one element, and no word sign is substituted. For example, to-day has one spelled run and three Latin parts, and dhs has one Latin part and seven runs. The orthographic rules, the word signs and the lint checks all split entries here, so they agree on where the boundaries are.
    """
    parts = components(latin)
    spelled = runs(letters)
    if not aligned(parts, spelled):
        return None
    return tuple(zip(parts, spelled, strict=True))
