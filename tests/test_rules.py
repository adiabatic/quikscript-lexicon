import collections

import pytest

from qslex import (
    Context,
    Example,
    Row,
    load_examples,
    load_mapping,
    load_overrides,
    load_quirks,
    load_rows,
    load_tables,
    load_var_tags,
    normalize,
    render,
    select,
    spell,
    tokenize,
)
from qslex.letters import parse, render_qs
from qslex.manual import SIGN_ANCHORS
from qslex.rules import (
    RULE_IDS,
    TERMINAL_RULES,
    Tables,
    load_rule_words,
    load_x_ligatures,
    naive,
    split,
    terminal_for,
    undecided_ing,
)

MAPPING = load_mapping()
QUIRKS = load_quirks()
OVERRIDES = load_overrides(MAPPING)
TABLES = load_tables()
EXAMPLES = load_examples()

BY_WORD: dict[str, list[Row]] = collections.defaultdict(list)
for _row in select(load_var_tags(), load_rows()):
    BY_WORD[_row.word.lower()].append(_row)


def context_for(word: str, pos: str = "") -> Context:
    rows = [row for row in BY_WORD[word] if not pos or row.pos == pos]
    ipa, _ = normalize(rows[0].ipa, QUIRKS)
    return Context(word, rows[0].pos, ipa, tuple(tokenize(ipa, MAPPING, OVERRIDES)))


def spellings(word: str, pos: str) -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    for row in BY_WORD.get(word, []):
        if pos and row.pos != pos:
            continue
        ipa, _ = normalize(row.ipa, QUIRKS)
        context = Context(word, row.pos, ipa, tuple(tokenize(ipa, MAPPING, OVERRIDES)))
        result = spell(context, TABLES)
        out.append((row.pos, result.senior, result.ligature or result.senior))
    return out


def senior(word: str, pos: str = "") -> str:
    produced = spellings(word, pos)
    assert produced, f"{word!r} is not in ReadLex"
    assert len({value for _, value, _ in produced}) == 1, produced
    return produced[0][1]


def ligature(word: str, pos: str = "") -> str:
    produced = spellings(word, pos)
    assert produced, f"{word!r} is not in ReadLex"
    return produced[0][2]


def _in_readlex(example: Example) -> bool:
    rows = BY_WORD.get(example.word, [])
    return any(not example.pos or row.pos == example.pos for row in rows)


IN_READLEX = [example for example in EXAMPLES if _in_readlex(example)]


@pytest.mark.parametrize(
    "example",
    IN_READLEX,
    ids=lambda e: f"{e.rule}:{e.word}:{e.column}",
)
def test_manual_example_words(example: Example) -> None:
    produced = spellings(example.word, example.pos)
    index = 2 if example.column == "ligature" else 1
    values = {row[index] for row in produced}
    assert any(example.matches(value) for value in values), (
        f"{example.word} [{example.source}] wants {example.kind} "
        f"{example.spelling}, got {sorted(values)}"
    )


def test_the_fixture_covers_every_rule() -> None:
    covered = {example.rule for example in EXAMPLES}
    assert covered == set(RULE_IDS) | {"section-2"} | SIGN_ANCHORS


def test_every_manual_source_row_is_a_whole_or_partial_spelling() -> None:
    for example in EXAMPLES:
        if example.source == "manual":
            continue
        assert example.note, example.word


def test_es_ed_drops_the_epenthetic_vowel() -> None:
    assert senior("kisses") == "·Key·It·See·Zoo"
    assert senior("added", "AJ0") == "·At·Day·Day"
    assert senior("fitted", "AJ0") == "·Fee·It·Tea·Day"


def test_es_ed_catches_sites_upstream_wrote_with_a_plain_schwa() -> None:
    assert all("Ə" not in row.ipa for row in BY_WORD["englishes"])
    assert senior("englishes") == "·It·Oolong·Gay·Low·It·She·Zoo"
    assert all("Ə" not in row.ipa for row in BY_WORD["cashboxes"])
    assert senior("cashboxes") == "·Key·At·She·Bay·Ox·Key·See·Zoo"


def test_es_ed_leaves_voicing_alone_because_readlex_already_has_it() -> None:
    assert senior("cups") == "·Key·Utter·Pea·See"
    assert senior("cubs") == "·Key·Utter·Bay·Zoo"
    assert senior("tipped", "VVD") == "·Tea·It·Pea·Tea"


def test_ing_bares_an_affix_but_not_a_root() -> None:
    assert senior("calling", "AJ0") == "·Key·Awe·Low·Oolong"
    assert senior("wing", "NN1") == "·Way·It·Oolong"
    assert senior("bringing", "VVG") == "·Bay·Roe·It·Oolong·Oolong"
    assert senior("carrying", "NN1") == "·Key·At·Roe·It·It·Oolong"


def test_ing_stays_bare_after_a_prefix() -> None:
    assert senior("beings", "NN2") == "·Bay·Eat·Oolong·Zoo"
    assert senior("undoing", "NN1") == "·Utter·No·Day·Ooze·Oolong"
    assert senior("willingness", "NN1") == "·Way·It·Low·Oolong·No·Et·See"


def test_al_omits_the_vowel_only_after_a_consonant() -> None:
    assert senior("tribal", "AJ0") == "·Tea·Roe·I·Bay·Low"
    assert senior("spaniel", "NN1") == "·See·Pea·At·No·Ye·Low"
    assert senior("burial", "NN1") == "·Bay·Et·Roe·It·Utter·Low"
    assert senior("loyal", "AJ0") == "·Low·Oy·Utter·Low"
    assert senior("finally", "AV0") == "·Fee·I·No·Utter·Low·It"


def test_ally_is_written_even_where_the_sound_is_absent() -> None:
    assert senior("basically", "AV0") == "·Bay·Eight·See·It·Key·Utter·Low·It"
    assert senior("capable", "AJ0") == "·Key·Eight·Pea·Utter·Bay·Low"


def test_tion_and_en_on_split_on_the_latin_spelling() -> None:
    assert senior("fashion", "NN1") == "·Fee·At·She·No"
    assert senior("ashen", "AJ0") == "·At·She·Utter·No"
    assert senior("action", "NN1") == "·At·Key·She·No"
    assert senior("vision", "NN1") == "·Vie·It·Zhivago·No"


def test_land_ment_drops_the_vowel_except_in_men() -> None:
    assert senior("england", "NP0") == "·It·Oolong·Gay·Low·No·Day"
    assert senior("seaman", "NN1") == "·See·Eat·May·No"
    assert senior("seamen", "NN2") == "·See·Eat·May·Et·No"
    assert senior("cement", "NN1") == "·See·It·May·Et·No·Tea"


def test_ess_est_writes_et_but_only_where_the_terminal_is_real() -> None:
    assert senior("highest", "AJS") == "·He·I·Et·See·Tea"
    assert senior("hopeless", "AJ0") == "·He·Owe·Pea·Low·Et·See"
    assert senior("goodness", "NN1") == "·Gay·Foot·Day·No·Et·See"
    assert senior("forest", "NN1") == "·Fee·Ox·Roe·It·See·Tea"
    assert senior("honest", "AJ0") == "·Ox·No·Utter·See·Tea"


def test_ain_and_age_normalise_the_unstressed_vowel() -> None:
    assert senior("captain", "NN1") == "·Key·At·Pea·Tea·Utter·No"
    assert senior("maintain", "VVB") == "·May·Eight·No·Tea·Eight·No"
    assert senior("manage", "VVB") == "·May·At·No·Utter·Jay"
    assert senior("marriage", "NN1") == "·May·At·Roe·It·Jay"


def test_ward_is_contracted_but_not_when_stressed() -> None:
    assert senior("eastward", "AJ0") == "·Eat·See·Tea·Way·Day"
    assert senior("forward", "AJ0") == "·Fee·Awe·Roe·Way·Day"
    assert senior("onwards", "AV0") == "·Ox·No·Way·Day·Zoo"
    assert senior("toward") == "·Tea·Utter·Way·Awe·Roe·Day"


def test_ful_follows_readlex_because_it_already_splits_adjective_from_noun() -> None:
    assert senior("careful", "AJ0") == "·Key·Eight·Roe·Fee·Utter·Low"
    assert senior("carefully", "AV0") == "·Key·Eight·Roe·Fee·Utter·Low·It"
    assert senior("spoonful", "NN1") == "·See·Pea·Ooze·No·Fee·Foot·Low"
    assert senior("fully", "AV0") == "·Fee·Foot·Low·It"


def test_con_com_is_the_only_prefix_that_rewrites() -> None:
    assert senior("content", "AJ0") == "·Key·No·Tea·Et·No·Tea"
    assert senior("contents", "NN2") == "·Key·Ox·No·Tea·Et·No·Tea·See"
    assert senior("commend", "VVB") == "·Key·May·Et·No·Day"
    assert senior("comment", "NN1") == "·Key·Ox·May·Et·No·Tea"
    assert senior("company", "NN1") == "·Key·Utter·May·Pea·Utter·No·It"


@pytest.mark.parametrize(
    "word,pos,expected",
    [
        ("unless", "CJS", "·Utter·No·Low·Et·See"),
        ("unknown", "AJ0", "·Utter·No·No·Owe·No"),
        ("announce", "VVB", "·Utter·No·Out·No·See"),
        ("annual", "AJ0", "·At·No·Ye·Ooze·Utter·Low"),
        ("obtain", "VVB", "·Utter·Bay·Tea·Eight·No"),
        ("office", "NN1", "·Ox·Fee·It·See"),
        ("begin", "VVB", "·Bay·It·Gay·It·No"),
        ("receive", "VVB", "·Roe·It·See·Eat·Vie"),
        ("produce", "VVB", "·Pea·Roe·Utter·Day·Ye·Ooze·See"),
        ("persuade", "VVB", "·Pea·Utter·Roe·See·Way·Eight·Day"),
        ("inquire", "VVB", "·It·No·Key·Way·I·Roe"),
    ],
)
def test_the_other_prefixes_are_satisfied_by_readlex_already(
    word: str, pos: str, expected: str
) -> None:
    assert senior(word, pos) == expected


def test_ligature_only_where_orthodox_spells_an_x() -> None:
    assert ligature("tax", "NN1") == "·Tea·At·Excite"
    assert ligature("tacks", "NN2") == "·Tea·At·Key·See"
    assert ligature("next", "ORD") == "·No·Et·Excite·Tea"
    assert ligature("necks", "NN2") == "·No·Et·Key·See"


def test_ligature_takes_et_only_on_a_word_initial_unstressed_ex() -> None:
    assert ligature("expect", "VVB") == "·Et·Excite·Pea·Et·Key·Tea"
    assert ligature("examine", "VVB") == "·Et·Exam·At·May·It·No"
    assert ligature("sixty", "CRD") == "·See·It·Excite·Tea·It"


def test_ligature_reproduces_the_manuals_own_prose_spellings() -> None:
    assert ligature("experiment", "NN1") == "·Et·Excite·Pea·Et·Roe·It·May·No·Tea"
    assert ligature("next", "ORD") == "·No·Et·Excite·Tea"


def test_x_that_is_not_key_see_or_gay_zoo_gets_no_ligature() -> None:
    for word in ("xylophone", "anxious", "sexual", "faux"):
        assert ligature(word) == senior(word)


def test_senior_and_ligature_differ_only_where_recorded() -> None:
    assert senior("expect", "VVB") == "·It·Key·See·Pea·Et·Key·Tea"


def test_a_terminal_or_prefix_rule_reaches_every_element_of_a_compound() -> None:
    assert senior("adding-machine", "NN1") == "·At·Day·Oolong-·May·Utter·She·Eat·No"
    assert senior("adding", "VVG") == "·At·Day·Oolong"
    assert (
        senior("air-conditioned", "AJ0") == "·Eight·Roe-·Key·No·Day·It·She·Utter·No·Day"
    )
    assert (
        senior("combination-lock", "NN1")
        == "·Key·Ox·May·Bay·It·No·Eight·She·No-·Low·Ox·Key"
    )
    assert senior("combination", "NN1") == "·Key·Ox·May·Bay·It·No·Eight·She·No"


def test_the_vowel_before_a_final_l_comes_back_when_a_syllable_follows() -> None:
    assert senior("rifle", "NN1") == "·Roe·I·Fee·Low"
    assert senior("rifleman", "NN1") == "·Roe·I·Fee·Utter·Low·May·No"
    assert senior("able", "AJ0") == "·Eight·Bay·Low"
    assert senior("able-bodied", "AJ0") == "·Eight·Bay·Utter·Low-·Bay·Ox·Day·It·Day"
    assert senior("cable", "NN1") == "·Key·Eight·Bay·Low"
    assert senior("cable-car", "NN1") == "·Key·Eight·Bay·Utter·Low-·Key·Ah·Roe"
    assert senior("feeding-bottle", "NN1") == "·Fee·Eat·Day·Oolong-·Bay·Ox·Tea·Low"


def test_a_ruling_keyed_on_an_element_governs_the_compound() -> None:
    assert senior("left-wing", "NN1") == "·Low·Et·Fee·Tea-·Way·It·Oolong"
    assert senior("well-being", "NN1") == "·Way·Et·Low-·Bay·Eat·Oolong"
    assert senior("ding-dong", "NN1") == "·Day·It·Oolong-·Day·Ox·Oolong"
    assert senior("leading-strings", "NN2") == (
        "·Low·Eat·Day·Oolong-·See·Tea·Roe·It·Oolong·Zoo"
    )


def test_a_compound_keeps_its_own_pronunciation_where_readlex_gives_it_one() -> None:
    assert senior("black-lead", "NN1") == "·Bay·Low·At·Key-·Low·Et·Day"
    assert senior("bay-wreaths", "NN2") == "·Bay·Eight-·Roe·Eat·Thaw·See"
    assert senior("aide-de-camp", "NN1") == "·Eight·Day-·Day·Utter-·Key·Ah·May"
    assert senior("a la mode", "AV0") == "·Ah ·Low·Ah ·May·Owe·Day"


def test_split_marks_only_the_element_the_entry_ends_on_as_final() -> None:
    context = context_for("adding-machine", "NN1")
    elements = split(context, naive(context))
    assert [(e.context.latin, e.word, e.context.final) for e in elements] == [
        ("adding", True, False),
        ("-", False, False),
        ("machine", True, True),
    ]


def test_split_gives_a_prefix_form_entry_no_final_element() -> None:
    context = context_for("after-", "PRE")
    elements = split(context, naive(context))
    assert [e.context.final for e in elements if e.word] == [False]


def test_split_leaves_an_entry_the_alignment_guard_rejects_whole() -> None:
    for word in ("to-day", "dhs"):
        context = context_for(word)
        elements = split(context, naive(context))
        assert [(e.context.latin, e.context.final) for e in elements] == [(word, True)]
    assert senior("to-day", "NN1") == "·Tea·Utter·Day·Eight"


def test_terminal_rules_are_mutually_exclusive() -> None:
    for word in ("fashion", "ashen", "settlement", "eagle", "manage", "highest"):
        found = terminal_for(context_for(word))
        assert found is not None, word
        assert sum(1 for rule in TERMINAL_RULES if rule is found[0]) == 1


def test_rule_ids_are_unique_and_ordered_prefix_then_terminal() -> None:
    assert len(RULE_IDS) == len(set(RULE_IDS))
    assert len(RULE_IDS) == 26


def test_parse_round_trips_a_spelling_with_separators() -> None:
    for spelling in (
        "·Bay·Eat",
        "·Eat·See·Tea·Way·Day",
        "·Way·Utter·Roe·Low·Day-·Way·It",
    ):
        assert render(parse(spelling)) == spelling


def test_render_qs_agrees_with_the_letter_names() -> None:
    letters = naive(context_for("baker"))
    assert render(letters) == "·Bay·Eight·Key·Utter·Roe"
    assert len(render_qs(letters)) == 5


def test_naive_marks_only_the_first_letter_of_a_token_as_stressed() -> None:
    letters = naive(context_for("highest", "AJS"))
    price, schwa = letters[1], letters[2]
    assert (price.name, price.stressed) == ("I", True)
    assert (schwa.name, schwa.stressed) == ("Utter", False)


def test_undecided_ing_defers_to_any_participle_suffix() -> None:
    assert undecided_ing("wing", {"calling"})
    assert not undecided_ing("bookkeeping", {"keeping"})
    assert not undecided_ing("carrying", set())


def test_spell_without_tables_still_produces_a_spelling() -> None:
    assert spell(context_for("calling"), Tables()).senior == "·Key·Awe·Low·Oolong"


def test_every_ruling_carries_an_authority_and_a_note() -> None:
    for (rule, word), entry in load_rule_words().items():
        assert entry.authority, (rule, word)
        assert entry.note, (rule, word)


def test_every_ligature_ruling_names_a_word_with_an_x() -> None:
    for word, entry in load_x_ligatures().items():
        assert "x" in word
        assert entry.note


def test_ligature_rulings_parse_to_known_letters() -> None:
    for entry in load_x_ligatures().values():
        assert render(parse(entry.ligature)) == entry.ligature
