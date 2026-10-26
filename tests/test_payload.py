import collections
import dataclasses
import json
from pathlib import Path

import pytest

from qslex.build import HUNSPELL_AFF, HUNSPELL_DIC
from qslex.checker_data import (
    COLUMNS,
    CONTRACTION,
    CheckerDataError,
    artifact,
    contracted,
    crosscheck,
    load_records,
    payload,
)
from qslex.desk import build as build_page
from qslex.hunspell import X_LETTERS, by_frequency
from qslex.payload import PAYLOAD, build, main
from qslex.readlex import repo_root
from qslex.words import Contraction

TEA = chr(0xE652)
DAY = chr(0xE653)
KEY = chr(0xE654)
NO = chr(0xE666)
LOW = chr(0xE667)
ROE = chr(0xE668)
EAT = chr(0xE671)
ET = chr(0xE672)
UTTER = chr(0xE67A)
FOOT = chr(0xE67D)

ROOT = repo_root()
RECORDS = load_records(ROOT)
WRITTEN, LEXICON = build()
DATA = json.loads(WRITTEN)
LINES = DATA["words"].split("\n")
LATIN_BY_SPELLING_LINES = DATA["latin_by_spelling"].split("\n")
SPELLINGS_BY_LATIN_LINES = DATA["spellings_by_latin"].split("\n")


def directive(name: str, keyword: str) -> str:
    lines = artifact(name, ROOT).splitlines()
    return next(line for line in lines if line.startswith(keyword + " ")).split(" ", 1)[
        1
    ]


def test_building_the_payload_twice_is_byte_identical() -> None:
    again, _ = build()
    assert again.encode("utf-8") == WRITTEN.encode("utf-8")


def test_the_file_is_the_desk_pages_object_plus_the_lookup_maps() -> None:
    page, _ = build_page()
    inlined = payload(LEXICON)
    assert inlined in page
    assert json.loads(inlined) == {
        key: value
        for key, value in DATA.items()
        if key not in ("latin_by_spelling", "spellings_by_latin")
    }
    assert WRITTEN.endswith("\n")
    assert "\n" not in WRITTEN.removesuffix("\n")


def test_the_payload_has_the_expected_top_level_keys() -> None:
    assert sorted(DATA) == [
        "confusions",
        "latin_by_spelling",
        "rep",
        "spellings_by_latin",
        "try_order",
        "words",
    ]


def test_the_word_set_is_the_dictionary_and_the_senior_contractions() -> None:
    words = tuple(line.partition("\t")[0] for line in LINES)
    assert words == LEXICON.union
    counted, *listed = artifact(HUNSPELL_DIC, ROOT).splitlines()
    assert counted == str(len(listed))
    assert frozenset(listed) < frozenset(words)
    assert len(listed) == 75605
    assert len(words) == 75674
    assert len(words) - len(listed) == 69


def test_a_frequency_is_written_only_where_there_is_one() -> None:
    for line, word in zip(LINES, LEXICON.union, strict=True):
        spelling, _, frequency = line.partition("\t")
        assert spelling == word
        counted = LEXICON.frequency[word]
        assert frequency == (str(counted) if counted else "")


def test_the_letter_order_is_the_affix_files_try_order() -> None:
    assert DATA["try_order"] == directive(HUNSPELL_AFF, "TRY")
    assert DATA["try_order"] == by_frequency(LEXICON.listed)


def test_the_replacement_table_is_the_affix_files_own() -> None:
    written = [
        line.split(" ")[1:]
        for line in artifact(HUNSPELL_AFF, ROOT).splitlines()
        if line.startswith("REP ") and line.count(" ") == 2
    ]
    assert DATA["rep"] == written
    assert len(DATA["rep"]) == 2 * len(X_LETTERS)


def test_the_confusion_group_is_the_vowels() -> None:
    """Compared with the codepoint block directly, rather than derived from the letter names as the builder does."""
    assert DATA["confusions"] == ["".join(map(chr, range(0xE670, 0xE67F)))]


def test_latin_by_spelling_has_exactly_the_union_as_its_keys() -> None:
    assert len(LATIN_BY_SPELLING_LINES) == 110258
    assert {line.split("\t")[0] for line in LATIN_BY_SPELLING_LINES} == frozenset(
        LEXICON.union
    )


def test_a_latin_by_spelling_line_has_a_latin_word_tag_and_column() -> None:
    for line in LATIN_BY_SPELLING_LINES:
        spelling, latin, pos, column = line.split("\t")
        assert spelling and latin and pos
        assert column in (*COLUMNS, CONTRACTION)


def test_latin_by_spelling_has_the_expected_line_count_for_each_column() -> None:
    counted = collections.Counter(
        line.split("\t")[3] for line in LATIN_BY_SPELLING_LINES
    )
    assert counted == {"senior": 107751, "x": 2326, "contraction": 154, "junior": 27}


def test_every_latin_and_tag_in_latin_by_spelling_is_in_spellings_by_latin() -> None:
    tagged = {tuple(line.split("\t")[:2]) for line in SPELLINGS_BY_LATIN_LINES}
    for line in LATIN_BY_SPELLING_LINES:
        _, latin, pos, _ = line.split("\t")
        assert (latin, pos) in tagged


def test_spellings_by_latin_has_the_expected_line_and_latin_word_counts() -> None:
    assert len(SPELLINGS_BY_LATIN_LINES) == 107755
    assert len({line.split("\t")[0] for line in SPELLINGS_BY_LATIN_LINES}) == 77561


def test_a_spellings_by_latin_line_is_lowercased_with_every_required_field() -> None:
    for line in SPELLINGS_BY_LATIN_LINES:
        latin, pos, frequency, qs, _, _ = line.split("\t")
        assert latin == latin.lower()
        assert pos
        assert frequency == str(int(frequency))
        assert qs


def test_read_has_one_spellings_by_latin_row_per_tag() -> None:
    rows = [
        line.split("\t")
        for line in SPELLINGS_BY_LATIN_LINES
        if line.startswith("read\t")
    ]
    assert [(pos, qs) for _, pos, _, qs, _, _ in rows] == [
        ("NN1", ROE + EAT + DAY),
        ("VVB", ROE + EAT + DAY),
        ("VVD", ROE + ET + DAY),
        ("VVI", ROE + EAT + DAY),
        ("VVN", ROE + ET + DAY),
    ]


def test_lead_has_two_nn1_rows_with_different_spellings() -> None:
    rows = [
        line.split("\t")
        for line in SPELLINGS_BY_LATIN_LINES
        if line.startswith("lead\tNN1\t")
    ]
    assert [(frequency, qs) for _, _, frequency, qs, _, _ in rows] == [
        ("5049", LOW + EAT + DAY),
        ("5049", LOW + ET + DAY),
    ]


def test_a_diverging_rows_junior_spelling_appears_in_both_maps() -> None:
    (line,) = [
        line for line in SPELLINGS_BY_LATIN_LINES if line.startswith("couldn't\t")
    ]
    assert line.split("\t") == [
        "couldn't",
        "VM0+XX0",
        "0",
        KEY + FOOT + DAY + NO + TEA,
        KEY + FOOT + DAY + UTTER + NO + TEA,
        "",
    ]
    junior = KEY + FOOT + DAY + UTTER + NO + TEA
    assert f"{junior}\tcouldn't\tVM0+XX0\tjunior" in LATIN_BY_SPELLING_LINES


def test_a_spaced_spelling_is_in_neither_map() -> None:
    assert not any(" " in line.split("\t")[0] for line in LATIN_BY_SPELLING_LINES)
    assert not any(
        " " in field
        for line in SPELLINGS_BY_LATIN_LINES
        for field in line.split("\t")[3:]
    )


def test_a_word_set_the_dictionary_does_not_list_is_refused() -> None:
    without_last_spelling = dataclasses.replace(LEXICON, listed=LEXICON.listed[:-1])
    with pytest.raises(CheckerDataError, match="make artifacts"):
        crosscheck(without_last_spelling, ROOT)


def test_a_contraction_matching_no_lexicon_row_is_refused() -> None:
    stray = Contraction("qwertyuiop", "", "word", "·Key", "senior-contractions", "")
    with pytest.raises(CheckerDataError, match="matches no row"):
        contracted((stray,), RECORDS)


def test_check_reports_a_payload_that_is_not_there(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["--out", str(tmp_path / PAYLOAD), "--check"]) == 1
    assert "is missing" in capsys.readouterr().out


def test_the_payload_it_writes_passes_its_own_check(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / PAYLOAD
    assert main(["--out", str(out)]) == 0
    assert out.read_text(encoding="utf-8") == WRITTEN
    assert main(["--out", str(out), "--check"]) == 0
    assert "OK: 1 artifact matches a fresh build" in capsys.readouterr().out


def test_check_fails_on_a_payload_that_has_been_edited(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / PAYLOAD
    out.write_text(WRITTEN.replace("try_order", "try_order2"), encoding="utf-8")
    assert main(["--out", str(out), "--check"]) == 1
    assert "differs from a fresh build" in capsys.readouterr().out
