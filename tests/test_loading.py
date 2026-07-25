from pathlib import Path

import pytest

from qslex import load_mapping, load_overrides, load_quirks
from qslex.divergences import DIVERGENCES_HEADER, load_divergences
from qslex.mapping import HEADER
from qslex.overrides import OVERRIDES_HEADER
from qslex.quirks import QUIRKS_HEADER

PEA = chr(0xE650)
EAT_UTTER = chr(0xE671) + chr(0xE67A)
IT_UTTER = chr(0xE670) + chr(0xE67A)

GOOD_ROWS = [
    ["p", "", PEA, "U+E650", "·Pea", "consonant", "pea", ""],
    ["ˈ", "", "", "", "", "marker", "", ""],
    ["ɪə", "stressed", EAT_UTTER, "U+E671 U+E67A", "·Eat·Utter", "sequence", "c", "x"],
    ["ɪə", "unstressed", IT_UTTER, "U+E670 U+E67A", "·It·Utter", "sequence", "h", "x"],
]


def write_tsv(path: Path, header: list[str], rows: list[list[str]]) -> Path:
    lines = ["\t".join(header)] + ["\t".join(r) for r in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def mapping_file(tmp_path: Path, rows: list[list[str]]) -> Path:
    return write_tsv(tmp_path / "m.tsv", HEADER, rows)


def test_good_mapping_loads(tmp_path: Path) -> None:
    mapping = load_mapping(mapping_file(tmp_path, GOOD_ROWS))
    assert mapping.lookup["ɪə"]["stressed"].letters == ("Eat", "Utter")
    assert mapping.lookup["ˈ"][""].codepoints == ()


def test_empty_ipa_is_rejected(tmp_path: Path) -> None:
    rows = [*GOOD_ROWS, ["", "", "", "", "", "marker", "", ""]]
    with pytest.raises(ValueError, match="empty ipa token"):
        load_mapping(mapping_file(tmp_path, rows))


def test_bad_header(tmp_path: Path) -> None:
    path = write_tsv(tmp_path / "m.tsv", HEADER[:-1], [])
    with pytest.raises(ValueError, match="unexpected header"):
        load_mapping(path)


def test_wrong_field_count(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="expected 8 fields"):
        load_mapping(mapping_file(tmp_path, [["p", "", ""]]))


def test_unknown_kind(tmp_path: Path) -> None:
    rows = [["p", "", PEA, "U+E650", "·Pea", "gadget", "pea", ""]]
    with pytest.raises(ValueError, match="unknown kind"):
        load_mapping(mapping_file(tmp_path, rows))


def test_unknown_letter_name(tmp_path: Path) -> None:
    rows = [["p", "", PEA, "U+E650", "·Pee", "consonant", "pea", ""]]
    with pytest.raises(ValueError, match="unknown letter names"):
        load_mapping(mapping_file(tmp_path, rows))


def test_codepoints_disagree_with_names(tmp_path: Path) -> None:
    rows = [["p", "", PEA, "U+E651", "·Pea", "consonant", "pea", ""]]
    with pytest.raises(ValueError, match="codepoints do not match"):
        load_mapping(mapping_file(tmp_path, rows))


def test_qs_disagrees_with_codepoints(tmp_path: Path) -> None:
    rows = [["p", "", "", "U+E650", "·Pea", "consonant", "pea", ""]]
    with pytest.raises(ValueError, match="qs string does not match"):
        load_mapping(mapping_file(tmp_path, rows))


def test_letters_must_be_dot_prefixed(tmp_path: Path) -> None:
    rows = [["p", "", PEA, "U+E650", "Pea", "consonant", "pea", ""]]
    with pytest.raises(ValueError, match="·-prefixed"):
        load_mapping(mapping_file(tmp_path, rows))


def test_codepoint_must_be_u_prefixed(tmp_path: Path) -> None:
    rows = [["p", "", PEA, "E650", "·Pea", "consonant", "pea", ""]]
    with pytest.raises(ValueError, match=r"U\+-prefixed"):
        load_mapping(mapping_file(tmp_path, rows))


def test_marker_row_may_not_carry_letters(tmp_path: Path) -> None:
    rows = [["ˈ", "", PEA, "U+E650", "·Pea", "marker", "", ""]]
    with pytest.raises(ValueError, match="must map to no letters"):
        load_mapping(mapping_file(tmp_path, rows))


def test_duplicate_row(tmp_path: Path) -> None:
    rows = [GOOD_ROWS[0], GOOD_ROWS[0]]
    with pytest.raises(ValueError, match="duplicate mapping row"):
        load_mapping(mapping_file(tmp_path, rows))


def test_incoherent_condition_set(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="incoherent condition set"):
        load_mapping(mapping_file(tmp_path, [GOOD_ROWS[2]]))


def test_quirks_reject_unknown_scope(tmp_path: Path) -> None:
    path = write_tsv(tmp_path / "q.tsv", QUIRKS_HEADER, [["nope", "a", "b", "w", "n"]])
    with pytest.raises(ValueError, match="unknown scope"):
        load_quirks(path)


def test_quirks_reject_empty_match(tmp_path: Path) -> None:
    path = write_tsv(tmp_path / "q.tsv", QUIRKS_HEADER, [["sub", "", "b", "w", "n"]])
    with pytest.raises(ValueError, match="empty match"):
        load_quirks(path)


def test_quirks_reject_bad_regex(tmp_path: Path) -> None:
    rows = [["regex", "a(", "b", "w", "n"]]
    path = write_tsv(tmp_path / "q.tsv", QUIRKS_HEADER, rows)
    with pytest.raises(ValueError, match="bad regex"):
        load_quirks(path)


def overrides_file(tmp_path: Path, rows: list[list[str]]) -> Path:
    return write_tsv(tmp_path / "o.tsv", OVERRIDES_HEADER, rows)


def test_overrides_reject_unknown_token(tmp_path: Path) -> None:
    mapping = load_mapping(mapping_file(tmp_path, GOOD_ROWS))
    rows = [["ˈzzz", "zz", "*", "stressed", "word", "a", ""]]
    with pytest.raises(ValueError, match="unknown token"):
        load_overrides(mapping, overrides_file(tmp_path, rows))


def test_overrides_reject_wrong_condition(tmp_path: Path) -> None:
    mapping = load_mapping(mapping_file(tmp_path, GOOD_ROWS))
    rows = [["ˈkɪə", "ɪə", "*", "pre-r", "word", "a", ""]]
    with pytest.raises(ValueError, match="no condition"):
        load_overrides(mapping, overrides_file(tmp_path, rows))


def test_overrides_reject_unconditional_token(tmp_path: Path) -> None:
    mapping = load_mapping(mapping_file(tmp_path, GOOD_ROWS))
    rows = [["p", "p", "*", "stressed", "word", "a", ""]]
    with pytest.raises(ValueError, match="unconditional"):
        load_overrides(mapping, overrides_file(tmp_path, rows))


def test_overrides_reject_ipa_without_token(tmp_path: Path) -> None:
    mapping = load_mapping(mapping_file(tmp_path, GOOD_ROWS))
    rows = [["ˈpp", "ɪə", "*", "stressed", "word", "a", ""]]
    with pytest.raises(ValueError, match="does not contain"):
        load_overrides(mapping, overrides_file(tmp_path, rows))


@pytest.mark.parametrize("occurrence", ["last", "0", "01", "-1", "²", "1.0", ""])
def test_overrides_reject_bad_occurrence(tmp_path: Path, occurrence: str) -> None:
    mapping = load_mapping(mapping_file(tmp_path, GOOD_ROWS))
    rows = [["ˈkɪə", "ɪə", occurrence, "stressed", "word", "a", ""]]
    with pytest.raises(ValueError, match="occurrence must be"):
        load_overrides(mapping, overrides_file(tmp_path, rows))


@pytest.mark.parametrize("occurrence", ["*", "1", "2", "10"])
def test_overrides_accept_good_occurrence(tmp_path: Path, occurrence: str) -> None:
    mapping = load_mapping(mapping_file(tmp_path, GOOD_ROWS))
    rows = [["ˈkɪə", "ɪə", occurrence, "stressed", "word", "a", ""]]
    assert load_overrides(mapping, overrides_file(tmp_path, rows))


def test_quirks_reject_missing_words(tmp_path: Path) -> None:
    path = write_tsv(tmp_path / "q.tsv", QUIRKS_HEADER, [["sub", "a", "b", "", "n"]])
    with pytest.raises(ValueError, match="no words declared"):
        load_quirks(path)


def test_overrides_reject_missing_words(tmp_path: Path) -> None:
    mapping = load_mapping(mapping_file(tmp_path, GOOD_ROWS))
    rows = [["ˈkɪə", "ɪə", "*", "stressed", "", "a", ""]]
    with pytest.raises(ValueError, match="no words declared"):
        load_overrides(mapping, overrides_file(tmp_path, rows))


def test_overrides_reject_duplicates(tmp_path: Path) -> None:
    mapping = load_mapping(mapping_file(tmp_path, GOOD_ROWS))
    row = ["ˈkɪə", "ɪə", "*", "stressed", "word", "a", ""]
    with pytest.raises(ValueError, match="duplicate override"):
        load_overrides(mapping, overrides_file(tmp_path, [row, row]))


def test_divergence_needs_authority(tmp_path: Path) -> None:
    rows = [["barrier", "ˈbærɪəR", "unstressed", "x", "-ier", ""]]
    path = write_tsv(tmp_path / "d.tsv", DIVERGENCES_HEADER, rows)
    with pytest.raises(ValueError, match="needs an authority"):
        load_divergences(path)


def test_divergence_needs_word_and_ipa(tmp_path: Path) -> None:
    rows = [["", "", "unstressed", "x", "-ier", "a"]]
    path = write_tsv(tmp_path / "d.tsv", DIVERGENCES_HEADER, rows)
    with pytest.raises(ValueError, match="word and ipa are both required"):
        load_divergences(path)


def test_divergence_rejects_unknown_condition(tmp_path: Path) -> None:
    rows = [["barrier", "ˈbærɪəR", "sideways", "x", "-ier", "a"]]
    path = write_tsv(tmp_path / "d.tsv", DIVERGENCES_HEADER, rows)
    with pytest.raises(ValueError, match="condition must be one of"):
        load_divergences(path)


def test_divergence_needs_shavian_and_family(tmp_path: Path) -> None:
    rows = [["barrier", "ˈbærɪəR", "unstressed", "", "", "a"]]
    path = write_tsv(tmp_path / "d.tsv", DIVERGENCES_HEADER, rows)
    with pytest.raises(ValueError, match="shavian and family are required"):
        load_divergences(path)


def test_divergence_rejects_duplicate_key(tmp_path: Path) -> None:
    row = ["barrier", "ˈbærɪəR", "unstressed", "x", "-ier", "a"]
    path = write_tsv(tmp_path / "d.tsv", DIVERGENCES_HEADER, [row, row])
    with pytest.raises(ValueError, match="duplicate row"):
        load_divergences(path)


def test_shipped_tables_load() -> None:
    mapping = load_mapping()
    assert load_overrides(mapping)
    assert load_quirks()
    assert load_divergences()
