from __future__ import annotations

import re
from dataclasses import dataclass

from qslex.csur import CODEPOINT_OF

VOWELS = frozenset(
    {
        "It",
        "Eat",
        "Et",
        "Eight",
        "At",
        "I",
        "Ah",
        "Awe",
        "Ox",
        "Oy",
        "Utter",
        "Out",
        "Owe",
        "Foot",
        "Ooze",
    }
)

SEPARATORS = frozenset("- '’")
LETTER = re.compile(r"·(-ing|J’ai|[A-Za-z]+)|(.)")


@dataclass(frozen=True)
class Letter:
    name: str
    stressed: bool
    source: str

    @property
    def is_vowel(self) -> bool:
        return self.name in VOWELS

    @property
    def is_letter(self) -> bool:
        return self.name in CODEPOINT_OF


Letters = tuple[Letter, ...]


def parse(spelling: str) -> Letters:
    return tuple(
        Letter(name or other, False, "") for name, other in LETTER.findall(spelling)
    )


def unknown_names(spelling: str) -> list[str]:
    return [
        f.name
        for f in parse(spelling)
        if f.name not in CODEPOINT_OF and f.name not in SEPARATORS
    ]


def names(letters: Letters) -> tuple[str, ...]:
    return tuple(f.name for f in letters)


def render(letters: Letters) -> str:
    return "".join(("·" + f.name) if f.is_letter else f.name for f in letters)


def render_qs(letters: Letters) -> str:
    return "".join(
        chr(CODEPOINT_OF[f.name]) if f.is_letter else f.name for f in letters
    )
