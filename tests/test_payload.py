import dataclasses
import json
from pathlib import Path

import pytest

from qslex.build import HUNSPELL_AFF, HUNSPELL_DIC
from qslex.desk import build as build_page
from qslex.hunspell import X_LETTERS, by_frequency
from qslex.payload import PAYLOAD, build, main
from qslex.projection import (
    ProjectionError,
    artifact,
    contracted,
    crosscheck,
    load_records,
)
from qslex.readlex import repo_root
from qslex.words import Contraction

ROOT = repo_root()
RECORDS = load_records(ROOT)
WRITTEN, LEXICON = build()
DATA = json.loads(WRITTEN)
LINES = DATA["words"].split("\n")


def directive(name: str, keyword: str) -> str:
    lines = artifact(name, ROOT).splitlines()
    return next(line for line in lines if line.startswith(keyword + " ")).split(" ", 1)[
        1
    ]


def test_building_the_payload_twice_is_byte_identical() -> None:
    again, _ = build()
    assert again.encode("utf-8") == WRITTEN.encode("utf-8")


def test_the_file_is_the_object_the_desk_page_inlines_and_one_newline() -> None:
    page, _ = build_page()
    assert WRITTEN.removesuffix("\n") in page
    assert WRITTEN.endswith("\n")
    assert "\n" not in WRITTEN.removesuffix("\n")


def test_the_payload_carries_its_data_as_one_json_object() -> None:
    assert sorted(DATA) == ["confusions", "rep", "try_order", "words"]


def test_the_word_set_is_the_dictionary_and_the_senior_contractions() -> None:
    words = tuple(line.partition("\t")[0] for line in LINES)
    assert words == LEXICON.union
    counted, *listed = artifact(HUNSPELL_DIC, ROOT).splitlines()
    assert counted == str(len(listed))
    assert frozenset(listed) < frozenset(words)
    assert len(listed) == 75583
    assert len(words) == 75651
    assert len(words) - len(listed) == 68


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
