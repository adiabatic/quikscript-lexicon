from pathlib import Path

import pytest

from qslex.passages import PASSAGES_HEADER, SPECIMENS, load_passages

GOOD_ROWS = [
    ["no-how", "0", "if", "·It·Fee", "senior", "", ""],
    ["no-how", "1", "he", "·He", "contraction", "", ""],
    ["bo-peep", "0", "little", "·Low·It·Tea·Low", "junior", "", ""],
    ["bo-peep", "1", "bo-peep", "·Bay·Owe-·Pea·Eat·Pea", "absent", "", "a name"],
]


def passages_file(tmp_path: Path, rows: list[list[str]]) -> Path:
    lines = ["\t".join(PASSAGES_HEADER)] + ["\t".join(row) for row in rows]
    path = tmp_path / "p.tsv"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def loaded(tmp_path: Path, rows: list[list[str]]) -> tuple[str, ...]:
    return tuple(word.verdict for word in load_passages(passages_file(tmp_path, rows)))


def test_the_shipped_fixture_loads_and_covers_every_specimen() -> None:
    words = load_passages()
    assert len(words) == sum(specimen.words for specimen in SPECIMENS.values())
    assert {word.passage for word in words} == set(SPECIMENS)


def test_every_specimen_word_is_accounted_for() -> None:
    verdicts = {word.verdict for word in load_passages()}
    assert verdicts <= {
        "senior",
        "junior",
        "ligature",
        "contraction",
        "differs",
        "absent",
    }


def test_a_junior_passage_cannot_use_a_senior_verdict(tmp_path: Path) -> None:
    rows = [*GOOD_ROWS[:2], ["bo-peep", "0", "little", "·Low", "senior", "", ""]]
    with pytest.raises(ValueError, match="cannot have verdict"):
        loaded(tmp_path, rows)


def test_a_senior_passage_cannot_use_the_junior_column(tmp_path: Path) -> None:
    rows = [["no-how", "0", "if", "·It·Fee", "junior", "", ""]]
    with pytest.raises(ValueError, match="cannot have verdict"):
        loaded(tmp_path, rows)


def test_an_unknown_passage_is_rejected(tmp_path: Path) -> None:
    rows = [["hey-nonny", "0", "if", "·It·Fee", "senior", "", ""]]
    with pytest.raises(ValueError, match="unknown passage"):
        loaded(tmp_path, rows)


def test_words_must_be_in_order(tmp_path: Path) -> None:
    rows = [
        ["no-how", "1", "he", "·He", "contraction", "", ""],
        ["no-how", "0", "if", "·It·Fee", "senior", "", ""],
    ]
    with pytest.raises(ValueError, match="out of order"):
        loaded(tmp_path, rows)


def test_only_a_differing_word_pins_what_we_spell(tmp_path: Path) -> None:
    rows = [["no-how", "0", "if", "·It·Fee", "senior", "·It·Fee", ""]]
    with pytest.raises(ValueError, match="only a differing word"):
        loaded(tmp_path, rows)


def test_a_differing_word_needs_a_note(tmp_path: Path) -> None:
    rows = [["no-how", "0", "if", "·It·Fee", "differs", "·It·Vie", ""]]
    with pytest.raises(ValueError, match="needs a note"):
        loaded(tmp_path, rows)


def test_a_reproduced_word_takes_no_note(tmp_path: Path) -> None:
    rows = [["no-how", "0", "if", "·It·Fee", "senior", "", "because"]]
    with pytest.raises(ValueError, match="needs a note"):
        loaded(tmp_path, rows)


def test_unknown_letter_names_are_rejected(tmp_path: Path) -> None:
    rows = [["no-how", "0", "if", "·It·Fnord", "senior", "", ""]]
    with pytest.raises(ValueError, match="unknown letter names"):
        loaded(tmp_path, rows)


def test_a_passage_that_loses_words_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="expected 56"):
        loaded(tmp_path, GOOD_ROWS)
