import pytest

from qslex import normalize
from qslex.quirks import QuirkRule

from conftest import QUIRKS

ORDER_SENSITIVE = [
    ("hodler", "ˈhɑdləR", "ˈhɒdləR"),
    ("hodlers", "ˈhɑdləRz", "ˈhɒdləRz"),
    ("montpensier", "ˌmɑnˈpɒnsieɪ", "ˌmɒnˈpɒnsieɪ"),
    ("reigelheimer", "ˈrɑɪgelhɑɪməR", "ˈraɪɡelhaɪməR"),
    ("brainpan", "ˈbrainpæn", "ˈbreɪnpæn"),
    ("lobotomise", "ləˈbɒtəmaiz", "ləˈbɒtəmaɪz"),
    ("sabah", "ˈsaːbɑː", "ˈsɑːbɑː"),
    ("nauvoo", "nɔˈːvuː", "nɔːˈvuː"),
    ("goulburn", "ˈɡəʊlbəːRn", "ˈɡəʊlbəRn"),
    ("snowboard", "ˈsnəʊbɔRd", "ˈsnəʊbɔːRd"),
    ("tradesperson", "ˈtreɪdzpɛːRsən", "ˈtreɪdzpɜːRsən"),
    ("llanfair", "Lænˈfeər", "ɬænˈfeər"),
    ("juliana", "ˌdʒuːliˈⱭː.nə", "ˌdʒuːliˈⱭːnə"),
    ("bimorphic", "̩ˌbaɪˈmɔːRfɪk", "ˌbaɪˈmɔːRfɪk"),
]


@pytest.mark.parametrize("word,raw,expected", ORDER_SENSITIVE)
def test_normalization(word: str, raw: str, expected: str) -> None:
    assert normalize(raw, QUIRKS)[0] == expected, word


def test_untouched_strings_pass_through() -> None:
    for ipa in ["ˈbeɪkəR", "kəˈrɪəR", "hɜːRt", "fjuː", "ˈvɪʒuəl"]:
        assert normalize(ipa, QUIRKS) == (ipa, ())


def test_applied_indices_are_reported() -> None:
    _, applied = normalize("ˈhɑdləR", QUIRKS)
    assert len(applied) == 1
    assert QUIRKS[applied[0]].match == "ˈhɑdləR"


def test_row_scope_requires_exact_match() -> None:
    rules = (QuirkRule("row", "abc", "xyz", "w", "n"),)
    assert normalize("abcd", rules) == ("abcd", ())
    assert normalize("abc", rules) == ("xyz", (0,))


def test_rules_apply_in_file_order() -> None:
    rules = (
        QuirkRule("sub", "a", "b", "w", "n"),
        QuirkRule("sub", "b", "c", "w", "n"),
    )
    assert normalize("a", rules) == ("c", (0, 1))


def test_syllabic_marker_rule_is_anchored() -> None:
    assert normalize("bʌtn̩", QUIRKS)[0] == "bʌtn̩"
    assert normalize("̩bʌtn", QUIRKS)[0] == "bʌtn"


def test_every_shipped_rule_cites_the_issue_it_repairs() -> None:
    for rule in QUIRKS:
        assert rule.note.endswith("(#7)"), rule.match
