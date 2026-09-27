import collections
import shutil
import subprocess
from pathlib import Path

import pytest

from qslex.build import HUNSPELL_AFF, HUNSPELL_DIC
from qslex.csur import CODEPOINT_OF
from qslex.hunspell import ALPHABET, HYPHEN, WORDCHARS, X_LETTERS

from conftest import built, entries

ENTRIES = entries()
BUILT = built()

HUNSPELL = shutil.which("hunspell")

COUNT, *WORDS = BUILT[HUNSPELL_DIC].splitlines()
LISTED = frozenset(WORDS)

AFF = BUILT[HUNSPELL_AFF].splitlines()
KEYWORDS = [line.split(" ")[0] for line in AFF]
REPLACEMENTS = [
    line.split(" ")[1:]
    for line in AFF
    if line.startswith("REP ") and line.count(" ") == 2
]


def directive(keyword: str) -> str:
    return next(line for line in AFF if line.startswith(keyword + " ")).split(" ", 1)[1]


def columns() -> set[str]:
    return {
        value
        for entry in ENTRIES
        for value in (entry.qs, entry.junior, entry.x_letter)
        if value
    }


def mutate(word: str) -> str:
    return next(
        letter + word[1:] for letter in ALPHABET if letter + word[1:] not in LISTED
    )


def spell_the_pair_out() -> tuple[str, str]:
    for word in WORDS:
        for x_letter, pair in X_LETTERS:
            if x_letter in word and word.replace(x_letter, pair) not in LISTED:
                return word.replace(x_letter, pair), word
    raise AssertionError("no X-letter spelling whose pair form is free")


def write_the_x_letter_in() -> tuple[str, str]:
    for word in WORDS:
        for x_letter, pair in X_LETTERS:
            if pair in word and word.replace(pair, x_letter) not in LISTED:
                return word.replace(pair, x_letter), word
    raise AssertionError("no pair spelling whose X-letter form is free")


def check(base: Path, text: str, *flags: str) -> list[str]:
    assert HUNSPELL is not None
    finished = subprocess.run(
        [HUNSPELL, "-d", str(base), "-i", "utf-8", *flags],
        input=text,
        capture_output=True,
        encoding="utf-8",
        check=True,
    )
    return finished.stdout.splitlines()


def suggested(line: str) -> list[str]:
    return line.split(": ", 1)[1].split(", ") if ": " in line else []


@pytest.fixture(scope="module")
def installed(tmp_path_factory: pytest.TempPathFactory) -> Path:
    base = tmp_path_factory.mktemp("hunspell") / "en-Qaas"
    base.with_suffix(".dic").write_text(BUILT[HUNSPELL_DIC], encoding="utf-8")
    base.with_suffix(".aff").write_text(BUILT[HUNSPELL_AFF], encoding="utf-8")
    return base


def test_the_dictionary_counts_its_own_entries() -> None:
    assert str(len(WORDS)) == COUNT


def test_the_dictionary_is_every_unspaced_spelling_of_all_three_columns() -> None:
    assert {value for value in columns() if " " not in value} == LISTED


def test_the_spaced_entries_are_the_only_ones_left_out() -> None:
    dropped = columns() - LISTED
    assert dropped
    assert all(" " in value for value in dropped)


def test_every_entry_is_quikscript_letters_and_hyphens() -> None:
    stray = {character for word in WORDS for character in word}
    assert stray - (frozenset(ALPHABET) | {HYPHEN}) == set()


def test_the_entries_are_distinct_and_sorted() -> None:
    assert len(WORDS) == len(LISTED)
    assert sorted(LISTED) == WORDS


def test_no_entry_has_an_affix_flag() -> None:
    assert [word for word in WORDS if "/" in word] == []


def test_the_affix_file_has_only_the_directives_it_needs() -> None:
    assert KEYWORDS == ["SET", "WORDCHARS", "TRY"] + ["REP"] * 5
    assert directive("SET") == "UTF-8"


def test_wordchars_lists_every_letter_and_the_hyphen() -> None:
    assert directive("WORDCHARS") == WORDCHARS
    assert set(WORDCHARS) == set(ALPHABET) | {HYPHEN}
    assert len(WORDCHARS) == len(CODEPOINT_OF) + 1


def test_try_lists_every_letter_and_nothing_else() -> None:
    assert set(directive("TRY")) == set(ALPHABET)
    assert len(directive("TRY")) == len(CODEPOINT_OF)


def test_try_lists_letters_from_most_to_least_frequent() -> None:
    counts = collections.Counter(
        character for word in WORDS for character in word if character != HYPHEN
    )
    written = [(-counts[letter], letter) for letter in directive("TRY")]
    assert written == sorted(written)


def test_the_replacement_table_maps_each_x_letter_both_ways() -> None:
    expected = [
        [written, meant]
        for x_letter, pair in X_LETTERS
        for written, meant in ((x_letter, pair), (pair, x_letter))
    ]
    assert directive("REP") == str(len(expected))
    assert expected == REPLACEMENTS


def test_each_x_letter_stands_for_the_pair_it_is_named_for() -> None:
    letter = {name: chr(codepoint) for name, codepoint in CODEPOINT_OF.items()}
    named = (
        (letter["Excite"], letter["Key"] + letter["See"]),
        (letter["Exam"], letter["Gay"] + letter["Zoo"]),
    )
    assert named == X_LETTERS


@pytest.mark.skipif(HUNSPELL is None, reason="hunspell is not installed")
def test_hunspell_accepts_every_entry_the_dictionary_ships(installed: Path) -> None:
    assert check(installed, "\n".join(WORDS) + "\n", "-l") == []


@pytest.mark.skipif(HUNSPELL is None, reason="hunspell is not installed")
def test_hunspell_accepts_a_hyphenated_entry_with_an_unlisted_part(
    installed: Path,
) -> None:
    compounds = [
        word
        for word in WORDS
        if HYPHEN in word and any(p not in LISTED for p in word.split(HYPHEN))
    ]
    assert compounds
    assert check(installed, "\n".join(compounds) + "\n", "-l") == []


@pytest.mark.skipif(HUNSPELL is None, reason="hunspell is not installed")
def test_hunspell_flags_a_mutated_entry_and_suggests_the_original(
    installed: Path,
) -> None:
    word = max(WORDS, key=len)
    reported = check(installed, mutate(word) + "\n", "-a")[1:]
    assert reported[0].startswith("& ")
    assert word in suggested(reported[0])


@pytest.mark.skipif(HUNSPELL is None, reason="hunspell is not installed")
def test_hunspell_suggests_the_x_letter_first_where_the_pair_is_spelled_out(
    installed: Path,
) -> None:
    spelled_out, substituted = spell_the_pair_out()
    reported = check(installed, spelled_out + "\n", "-a")[1:]
    assert suggested(reported[0])[:1] == [substituted]


@pytest.mark.skipif(HUNSPELL is None, reason="hunspell is not installed")
def test_hunspell_suggests_the_pair_first_where_no_x_letter_is_allowed(
    installed: Path,
) -> None:
    substituted, spelled_out = write_the_x_letter_in()
    reported = check(installed, substituted + "\n", "-a")[1:]
    assert suggested(reported[0])[:1] == [spelled_out]


@pytest.mark.skipif(HUNSPELL is None, reason="hunspell is not installed")
def test_hunspell_flags_a_bare_hyphen_between_two_entries(installed: Path) -> None:
    first, second = WORDS[0], WORDS[-1]
    line = f"{first} {HYPHEN} {second}\n"
    assert check(installed, line, "-l") == [HYPHEN]
