import collections
import dataclasses
import json
from pathlib import Path

import pytest

from qslex.build import HUNSPELL_AFF, HUNSPELL_DIC
from qslex.desk import build as build_page
from qslex.hunspell import X_LETTERS, by_frequency
from qslex.payload import PAYLOAD, build, main
from qslex.projection import (
    COLUMNS,
    CONTRACTION,
    ProjectionError,
    artifact,
    contracted,
    crosscheck,
    load_records,
    payload,
)
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
READS = DATA["readings"].split("\n")
WRITES = DATA["writings"].split("\n")


def directive(name: str, keyword: str) -> str:
    lines = artifact(name, ROOT).splitlines()
    return next(line for line in lines if line.startswith(keyword + " ")).split(" ", 1)[
        1
    ]


def test_building_the_payload_twice_is_byte_identical() -> None:
    again, _ = build()
    assert again.encode("utf-8") == WRITTEN.encode("utf-8")


def test_the_file_is_the_desk_pages_object_grown_by_the_lookup_maps() -> None:
    page, _ = build_page()
    inlined = payload(LEXICON)
    assert inlined in page
    assert json.loads(inlined) == {
        key: held for key, held in DATA.items() if key not in ("readings", "writings")
    }
    assert WRITTEN.endswith("\n")
    assert "\n" not in WRITTEN.removesuffix("\n")


def test_the_payload_carries_its_data_as_one_json_object() -> None:
    assert sorted(DATA) == [
        "confusions",
        "readings",
        "rep",
        "try_order",
        "words",
        "writings",
    ]


def test_the_word_set_is_the_dictionary_and_the_senior_contractions() -> None:
    words = tuple(line.partition("\t")[0] for line in LINES)
    assert words == LEXICON.union
    counted, *listed = artifact(HUNSPELL_DIC, ROOT).splitlines()
    assert counted == str(len(listed))
    assert frozenset(listed) < frozenset(words)
    assert len(listed) == 75588
    assert len(words) == 75657
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
    """Pinned to the codepoint block, not re-derived from the names the builder uses."""
    assert DATA["confusions"] == ["".join(map(chr, range(0xE670, 0xE67F)))]


def test_the_readings_key_exactly_the_union() -> None:
    assert len(READS) == 110235
    assert {line.split("\t")[0] for line in READS} == frozenset(LEXICON.union)


def test_a_reading_names_its_row_and_the_column_the_spelling_sits_in() -> None:
    for line in READS:
        spelling, latin, pos, column = line.split("\t")
        assert spelling and latin and pos
        assert column in (*COLUMNS, CONTRACTION)


def test_the_reading_columns_count_the_masters_divergences() -> None:
    counted = collections.Counter(line.split("\t")[3] for line in READS)
    assert counted == {"senior": 107728, "x": 2326, "contraction": 154, "junior": 27}


def test_every_reading_joins_the_writings_on_latin_and_tag() -> None:
    tagged = {tuple(line.split("\t")[:2]) for line in WRITES}
    for line in READS:
        _, latin, pos, _ = line.split("\t")
        assert (latin, pos) in tagged


def test_the_writings_carry_every_row_that_spells_a_token() -> None:
    assert len(WRITES) == 107732
    assert len({line.split("\t")[0] for line in WRITES}) == 77543


def test_a_writing_is_lowercased_and_fully_fielded() -> None:
    for line in WRITES:
        latin, pos, frequency, qs, _, _ = line.split("\t")
        assert latin == latin.lower()
        assert pos
        assert frequency == str(int(frequency))
        assert qs


def test_read_keeps_its_heteronyms_apart_by_tag() -> None:
    rows = [line.split("\t") for line in WRITES if line.startswith("read\t")]
    assert [(pos, qs) for _, pos, _, qs, _, _ in rows] == [
        ("NN1", ROE + EAT + DAY),
        ("VVB", ROE + EAT + DAY),
        ("VVD", ROE + ET + DAY),
        ("VVI", ROE + EAT + DAY),
        ("VVN", ROE + ET + DAY),
    ]


def test_lead_keeps_its_two_nouns_side_by_side() -> None:
    rows = [line.split("\t") for line in WRITES if line.startswith("lead\tNN1\t")]
    assert [(frequency, qs) for _, _, frequency, qs, _, _ in rows] == [
        ("5049", LOW + EAT + DAY),
        ("5049", LOW + ET + DAY),
    ]


def test_a_diverging_row_carries_its_junior_column() -> None:
    (line,) = [line for line in WRITES if line.startswith("couldn't\t")]
    assert line.split("\t") == [
        "couldn't",
        "VM0+XX0",
        "0",
        KEY + FOOT + DAY + NO + TEA,
        KEY + FOOT + DAY + UTTER + NO + TEA,
        "",
    ]
    junior = KEY + FOOT + DAY + UTTER + NO + TEA
    assert f"{junior}\tcouldn't\tVM0+XX0\tjunior" in READS


def test_a_spaced_spelling_reaches_neither_map() -> None:
    assert not any(" " in line.split("\t")[0] for line in READS)
    assert not any(" " in field for line in WRITES for field in line.split("\t")[3:])


def test_a_word_set_the_dictionary_does_not_list_is_refused() -> None:
    doctored = dataclasses.replace(LEXICON, listed=LEXICON.listed[:-1])
    with pytest.raises(ProjectionError, match="make artifacts"):
        crosscheck(doctored, ROOT)


def test_a_contraction_matching_no_lexicon_row_is_refused() -> None:
    stray = Contraction("qwertyuiop", "", "word", "·Key", "senior-contractions", "")
    with pytest.raises(ProjectionError, match="matches no row"):
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
