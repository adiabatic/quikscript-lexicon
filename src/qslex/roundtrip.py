from __future__ import annotations

from qslex.letters import parse
from qslex.mapping import Mapping
from qslex.tokenizer import Token

# IPA symbols the segment mapping writes with the same letter as another symbol, each mapped to that symbol. The round trip applies this table to the ReadLex IPA and to each letter’s reading, so a merged symbol compares equal to the symbol it maps to. ipa-to-qs.tsv and docs/ipa-to-qs.md give the source of each merge. The capitals are ReadLex’s own conventions. ʌ, ə and ɜː share ·Utter under Vowels + R. i and u are the weak vowels the terminal rules use.
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

# Each of the mapping’s sequence rows writes two phonemes with two letters. The round trip splits the ReadLex token into those two phonemes before comparing.
SEQUENCES = {
    "ɪə": ("ɪ", "ə"),
    "eə": ("e", "ə"),
    "ʊə": ("ʊ", "ə"),
    "aɪə": ("aɪ", "ə"),
    "aʊə": ("aʊ", "ə"),
}

# No mapping row writes an X-letter, so these are the only letters whose phonemes are listed here instead of derived from the mapping. §II gives both.
X_LETTERS = {"Excite": ("k", "s"), "Exam": ("ɡ", "z")}

NOTHING = ""

# Every difference the round trip allows between the ReadLex IPA and the spelling’s reading, with the reason for each. A difference outside this table means the spelling no longer represents the sounds it was made from. Rows a word sign rewrites are not read back, because a word sign stands for the written word rather than its sounds. Every entry here therefore comes from the mapping, a terminal or prefix convention, or the X-letter spelling.
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
    """The phonemes each letter reads back as, derived from the mapping.

    Deriving the table checks that the mapping can be inverted. It raises ValueError if two IPA tokens that no entry in `MERGES` joins are written with the same letter.
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
    """The ReadLex IPA as a phoneme string, with `MERGES` applied and sequences split."""
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
    """The phonemes a spelling reads back as, one letter at a time."""
    out: list[str] = []
    for letter in parse(spelling):
        if letter.is_letter:
            out.extend(table[letter.name])
    return tuple(out)


def align(
    source: tuple[str, ...], spelled: tuple[str, ...]
) -> tuple[tuple[str, str], ...] | None:
    """The fewest differences from `EDITS` that turn `source` into `spelled`, or None.

    None means no sequence of the differences in `EDITS` turns the ReadLex IPA into the spelling’s reading. That is the failure the round trip checks for.
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
