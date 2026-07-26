from pathlib import Path

import pytest

from qslex import (
    CORE_EIGHT,
    Context,
    load_contractions,
    load_mapping,
    load_overrides,
    load_quirks,
    load_rows,
    load_tables,
    load_word_signs,
    normalize,
    sign_for,
    spell,
    tokenize,
)
from qslex.elements import components
from qslex.letters import parse
from qslex.words import (
    CONTRACTIONS_HEADER,
    SIGNS_HEADER,
    apply_signs,
)

from tsv import write_tsv

MAPPING = load_mapping()
QUIRKS = load_quirks()
OVERRIDES = load_overrides(MAPPING)
TABLES = load_tables()
SIGNS = TABLES.signs
CONTRACTIONS = load_contractions()

ROWS = {(row.word.lower(), row.pos): row for row in load_rows()}


CORE_ROWS = [
    [word, "", "core", sign, "", full, "junior-contractions", "note"]
    for word, sign, full in (
        ("the", "·They", "·They·Utter"),
        ("of", "·Vie", "·Ox·Vie"),
        ("and", "·No", "·At·No·Day"),
        ("to", "·Tea", "·Tea·Foot"),
        ("it", "·It", "·It·Tea"),
        ("is", "·Zoo", "·It·Zoo"),
        ("for", "·Fee", "·Fee·Awe·Roe"),
        ("be", "·Bay", "·Bay·Eat"),
    )
]


def signs_file(tmp_path: Path, extra: list[list[str]]) -> Path:
    return write_tsv(tmp_path / "s.tsv", SIGNS_HEADER, CORE_ROWS + extra)


def senior(word: str, pos: str) -> str:
    row = ROWS[(word, pos)]
    ipa, _ = normalize(row.ipa, QUIRKS)
    context = Context(word, pos, ipa, tuple(tokenize(ipa, MAPPING, OVERRIDES)))
    return spell(context, TABLES).senior


def spelling(word: str, pos: str) -> tuple[str, str]:
    row = ROWS[(word, pos)]
    ipa, _ = normalize(row.ipa, QUIRKS)
    context = Context(word, pos, ipa, tuple(tokenize(ipa, MAPPING, OVERRIDES)))
    result = spell(context, TABLES)
    return result.senior, result.junior or result.senior


def test_core_eight_are_single_signs() -> None:
    for word in CORE_EIGHT:
        sign = SIGNS[(word, "")]
        assert sign.tier == "core"
        assert len(sign.senior.split("·")) == 2, sign.senior
        assert not sign.junior


@pytest.mark.parametrize(
    ("word", "pos", "want"),
    [
        ("the", "AT0", "·They"),
        ("of", "PRF", "·Vie"),
        ("and", "CJC", "·No"),
        ("to", "PRP", "·Tea"),
        ("for", "PRP", "·Fee"),
        ("it", "PNP", "·It"),
        ("is", "VBZ", "·Zoo"),
        ("be", "VBI", "·Bay"),
    ],
)
def test_core_signs_reach_the_column(word: str, pos: str, want: str) -> None:
    assert senior(word, pos) == want


@pytest.mark.parametrize(
    ("word", "pos", "capital"),
    [
        ("the", "AT0", "Ð"),
        ("of", "PRF", "V"),
        ("and", "CJC", "N"),
        ("to", "PRP", "T"),
        ("for", "PRP", "F"),
    ],
)
def test_upstream_capitals_deliver_five_of_them(
    word: str, pos: str, capital: str
) -> None:
    assert ROWS[(word, pos)].ipa == capital


@pytest.mark.parametrize(("word", "pos"), [("it", "PNP"), ("is", "VBZ"), ("be", "VBI")])
def test_the_other_three_carry_ordinary_ipa(word: str, pos: str) -> None:
    assert ROWS[(word, pos)].ipa in {"ɪt", "ɪz", "biː"}


def test_abbreviations_beat_the_expanded_pronunciation() -> None:
    assert senior("mr", "NP0") == "·May·Roe"
    assert senior("mrs", "NP0") == "·May·Zoo"
    assert senior("dr", "NP0") == "·Day·Utter·Roe"


def test_junior_diverges_only_where_a_row_says_so() -> None:
    assert spelling("always", "AV0") == (
        "·Awe·Low·Way·Utter·Zoo",
        "·Awe·Low·Way·Eight·Zoo",
    )
    assert spelling("was", "VBD") == ("·Way·Utter·Zoo", "·Way·Ox·Zoo")
    assert spelling("one", "CRD") == ("·Way·Utter·No", "·Way·Utter·No")


def test_that_is_spelt_in_full_only_when_demonstrative() -> None:
    assert spelling("that", "DT0") == ("·They·At·Tea", "·They·At·Tea")
    assert spelling("that", "CJT") == ("·They·Tea", "·They·At·Tea")
    assert spelling("that", "AV0") == ("·They·Tea", "·They·At·Tea")


def test_a_phrase_is_signed_word_by_word() -> None:
    assert senior("as it were", "AV0") == "·At·Zoo ·It ·Way·Utter·Roe"
    assert senior("that is", "AV0") == "·They·At·Tea ·Zoo"
    assert senior("would-be", "AJ0") == "·Way·Foot·Day-·Bay"


def test_a_phrase_does_not_take_its_own_tag_for_a_word_inside_it() -> None:
    assert senior("that", "AV0") == "·They·Tea"
    assert senior("that is", "AV0").startswith("·They·At·Tea")


def test_standard_outline_overrules_a_weak_vowel() -> None:
    assert senior("at-home", "NN1") == "·At·Tea-·He·Owe·May"


def test_a_part_of_speech_row_beats_the_general_one() -> None:
    assert sign_for(SIGNS, "use", "NN1") is not None
    assert sign_for(SIGNS, "use", "NN1") != sign_for(SIGNS, "use", "VVB")
    assert senior("use", "NN1") == "·Ye·Ooze·See"
    assert senior("use", "VVB") == "·Ye·Ooze·Zoo"


def test_components_splits_on_spaces_and_hyphens() -> None:
    assert components("as it were") == ("as", " ", "it", " ", "were")
    assert components("would-be") == ("would", "-", "be")
    assert components("was") == ("was",)
    assert components("after-") == ("after", "-", "")
    assert senior("after-", "PRE") == "·At·Fee·Tea·Utter·Roe-"


def test_signs_are_skipped_when_the_word_and_the_ipa_disagree_on_shape() -> None:
    row = ROWS[("to-day", "NN1")]
    ipa, _ = normalize(row.ipa, QUIRKS)
    context = Context("to-day", row.pos, ipa, tuple(tokenize(ipa, MAPPING, OVERRIDES)))
    assert spell(context, TABLES).signed == ()


def test_apply_signs_reports_only_what_it_changed() -> None:
    row = ROWS[("as it were", "AV0")]
    ipa, _ = normalize(row.ipa, QUIRKS)
    context = Context(
        "as it were", row.pos, ipa, tuple(tokenize(ipa, MAPPING, OVERRIDES))
    )
    assert spell(context, TABLES).signed == ("it",)


def test_unknown_tier(tmp_path: Path) -> None:
    extra = [["also", "", "senior", "·Awe·Low·See", "", "", "common-words", ""]]
    with pytest.raises(ValueError, match="tier must be one of"):
        load_word_signs(signs_file(tmp_path, extra))


def test_unknown_authority(tmp_path: Path) -> None:
    extra = [["also", "", "standard", "·Awe·Low·See", "", "", "section-2", ""]]
    with pytest.raises(ValueError, match="not a Manual anchor"):
        load_word_signs(signs_file(tmp_path, extra))


def test_uncontracted_form_outside_the_core_eight(tmp_path: Path) -> None:
    extra = [
        ["also", "", "standard", "·Awe·Low·See", "", "·Awe·Low", "common-words", ""]
    ]
    with pytest.raises(ValueError, match="only recorded for"):
        load_word_signs(signs_file(tmp_path, extra))


def test_unknown_letter_name_in_a_sign(tmp_path: Path) -> None:
    extra = [["also", "", "standard", "·Awe·Lo", "", "", "common-words", ""]]
    with pytest.raises(ValueError, match="unknown letter names in senior"):
        load_word_signs(signs_file(tmp_path, extra))


def test_junior_repeating_senior_is_rejected(tmp_path: Path) -> None:
    extra = [
        [
            "also",
            "",
            "standard",
            "·Awe·Low·See",
            "·Awe·Low·See",
            "",
            "common-words",
            "",
        ]
    ]
    with pytest.raises(ValueError, match="leave junior empty"):
        load_word_signs(signs_file(tmp_path, extra))


def test_an_unreachable_part_of_speech_row_is_rejected(tmp_path: Path) -> None:
    extra = [
        ["also", "", "standard", "·Awe·Low·See", "", "", "common-words", ""],
        ["also", "AV0", "standard", "·Awe·Low", "", "", "common-words", ""],
    ]
    with pytest.raises(ValueError, match="can never be reached"):
        load_word_signs(signs_file(tmp_path, extra))


def test_a_missing_core_sign_is_rejected(tmp_path: Path) -> None:
    path = write_tsv(tmp_path / "s.tsv", SIGNS_HEADER, CORE_ROWS[:-1])
    with pytest.raises(ValueError, match="missing core word signs"):
        load_word_signs(path)


def test_signs_do_not_shadow_one_another(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="duplicate row"):
        load_word_signs(signs_file(tmp_path, CORE_ROWS[:1]))


def test_every_manual_contraction_is_loaded() -> None:
    by_word = {entry.word for entry in CONTRACTIONS}
    for word in ("also", "perhaps", "cannot", "whatever", "yours", "often"):
        assert word in by_word
    assert {entry.kind for entry in CONTRACTIONS} == {"word", "clitic"}


def test_a_listed_contraction_does_not_reach_the_senior_column() -> None:
    assert senior("often", "AV0") == "·Ox·Fee·Utter·No"
    assert senior("people", "NN0") == "·Pea·Eat·Pea·Low"


def test_unknown_contraction_kind(tmp_path: Path) -> None:
    rows = [["also", "", "affix", "·Awe·Low·See", "senior-contractions", ""]]
    path = write_tsv(tmp_path / "c.tsv", CONTRACTIONS_HEADER, rows)
    with pytest.raises(ValueError, match="kind must be one of"):
        load_contractions(path)


def test_a_clitic_needs_a_note(tmp_path: Path) -> None:
    rows = [["'ll", "", "clitic", "’·Low", "senior-contractions", ""]]
    path = write_tsv(tmp_path / "c.tsv", CONTRACTIONS_HEADER, rows)
    with pytest.raises(ValueError, match="needs a note"):
        load_contractions(path)


def test_apply_signs_leaves_an_unaligned_spelling_alone() -> None:
    letters = parse("·Tea·Utter·Day·Eight")
    out, _, applied, consulted = apply_signs("to-day", "NN1", letters, SIGNS)
    assert out == letters
    assert applied == ()
    assert consulted == ()


def test_a_latin_hyphen_facing_a_spelt_space_is_not_aligned() -> None:
    letters = parse("·At·Zoo ·It ·Way·Utter·Roe")
    out, _, applied, consulted = apply_signs("as-it-were", "AV0", letters, SIGNS)
    assert out == letters
    assert applied == ()
    assert consulted == ()


def test_a_no_op_row_is_still_consulted() -> None:
    row = ROWS[("one", "CRD")]
    ipa, _ = normalize(row.ipa, QUIRKS)
    context = Context("one", row.pos, ipa, tuple(tokenize(ipa, MAPPING, OVERRIDES)))
    result = spell(context, TABLES)
    assert result.signs == (("one", ""),)
    assert result.signed == ()
