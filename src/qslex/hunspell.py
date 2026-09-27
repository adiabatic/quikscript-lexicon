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
    """Every distinct spelling a spell checker could be given, in codepoint order.

    All three columns are included, so the dictionary accepts both grades and the X-letter form. Spaced entries are dropped. A tokenizer splits at a space before it consults a dictionary, so hunspell never receives a spaced string, and a listed one could never match.
    """
    found = {value for row in columns for value in row if value and " " not in value}
    return tuple(sorted(found))


def dictionary(words: Sequence[str]) -> str:
    """The word list, with the word count on the first line as hunspell’s format requires.

    No word has an affix flag. ReadLex lists every inflected form as its own row, so affix rules would encode nothing the list does not already contain, and a flag with no rule behind it could only introduce errors.
    """
    return f"{len(words)}\n" + "".join(f"{word}\n" for word in words)


def by_frequency(words: Iterable[str]) -> str:
    """The alphabet ordered by how often each letter occurs in the word list, most frequent first.

    hunspell tries TRY letters in order when it substitutes one letter for another, so the order is computed from letter frequency. Ties are broken by codepoint, which keeps the string deterministic.
    """
    counts = collections.Counter(character for word in words for character in word)
    return "".join(sorted(ALPHABET, key=lambda letter: (-counts[letter], letter)))


def affix(words: Iterable[str]) -> str:
    """The affix file: an encoding, the tokenizer’s word characters, and one replacement table.

    Without `WORDCHARS`, hunspell’s own tokenizer treats Quikscript codepoints as punctuation and checks nothing. The hyphen is included because hundreds of hyphenated entries have a piece that is not itself an entry. Without the hyphen, hunspell splits those entries and flags the pieces.

    `REP` maps each X-letter to its two-letter pair and the pair back to the X-letter. Replacing an X-letter with its pair takes two single-letter edits, so without REP the other form is at best far down the suggestion list.
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
