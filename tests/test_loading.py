import json
from pathlib import Path

import pytest

from qslex import load_mapping, load_overrides, load_quirks, readlex
from qslex.converter import (
    EXCEPTIONS_HEADER,
    PENN_HEADER,
    load_penn,
    load_phrase_exceptions,
)
from qslex.divergences import DIVERGENCES_HEADER, load_divergences
from qslex.mapping import HEADER
from qslex.overrides import OVERRIDES_HEADER
from qslex.quirks import QUIRKS_HEADER
from qslex.readlex import CorpusError, Row, load_rows
from qslex.variants import TAGS_HEADER, canonical, kept, load_var_tags, select

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


ENTRY: dict[str, object] = {
    "Latn": "pea",
    "Shaw": "𐑐𐑰",
    "pos": "NN1",
    "ipa": "piː",
    "freq": 1,
    "var": "RRP",
}


def corpus_file(tmp_path: Path, corpus: object) -> Path:
    path = tmp_path / "readlex.json"
    path.write_text(json.dumps(corpus, ensure_ascii=False), encoding="utf-8")
    return path


def entry(**changed: object) -> dict[str, object]:
    return {**ENTRY, **changed}


def without(field: str) -> dict[str, object]:
    return {key: value for key, value in ENTRY.items() if key != field}


def test_missing_corpus_is_a_clear_error(tmp_path: Path) -> None:
    with pytest.raises(CorpusError, match="not found"):
        load_rows(tmp_path / "absent.json")


def test_tampered_corpus_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(CorpusError, match="SHA-256"):
        load_rows(corpus_file(tmp_path, {"pea_NN1": [ENTRY]}))


def test_malformed_json_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "readlex.json"
    path.write_text('{"pea_NN1": [', encoding="utf-8")
    with pytest.raises(CorpusError, match="Expecting"):
        load_rows(path, verify=False)


def test_a_non_object_corpus_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(CorpusError, match="expected an object of headwords"):
        load_rows(corpus_file(tmp_path, [ENTRY]), verify=False)


@pytest.mark.parametrize("entries", [[], {}, "", None, ENTRY])
def test_a_headword_needs_a_non_empty_list(tmp_path: Path, entries: object) -> None:
    with pytest.raises(CorpusError, match="is not a non-empty list"):
        load_rows(corpus_file(tmp_path, {"pea_NN1": entries}), verify=False)


def test_an_entry_must_be_an_object(tmp_path: Path) -> None:
    with pytest.raises(CorpusError, match="expected an object, got str"):
        load_rows(corpus_file(tmp_path, {"pea_NN1": ["pea"]}), verify=False)


def test_a_missing_field_is_rejected(tmp_path: Path) -> None:
    corpus = {"pea_NN1": [without("ipa")]}
    with pytest.raises(CorpusError, match=r"missing \['ipa'\]"):
        load_rows(corpus_file(tmp_path, corpus), verify=False)


def test_an_unexpected_field_is_rejected(tmp_path: Path) -> None:
    corpus = {"pea_NN1": [entry(Latin="pea")]}
    with pytest.raises(CorpusError, match=r"unexpected fields \['Latin'\]"):
        load_rows(corpus_file(tmp_path, corpus), verify=False)


@pytest.mark.parametrize("frequency", ["1", 1.5, None, []])
def test_a_non_integer_frequency_is_rejected(tmp_path: Path, frequency: object) -> None:
    corpus = {"pea_NN1": [entry(freq=frequency)]}
    with pytest.raises(CorpusError, match="freq is not a number"):
        load_rows(corpus_file(tmp_path, corpus), verify=False)


def test_a_wrong_headword_count_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(readlex, "CORPUS_HEADWORDS", 2)
    with pytest.raises(CorpusError, match="expected 2 headwords, got 1"):
        load_rows(corpus_file(tmp_path, {"pea_NN1": [ENTRY]}), verify=False)


def test_a_wrong_row_count_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(readlex, "CORPUS_HEADWORDS", 1)
    monkeypatch.setattr(readlex, "CORPUS_ROWS", 2)
    with pytest.raises(CorpusError, match="expected 2 rows, got 1"):
        load_rows(corpus_file(tmp_path, {"pea_NN1": [ENTRY]}), verify=False)


def test_a_good_corpus_flattens_in_file_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(readlex, "CORPUS_HEADWORDS", 2)
    monkeypatch.setattr(readlex, "CORPUS_ROWS", 3)
    corpus = {
        "pea_NN1": [ENTRY, entry(pos="VVB", freq=2)],
        "bay_NN1": [entry(Latn="bay", Shaw="𐑚𐑱", ipa="beɪ")],
    }
    rows = load_rows(corpus_file(tmp_path, corpus), verify=False)
    assert [row.headword for row in rows] == ["pea_NN1", "pea_NN1", "bay_NN1"]
    assert [row.pos for row in rows] == ["NN1", "VVB", "NN1"]
    assert rows[1].frequency == 2
    assert rows[2].word == "bay"
    assert rows[2].var == "RRP"


GOOD_TAGS = [
    ["RRP", "RRP", "keep", "3", "", "the only accent this lexicon spells"],
    ["RRPVar", "RRP", "keep", "1", "again", "a second RRP pronunciation"],
    ["GenAm", "GenAm", "drop", "2", "", "General American"],
]


def tags_file(tmp_path: Path, rows: list[list[str]]) -> Path:
    return write_tsv(tmp_path / "v.tsv", TAGS_HEADER, rows)


def test_good_var_tags_load(tmp_path: Path) -> None:
    tags = load_var_tags(tags_file(tmp_path, GOOD_TAGS))
    assert canonical(tags, "RRPVar") == "RRP"
    assert kept(tags, "RRPVar")
    assert not kept(tags, "GenAm")
    assert tags["RRPVar"].declared_words == ("again",)
    assert tags["RRP"].rows == 3


def test_var_tags_bad_header(tmp_path: Path) -> None:
    path = write_tsv(tmp_path / "v.tsv", TAGS_HEADER[:-1], [])
    with pytest.raises(ValueError, match="unexpected header"):
        load_var_tags(path)


def test_var_tags_wrong_field_count(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="expected 6 fields"):
        load_var_tags(tags_file(tmp_path, [["RRP", "RRP", "keep"]]))


def test_var_tags_reject_an_empty_tag(tmp_path: Path) -> None:
    rows = [*GOOD_TAGS, ["", "RRP", "keep", "0", "", "n"]]
    with pytest.raises(ValueError, match="empty tag"):
        load_var_tags(tags_file(tmp_path, rows))


def test_var_tags_reject_an_unknown_policy(tmp_path: Path) -> None:
    rows = [["RRP", "RRP", "maybe", "3", "", "n"]]
    with pytest.raises(ValueError, match="policy must be one of"):
        load_var_tags(tags_file(tmp_path, rows))


def test_var_tags_reject_a_non_numeric_row_count(tmp_path: Path) -> None:
    rows = [["RRP", "RRP", "keep", "many", "", "n"]]
    with pytest.raises(ValueError, match="rows must be a number"):
        load_var_tags(tags_file(tmp_path, rows))


def test_var_tags_reject_a_duplicate_row(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="duplicate row for 'RRP'"):
        load_var_tags(tags_file(tmp_path, [GOOD_TAGS[0], GOOD_TAGS[0]]))


def test_an_undocumented_tag_must_declare_the_words_it_covers(tmp_path: Path) -> None:
    rows = [*GOOD_TAGS, ["SSB", "SSB", "drop", "1", "", "n"]]
    with pytest.raises(ValueError, match="must declare the words it covers"):
        load_var_tags(tags_file(tmp_path, rows))


def test_var_tags_reject_a_missing_note(tmp_path: Path) -> None:
    rows = [["RRP", "RRP", "keep", "3", "", ""]]
    with pytest.raises(ValueError, match="every tag needs a note"):
        load_var_tags(tags_file(tmp_path, rows))


def test_var_tags_reject_a_canonical_with_no_row_of_its_own(tmp_path: Path) -> None:
    rows = [["RRP", "GenAm", "keep", "3", "", "n"]]
    with pytest.raises(ValueError, match="has no row of its own"):
        load_var_tags(tags_file(tmp_path, rows))


def test_var_tags_reject_a_canonical_that_disagrees_on_policy(tmp_path: Path) -> None:
    rows = [
        ["RRP", "RRP", "keep", "3", "", "n"],
        ["TrapBath", "RRP", "drop", "1", "", "n"],
    ]
    with pytest.raises(ValueError, match="disagree on policy"):
        load_var_tags(tags_file(tmp_path, rows))


def test_a_variant_tag_nobody_has_ruled_on_is_rejected(tmp_path: Path) -> None:
    tags = load_var_tags(tags_file(tmp_path, GOOD_TAGS))
    with pytest.raises(ValueError, match="no policy for the variant tag"):
        canonical(tags, "Martian")


def test_select_keeps_only_the_rrp_family(tmp_path: Path) -> None:
    tags = load_var_tags(tags_file(tmp_path, GOOD_TAGS))
    rows = [
        Row("pea_NN1", "pea", "𐑐𐑰", "NN1", "piː", 1, "RRP"),
        Row("pea_NN1", "pea", "𐑐𐑰", "NN1", "piː", 1, "RRPVar"),
        Row("pea_NN1", "pea", "𐑐𐑰", "NN1", "piː", 1, "GenAm"),
    ]
    assert select(tags, rows) == tuple(rows[:2])


GOOD_PENN = [
    ["NN1", "NN", "upstream", "singular noun"],
    ["NP0", "NNP", "upstream", "proper noun"],
    ["VVB", "VBP", "standard", "base present"],
]


def penn_file(tmp_path: Path, rows: list[list[str]]) -> Path:
    return write_tsv(tmp_path / "p.tsv", PENN_HEADER, rows)


def test_good_penn_rows_load(tmp_path: Path) -> None:
    penn = load_penn(penn_file(tmp_path, GOOD_PENN))
    assert penn["NP0"].penn == "NNP"
    assert penn["VVB"].evidence == "standard"


def test_penn_bad_header(tmp_path: Path) -> None:
    path = write_tsv(tmp_path / "p.tsv", PENN_HEADER[:-1], [])
    with pytest.raises(ValueError, match="unexpected header"):
        load_penn(path)


def test_penn_wrong_field_count(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="expected 4 fields"):
        load_penn(penn_file(tmp_path, [["NN1", "NN"]]))


def test_penn_rejects_unknown_evidence(tmp_path: Path) -> None:
    rows = [["NN1", "NN", "vibes", "singular noun"]]
    with pytest.raises(ValueError, match="evidence must be one of"):
        load_penn(penn_file(tmp_path, rows))


def test_penn_rejects_a_tag_with_no_place_in_the_row_order(tmp_path: Path) -> None:
    rows = [["CRD", "CD", "standard", "cardinal number"]]
    with pytest.raises(ValueError, match="has no place in the row order"):
        load_penn(penn_file(tmp_path, rows))


def test_penn_rejects_a_missing_note(tmp_path: Path) -> None:
    rows = [["NN1", "NN", "upstream", ""]]
    with pytest.raises(ValueError, match="every mapping needs a note"):
        load_penn(penn_file(tmp_path, rows))


def test_penn_rejects_a_duplicate_row(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="duplicate row for 'NN1'"):
        load_penn(penn_file(tmp_path, [GOOD_PENN[0], GOOD_PENN[0]]))


GOOD_EXCEPTIONS = [
    ["&amp;", "html-entity", "not a lexicon entry at all"],
    ["cannot", "tokenizer-split", "a documented spaCy tokenizer exception"],
]


def exceptions_file(tmp_path: Path, rows: list[list[str]]) -> Path:
    return write_tsv(tmp_path / "e.tsv", EXCEPTIONS_HEADER, rows)


def test_good_phrase_exceptions_load(tmp_path: Path) -> None:
    listed = load_phrase_exceptions(exceptions_file(tmp_path, GOOD_EXCEPTIONS))
    assert [exception.entry for exception in listed] == ["&amp;", "cannot"]
    assert listed[1].reason == "tokenizer-split"


def test_phrase_exceptions_bad_header(tmp_path: Path) -> None:
    path = write_tsv(tmp_path / "e.tsv", EXCEPTIONS_HEADER[:-1], [])
    with pytest.raises(ValueError, match="unexpected header"):
        load_phrase_exceptions(path)


def test_phrase_exceptions_wrong_field_count(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="expected 3 fields"):
        load_phrase_exceptions(exceptions_file(tmp_path, [["cannot", "html-entity"]]))


def test_phrase_exceptions_reject_an_unknown_reason(tmp_path: Path) -> None:
    rows = [["cannot", "vibes", "a documented spaCy tokenizer exception"]]
    with pytest.raises(ValueError, match="reason must be one of"):
        load_phrase_exceptions(exceptions_file(tmp_path, rows))


def test_phrase_exceptions_reject_a_missing_note(tmp_path: Path) -> None:
    rows = [["cannot", "tokenizer-split", ""]]
    with pytest.raises(ValueError, match="every exception needs a note"):
        load_phrase_exceptions(exceptions_file(tmp_path, rows))


def test_phrase_exceptions_reject_a_duplicate_row(tmp_path: Path) -> None:
    rows = [GOOD_EXCEPTIONS[1], GOOD_EXCEPTIONS[1]]
    with pytest.raises(ValueError, match="duplicate row for 'cannot'"):
        load_phrase_exceptions(exceptions_file(tmp_path, rows))


def test_shipped_tables_load() -> None:
    mapping = load_mapping()
    assert load_overrides(mapping)
    assert load_quirks()
    assert load_divergences()
    assert load_var_tags()
    assert load_penn()
    assert load_phrase_exceptions()
