from __future__ import annotations

import collections
from collections.abc import Iterable, Sequence

from qslex.csur import CODEPOINT_OF

HYPHEN = "-"

ALPHABET = tuple(chr(codepoint) for codepoint in CODEPOINT_OF.values())
WORDCHARS = "".join(ALPHABET) + HYPHEN

X_LETTERS = (
    (
        chr(CODEPOINT_OF["Excite"]),
        chr(CODEPOINT_OF["Key"]) + chr(CODEPOINT_OF["See"]),
    ),
    (
        chr(CODEPOINT_OF["Exam"]),
        chr(CODEPOINT_OF["Gay"]) + chr(CODEPOINT_OF["Zoo"]),
    ),
)


def spellings(columns: Iterable[tuple[str, str, str]]) -> tuple[str, ...]:
    """Every distinct spelling a spell checker could be handed, in codepoint order.

    All three columns go in, so the dictionary accepts every grade and the X-letter form. A spaced entry is dropped: a tokenizer splits at a space before it consults a dictionary, so no such string ever reaches hunspell, and listing one would only be a line that can never match.
    """
    found = {value for row in columns for value in row if value and " " not in value}
    return tuple(sorted(found))


def dictionary(words: Sequence[str]) -> str:
    """The word list, counted on its first line as hunspell's format wants.

    No word carries an affix flag. ReadLex lists every inflected form as a row of its own, so the affix machinery would encode nothing the list does not already state, and a flag standing for no rule is a flag that can only go wrong.
    """
    return f"{len(words)}\n" + "".join(f"{word}\n" for word in words)


def by_frequency(words: Iterable[str]) -> str:
    """The alphabet ordered by how often each letter is written, commonest first.

    hunspell walks TRY in order when it tries one letter in place of another, so the order is worth getting right; it is counted off the word list rather than chosen. Ties fall back to the codepoint, which keeps the string deterministic.
    """
    counts = collections.Counter(character for word in words for character in word)
    return "".join(sorted(ALPHABET, key=lambda letter: (-counts[letter], letter)))


def affix(words: Iterable[str]) -> str:
    """The affix file: an encoding, a tokenizer alphabet, and one suggestion table.

    `WORDCHARS` is what makes the PUA legible to hunspell's own tokenizer, which otherwise takes Quikscript for punctuation and checks nothing at all. The hyphen is in it because hundreds of hyphenated entries have a piece that is not itself an entry, and without it hunspell splits those entries up and flags the pieces.

    `REP` bridges each X-letter to the letter pair it stands for, both ways: the letters around an X-letter change with it, so neither form of a word is a single-letter edit from the other, and without the bridge the other form is at best buried in the suggestion list.
    """
    lines = [
        "SET UTF-8",
        f"WORDCHARS {WORDCHARS}",
        f"TRY {by_frequency(words)}",
        f"REP {2 * len(X_LETTERS)}",
    ]
    for x_letter, pair in X_LETTERS:
        lines.append(f"REP {x_letter} {pair}")
        lines.append(f"REP {pair} {x_letter}")
    return "\n".join(lines) + "\n"
