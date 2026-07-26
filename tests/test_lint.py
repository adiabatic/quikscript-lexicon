from pathlib import Path

import pytest

from qslex.lint import (
    CHECK_IDS,
    CHECKS,
    PRAGMAS_HEADER,
    lint,
    load_pragmas,
    sites,
)
from qslex.rules import NO_TABLES


def broken(word: str, spelling: str, ipa: str, ligature: str = "") -> set[str]:
    return {check for check, _, _ in lint(word, spelling, ligature, ipa, NO_TABLES)}


def pragma_file(tmp_path: Path, rows: list[list[str]]) -> Path:
    lines = ["\t".join(PRAGMAS_HEADER)] + ["\t".join(row) for row in rows]
    path = tmp_path / "p.tsv"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_every_check_says_what_the_manual_requires() -> None:
    assert len(set(CHECK_IDS)) == len(CHECKS)
    assert all(check.requires for check in CHECKS)


def test_the_shipped_pragmas_load() -> None:
    pragmas = load_pragmas()
    assert pragmas
    assert all(check in CHECK_IDS for check, _ in pragmas)


def test_an_element_is_cut_where_the_spelling_and_the_latin_agree() -> None:
    cut = sites("corn-exchange", "·Key·Awe·Roe·No-·It·Key·See", "", "ˈkɔːRn-ɪks")
    assert [site.latin for site in cut] == ["corn", "exchange"]
    assert [site.last for site in cut] == [False, True]


def test_a_misaligned_entry_is_treated_as_one_element() -> None:
    cut = sites("to-day", "·Tea·Day·Eight", "", "təˈdeɪ")
    assert [site.latin for site in cut] == ["to-day"]


def test_an_ing_affix_may_not_keep_its_vowel() -> None:
    assert "terminal-ing-vowel-omitted" in broken(
        "abasing", "·Utter·Bay·Eight·See·It·Oolong", "əˈbeɪsɪŋ"
    )
    assert "terminal-ing-vowel-omitted" not in broken(
        "abasing", "·Utter·Bay·Eight·See·Oolong", "əˈbeɪsɪŋ"
    )


def test_a_root_ending_in_y_or_i_keeps_its_vowel() -> None:
    assert not broken("carrying", "·Key·At·Roe·It·It·Oolong", "ˈkærɪɪŋ")
    assert not broken("skiing", "·See·Key·Eat·It·Oolong", "ˈskiːɪŋ")


def test_a_final_l_drops_only_an_unstressed_vowel() -> None:
    assert "terminal-al-vowel-omitted" in broken(
        "final", "·Fee·I·No·Utter·Low", "ˈfaɪnəl"
    )
    assert "terminal-al-vowel-omitted" not in broken(
        "final", "·Fee·I·No·Low", "ˈfaɪnəl"
    )
    assert "terminal-al-vowel-omitted" not in broken(
        "distil", "·Day·It·See·Tea·It·Low", "dɪˈstɪl"
    )


def test_a_vowel_before_the_l_keeps_the_one_after_it() -> None:
    assert not broken("loyal", "·Low·Oy·Utter·Low", "ˈlɔɪəl")
    assert not broken("burial", "·Bay·Et·Roe·It·Utter·Low", "ˈberɪəl")


def test_ent_and_ance_are_written_invariably_with_utter() -> None:
    assert "terminal-ent-ance-utter" in broken(
        "urgent", "·Utter·Roe·Jay·It·No·Tea", "ˈɜːRdʒənt"
    )
    assert "terminal-ent-ance-utter" not in broken(
        "urgent", "·Utter·Roe·Jay·Utter·No·Tea", "ˈɜːRdʒənt"
    )


def test_ment_is_not_ent() -> None:
    assert not broken("abasement", "·Utter·Bay·Eight·See·May·No·Tea", "əˈbeɪsmənt")


def test_land_and_ment_omit_the_unstressed_vowel() -> None:
    assert "terminal-land-ment-vowel-omitted" in broken(
        "abasement", "·Utter·Bay·Eight·See·May·Utter·No·Tea", "əˈbeɪsmənt"
    )


def test_men_is_the_one_that_keeps_its_vowel() -> None:
    assert not broken("dutchmen", "·Day·Utter·Cheer·May·Utter·No", "ˈdʌtʃmən")
    assert not broken("seamen", "·See·Eat·May·Et·No", "ˈsiːmen")
    assert "terminal-men-keeps-a-vowel" in broken(
        "dutchmen", "·Day·Utter·Cheer·May·No", "ˈdʌtʃmən"
    )


def test_an_initial_ex_takes_et_before_the_ligature() -> None:
    assert "initial-ex-et" in broken(
        "excite", "·It·Key·See·I·Tea", "ɪkˈsaɪt", "·It·Excite·I·Tea"
    )
    assert "initial-ex-et" not in broken(
        "excite", "·It·Key·See·I·Tea", "ɪkˈsaɪt", "·Et·Excite·I·Tea"
    )


def test_a_stressed_ex_keeps_its_own_vowel() -> None:
    assert "initial-ex-et" not in broken(
        "exit", "·It·Key·See·It·Tea", "ˈeksɪt", "·It·Excite·It·Tea"
    )


def test_no_more_ligatures_than_the_latin_has_x() -> None:
    assert "x-ligature-only-with-x" in broken(
        "next", "·No·Et·Key·See·Tea", "nekst", "·No·Et·Excite·Excite"
    )
    assert "x-ligature-only-with-x" not in broken(
        "xerox", "·Zhivago·Eat·Roe·Ox·Key·See", "ˈzɪəRɒks", "·Zhivago·Eat·Roe·Ox·Excite"
    )


def test_a_pragma_needs_a_known_reason(tmp_path: Path) -> None:
    rows = [["initial-ex-et", "pre-exist", "because-i-said-so", ""]]
    with pytest.raises(ValueError, match="reason must be 'known-defect'"):
        load_pragmas(pragma_file(tmp_path, rows))


def test_a_pragma_for_an_unknown_check_is_rejected(tmp_path: Path) -> None:
    rows = [["no-such-check", "pre-exist", "stressed", ""]]
    with pytest.raises(ValueError, match="is not a check"):
        load_pragmas(pragma_file(tmp_path, rows))


def test_a_known_defect_must_say_what_it_is(tmp_path: Path) -> None:
    rows = [["initial-ex-et", "pre-exist", "known-defect", ""]]
    with pytest.raises(ValueError, match="needs a note"):
        load_pragmas(pragma_file(tmp_path, rows))
