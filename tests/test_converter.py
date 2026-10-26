import pytest

from qslex.converter import (
    JOIN,
    ConverterError,
    PhraseException,
    TagMap,
    converter,
    phrases,
)

PEA = chr(0xE650)
BAY = chr(0xE651)
TEA = chr(0xE652)
DAY = chr(0xE653)

PENN = {
    "AJ0": TagMap("AJ0", "JJ", "upstream", "adjective"),
    "NN0": TagMap("NN0", "NN", "upstream", "number-neutral noun"),
    "NN1": TagMap("NN1", "NN", "upstream", "singular noun"),
    "NP0": TagMap("NP0", "NNP", "upstream", "proper noun"),
    "VVB": TagMap("VVB", "VBP", "standard", "base present"),
}


def test_one_spelling_gets_one_untagged_row() -> None:
    entries = [("Pea", "NN1", PEA, "", "")]
    assert converter(entries, PENN) == {"pea": [{"qs": PEA, "tag": "0"}]}


def test_several_spellings_under_one_penn_tag_stay_untagged() -> None:
    entries = [("bow", "NN1", PEA, "", ""), ("bow", "NN0", BAY, "", "")]
    assert converter(entries, PENN) == {"bow": [{"qs": PEA + JOIN + BAY, "tag": "0"}]}


def test_several_spellings_and_tags_put_the_untagged_row_last() -> None:
    entries = [("bow", "NN1", PEA, "", ""), ("bow", "VVB", BAY, "", "")]
    assert converter(entries, PENN)["bow"] == [
        {"qs": PEA, "tag": "NN"},
        {"qs": BAY, "tag": "VBP"},
        {"qs": PEA + JOIN + BAY, "tag": "0"},
    ]


def test_the_untagged_row_joins_the_distinct_spellings_by_codepoint() -> None:
    entries = [
        ("bow", "NN1", TEA, "", ""),
        ("bow", "VVB", PEA, "", ""),
        ("bow", "AJ0", TEA, "", ""),
        ("bow", "NP0", BAY, "", ""),
    ]
    assert converter(entries, PENN)["bow"][-1] == {
        "qs": JOIN.join((PEA, BAY, TEA)),
        "tag": "0",
    }


def test_the_sparse_columns_appear_only_when_they_differ() -> None:
    entries = [("pea", "NN1", PEA, PEA, PEA)]
    assert converter(entries, PENN) == {"pea": [{"qs": PEA, "tag": "0"}]}
    entries = [("pea", "NN1", PEA, BAY, TEA)]
    assert converter(entries, PENN) == {
        "pea": [{"qs": PEA, "qs_junior": BAY, "qs_x": TEA, "tag": "0"}]
    }


def test_an_entry_with_no_junior_contributes_its_senior() -> None:
    entries = [("bow", "NN1", PEA, DAY, ""), ("bow", "VVB", BAY, "", "")]
    assert converter(entries, PENN)["bow"][-1] == {
        "qs": PEA + JOIN + BAY,
        "qs_junior": DAY + JOIN + BAY,
        "tag": "0",
    }


def test_rows_come_out_in_penn_order_with_proper_nouns_first() -> None:
    entries = [
        ("reading", "NN1", PEA, "", ""),
        ("reading", "NP0", BAY, "", ""),
        ("reading", "VVB", TEA, "", ""),
        ("reading", "AJ0", DAY, "", ""),
    ]
    tags = [row["tag"] for row in converter(entries, PENN)["reading"]]
    assert tags == ["NNP", "JJ", "NN", "VBP", "0"]


def test_a_c5_tag_with_no_penn_equivalent_stops_a_multi_spelling_word() -> None:
    entries = [("bow", "NN1", PEA, "", ""), ("bow", "ZZ0", BAY, "", "")]
    with pytest.raises(ConverterError, match="no Penn equivalent"):
        converter(entries, PENN)


def test_a_c5_tag_with_no_penn_equivalent_is_ignored_on_one_spelling() -> None:
    entries = [("pea", "NN1", PEA, "", ""), ("pea", "ZZ0", PEA, "", "")]
    assert converter(entries, PENN) == {"pea": [{"qs": PEA, "tag": "0"}]}


def test_one_spelling_with_two_junior_forms_cannot_be_lined_up() -> None:
    entries = [("pea", "NN1", PEA, BAY, ""), ("pea", "VVB", PEA, TEA, "")]
    with pytest.raises(ConverterError, match="cannot be lined up"):
        converter(entries, PENN)


LEXICON = converter(
    [
        ("as", "NN1", PEA, "", ""),
        ("at", "NN1", BAY, "", ""),
        ("cat", "NN1", TEA, "", ""),
        ("cream", "NN1", BAY, "", ""),
        ("don't", "VVB", TEA, "", ""),
        ("home", "NN1", TEA, "", ""),
        ("ice", "NN1", PEA, "", ""),
        ("it", "NN1", BAY, "", ""),
        ("were", "NN1", TEA, "", ""),
        ("as it were", "NN1", PEA + " " + BAY + " " + TEA, "", ""),
        ("at home", "NN1", PEA + " " + PEA, "", ""),
        ("ice-box", "NN1", PEA + "-" + DAY, "", ""),
        ("ice-cream", "NN1", PEA + "-" + BAY, "", ""),
    ],
    PENN,
)


def test_a_single_word_with_an_apostrophe_never_composes() -> None:
    listed = phrases(LEXICON, ())
    assert "don't" in listed
    assert "cat" not in listed


def test_an_entry_its_own_parts_spell_is_left_to_the_tokenizer() -> None:
    listed = phrases(LEXICON, ())
    assert "ice-cream" not in listed
    assert "as it were" not in listed


def test_an_entry_whose_parts_are_missing_from_the_lexicon_is_listed() -> None:
    assert "ice-box" in phrases(LEXICON, ())


def test_an_entry_whose_parts_spell_something_else_is_listed() -> None:
    assert "at home" in phrases(LEXICON, ())


def test_a_phrase_exception_is_listed_however_it_composes() -> None:
    exceptions = (PhraseException("cat", "html-entity", "note"),)
    assert phrases(LEXICON, exceptions) == ("at home", "cat", "don't", "ice-box")


def test_the_phrase_list_is_sorted_and_deduplicated() -> None:
    exceptions = (
        PhraseException("don't", "tokenizer-split", "note"),
        PhraseException("cat", "html-entity", "note"),
    )
    listed = phrases(LEXICON, exceptions)
    assert listed == tuple(sorted(set(listed)))
    assert listed.count("don't") == 1
