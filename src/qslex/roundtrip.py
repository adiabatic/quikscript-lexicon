from __future__ import annotations

from qslex.letters import parse
from qslex.mapping import Mapping
from qslex.tokenizer import Token

# The merges the segment mapping makes on the way in, undone on the way out. Each is documented where it is made: the capitals are ReadLex’s own conventions, ʌ/ə/ɜː share ·Utter under Vowels + R, and i/u are the weak-vowel spellings the terminal rules use.
MERGES = {
    "ʌ": "ə",
    "ɜː": "ə",
    "Ə": "ə",
    "i": "ɪ",
    "I": "ɪ",
    "u": "uː",
    "R": "r",
    "Ɑː": "ɑː",
    "Æ": "æ",
    "Ð": "ð",
    "T": "t",
    "N": "n",
    "V": "v",
    "F": "f",
}

# The mapping’s sequence rows cover two phonemes with one row, so the reverse has to know they are two.
SEQUENCES = {
    "ɪə": ("ɪ", "ə"),
    "eə": ("e", "ə"),
    "ʊə": ("ʊ", "ə"),
    "aɪə": ("aɪ", "ə"),
    "aʊə": ("aʊ", "ə"),
}

# The two X-letters no segment mapping reaches, and so the only letters whose phonemes have to be stated here rather than derived. §II gives both.
X_LETTERS = {"Excite": ("k", "s"), "Exam": ("ɡ", "z")}

NOTHING = ""

# Every difference the round trip is allowed to find between what ReadLex said and what the spelling says, with the reason it is allowed. An edit outside this table is a spelling that has stopped meaning what its source meant. A word sign stands for the written word rather than for its sounds, so the rows one rewrites are not read back at all; every edit here belongs to the mapping or to a terminal convention.
EDITS: dict[tuple[str, str], str] = {
    (
        "ə",
        NOTHING,
    ): "an unstressed vowel one of the terminal or prefix conventions omits",
    (
        "ɪ",
        NOTHING,
    ): "an unstressed vowel one of the terminal or prefix conventions omits",
    (
        NOTHING,
        "ə",
    ): "the epenthetic ·Utter the rules insert between letters that cannot join",
    (
        "ɪ",
        "iː",
    ): "stressed ɪə is written ·Eat·Utter, so its first letter reads back as iː",
    ("ʊ", "uː"): "ʊə is written ·Ooze·Utter, so its first letter reads back as uː",
    ("e", "eɪ"): "eə before R is written ·Eight, which reads back as eɪ",
    (
        "ə",
        "e",
    ): "the -est, -ess, -ent and -ance terminals are written invariably with ·Et",
    ("ɪ", "e"): "the ·Excite X-letter takes the ·Et vowel, as -est and -ess do",
    ("ɪ", "ə"): "the -age and -en terminals are written invariably with ·Utter",
    ("ə", "ɪ"): "terminal -y is written ·It whatever ReadLex reduces it to",
    (
        "iː",
        "ɪ",
    ): "terminal -y is ·It unless that terminal is stressed, so a full iː reads as ɪ",
    ("r", NOTHING): "the -ward terminal drops the R with the vowel before it",
}


def phonemes_of(mapping: Mapping) -> dict[str, tuple[str, ...]]:
    """What each letter reads back as, derived from the mapping it is written by.

    Deriving this rather than writing it out is the point: it fails if two IPA tokens that are not a documented merge ever land on the same letter, which is the property that makes the mapping invertible at all.
    """
    table: dict[str, tuple[str, ...]] = {}
    for entry in mapping.entries:
        if len(entry.letters) != 1 or entry.ipa in SEQUENCES:
            continue
        name = entry.letters[0]
        phoneme = (MERGES.get(entry.ipa, entry.ipa),)
        if table.setdefault(name, phoneme) != phoneme:
            raise ValueError(
                f"·{name} is written for both {table[name][0]!r} and {phoneme[0]!r}, "
                f"which no documented merge joins"
            )
    for name, phonemes in X_LETTERS.items():
        table[name] = phonemes
    return table


def source_phonemes(tokens: tuple[Token, ...]) -> tuple[str, ...]:
    """What ReadLex said, as a phoneme string with the mapping’s merges applied."""
    out: list[str] = []
    for token in tokens:
        if token.entry.kind in {"marker", "structural", "hiatus"}:
            continue
        merged = MERGES.get(token.ipa, token.ipa)
        out.extend(SEQUENCES.get(merged, (merged,)))
    return tuple(out)


def spelled_phonemes(
    spelling: str, table: dict[str, tuple[str, ...]]
) -> tuple[str, ...]:
    """What the spelling says, read back one letter at a time."""
    out: list[str] = []
    for letter in parse(spelling):
        if letter.is_letter:
            out.extend(table[letter.name])
    return tuple(out)


def align(
    source: tuple[str, ...], spelled: tuple[str, ...]
) -> tuple[tuple[str, str], ...] | None:
    """The cheapest run of allowed edits carrying `source` to `spelled`, or None.

    None is the failure the check exists for: the spelling can no longer be read back to what ReadLex said by any sequence of differences this project has accounted for.
    """
    infinity = float("inf")
    width = len(spelled) + 1
    cost = [[infinity] * width for _ in range(len(source) + 1)]
    cost[0][0] = 0.0
    for i in range(len(source) + 1):
        for j in range(width):
            here = cost[i][j]
            if here == infinity:
                continue
            if i < len(source) and j < len(spelled):
                if source[i] == spelled[j]:
                    cost[i + 1][j + 1] = min(cost[i + 1][j + 1], here)
                elif (source[i], spelled[j]) in EDITS:
                    cost[i + 1][j + 1] = min(cost[i + 1][j + 1], here + 1)
            if i < len(source) and (source[i], NOTHING) in EDITS:
                cost[i + 1][j] = min(cost[i + 1][j], here + 1)
            if j < len(spelled) and (NOTHING, spelled[j]) in EDITS:
                cost[i][j + 1] = min(cost[i][j + 1], here + 1)
    if cost[len(source)][len(spelled)] == infinity:
        return None

    edits: list[tuple[str, str]] = []
    i, j = len(source), len(spelled)
    while i or j:
        here = cost[i][j]
        if i and j and source[i - 1] == spelled[j - 1] and cost[i - 1][j - 1] == here:
            i, j = i - 1, j - 1
            continue
        if (
            i
            and j
            and cost[i - 1][j - 1] == here - 1
            and (source[i - 1], spelled[j - 1]) in EDITS
        ):
            edits.append((source[i - 1], spelled[j - 1]))
            i, j = i - 1, j - 1
            continue
        if i and cost[i - 1][j] == here - 1 and (source[i - 1], NOTHING) in EDITS:
            edits.append((source[i - 1], NOTHING))
            i -= 1
            continue
        edits.append((NOTHING, spelled[j - 1]))
        j -= 1
    return tuple(reversed(edits))
