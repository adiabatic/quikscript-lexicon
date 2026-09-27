from pathlib import Path

import pytest

from qslex import (
    CORE_EIGHT,
    load_contractions,
    load_word_signs,
    sign_for,
    spell,
)
from qslex.elements import components
from qslex.letters import parse
from qslex.words import (
    CONTRACTIONS_HEADER,
    SIGNS_HEADER,
    apply_signs,
)

from conftest import KEPT, TABLES, context_of
from tsv import write_tsv

SIGNS = TABLES.signs
CONTRACTIONS = load_contractions()

ROWS = {(row.word.lower(), row.pos): row for row in KEPT}


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
    return spell(context_of(word, ROWS[(word, pos)]), TABLES).senior


def spelling(word: str, pos: str) -> tuple[str, str]:
    result = spell(context_of(word, ROWS[(word, pos)]), TABLES)
    return result.senior, result.junior or result.senior


def test_core_eight_are_single_signs() -> None:
    for word in CORE_EIGHT:
        sign = SIGNS[(word, "")]
        assert sign.tier == "core"
        assert len(sign.senior.split("·")) == 2, sign.senior
        assert not sign.junior


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


def test_junior_diverges_only_for_a_row_or_the_senior_only_elision() -> None:
    assert spelling("always", "AV0") == (
        "·Awe·Low·Way·Utter·Zoo",
        "·Awe·Low·Way·Eight·Zoo",
    )
    assert spelling("was", "VBD") == ("·Way·Utter·Zoo", "·Way·Ox·Zoo")
    assert spelling("one", "CRD") == ("·Way·Utter·No", "·Way·Utter·No")
    assert spelling("isn't", "VBZ+XX0") == ("·It·Zoo·No·Tea", "·It·Zoo·Utter·No·Tea")


def test_the_was_outline_reaches_inside_both_its_contractions() -> None:
    for pos in ("VBD+XX0", "VM0+XX0"):
        assert spelling("wasn't", pos) == (
            "·Way·Utter·Zoo·No·Tea",
            "·Way·Ox·Zoo·Utter·No·Tea",
        )
    assert spelling("'twas", "PNP+VBD") == ("·Tea·Way·Utter·Zoo", "·Tea·Way·Ox·Zoo")
    assert spelling("doesn't", "VDZ+XX0") == (
        "·Day·Utter·Zoo·No·Tea",
        "·Day·Utter·Zoo·Utter·No·Tea",
    )


def test_no_unlisted_stem_is_substituted_inside_one() -> None:
    assert senior("isn't", "VBZ+XX0") == "·It·Zoo·No·Tea"
    assert senior("'tis", "PNP+VBZ") == "·Tea·It·Zoo"
    assert senior("mustn't", "VM0+XX0") == "·May·Utter·See·No·Tea"
    assert senior("it's", "PNP+VBZ") == "·It·Tea·See"
    assert senior("it'd", "PNI+VHD") == "·It·Tea·Utter·Day"
    assert senior("it'll", "PNP+VM0") == "·It·Tea·Utter·Low"


def test_that_is_spelled_in_full_only_when_demonstrative() -> None:
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
    context = context_of("to-day", ROWS[("to-day", "NN1")])
    assert spell(context, TABLES).signed == ()


def test_apply_signs_reports_only_what_it_changed() -> None:
    context = context_of("as it were", ROWS[("as it were", "AV0")])
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


def test_a_part_of_speech_row_after_a_general_row_is_rejected(tmp_path: Path) -> None:
    extra = [
        ["also", "", "standard", "·Awe·Low·See", "", "", "common-words", ""],
        ["also", "AV0", "standard", "·Awe·Low", "", "", "common-words", ""],
    ]
    with pytest.raises(ValueError, match="already has a general row"):
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


def test_doing_is_carried_under_the_terminal_ing_anchor() -> None:
    doing = [entry for entry in CONTRACTIONS if entry.word == "doing"]
    assert [(e.contraction, e.authority) for e in doing] == [
        ("·Day·-ing", "terminal-ing")
    ]
    assert senior("doing", "VDG") == "·Day·Ooze·-ing"


def test_done_is_carried_under_the_no_how_anchor() -> None:
    done = [entry for entry in CONTRACTIONS if entry.word == "done"]
    assert [(e.contraction, e.authority) for e in done] == [("·Day·No", "no-how")]
    assert not done[0].transliterated
    assert all(e.transliterated for e in CONTRACTIONS if e.word != "done")
    assert senior("done", "VDN") == "·Day·Utter·No"


def test_unknown_contraction_kind(tmp_path: Path) -> None:
    rows = [["also", "", "affix", "·Awe·Low·See", "senior-contractions", ""]]
    path = write_tsv(tmp_path / "c.tsv", CONTRACTIONS_HEADER, rows)
    with pytest.raises(ValueError, match="kind must be one of"):
        load_contractions(path)


def test_an_unadmitted_contraction_authority(tmp_path: Path) -> None:
    rows = [["also", "", "word", "·Awe·Low·See", "common-words", ""]]
    path = write_tsv(tmp_path / "c.tsv", CONTRACTIONS_HEADER, rows)
    with pytest.raises(ValueError, match="not a Manual anchor"):
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


def test_a_latin_hyphen_facing_a_spelled_space_is_not_aligned() -> None:
    letters = parse("·At·Zoo ·It ·Way·Utter·Roe")
    out, _, applied, consulted = apply_signs("as-it-were", "AV0", letters, SIGNS)
    assert out == letters
    assert applied == ()
    assert consulted == ()


def test_a_no_op_row_is_still_consulted() -> None:
    result = spell(context_of("one", ROWS[("one", "CRD")]), TABLES)
    assert result.signs == (("one", ""),)
    assert result.signed == ()
