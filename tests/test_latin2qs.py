import pytest

pytest.importorskip("spacy")

from qslex.csur import NAME_OF  # noqa: E402
from qslex.latin2qs import (  # noqa: E402
    PREFIXES,
    SUFFIXES,
    Options,
    Transliterator,
    TransliteratorError,
)
from qslex.letters import parse, render_qs  # noqa: E402
from qslex.passages import SPECIMENS, load_passages  # noqa: E402


@pytest.fixture(scope="module")
def t() -> Transliterator:
    return Transliterator()


def qs(names: str) -> str:
    return render_qs(parse(names))


def decoded(text: str) -> str:
    return "".join("·" + NAME_OF[ord(c)] if ord(c) in NAME_OF else c for c in text)


def convert(t: Transliterator, text: str, **kwargs: object) -> str:
    return t.transliterate(text, Options(**kwargs)).strip()  # type: ignore[arg-type]


def words(t: Transliterator, text: str, **kwargs: object) -> list[str]:
    return convert(t, text, **kwargs).split(" ")


# --- heteronyms ---------------------------------------------------------------


def test_read_disambiguates_on_tense(t: Transliterator) -> None:
    present = words(t, "I read books for a living.")[1]
    past = words(t, "Last night I read a chapter to them.")[3]
    assert present == qs("·Roe·Eat·Day")
    assert past == qs("·Roe·Et·Day")


def test_lead_disambiguates_on_part_of_speech(t: Transliterator) -> None:
    verb = words(t, "You lead the way.")[1]
    assert verb == qs("·Low·Eat·Day")


def test_live_disambiguates_on_part_of_speech(t: Transliterator) -> None:
    verb = words(t, "They live here.")[1]
    adjective = words(t, "It was a live broadcast.")[3]
    assert verb == qs("·Low·It·Vie")
    assert adjective == qs("·Low·I·Vie")


def test_that_splits_demonstrative_from_conjunction(t: Transliterator) -> None:
    out = words(t, "I know that that man is here.")
    assert out[2] == qs("·They·Tea")
    assert out[3] == qs("·They·At·Tea")


def test_relative_that_is_the_conjunction(t: Transliterator) -> None:
    out = words(t, "all the words that have been said")
    assert out[3] == qs("·They·Tea")


def test_use_splits_noun_from_verb(t: Transliterator) -> None:
    noun = words(t, "What is the use of it?")[3]
    verb = words(t, "You use it daily.")[1]
    assert noun == qs("·Ye·Ooze·See")
    assert verb == qs("·Ye·Ooze·Zoo")


def test_an_ambiguity_no_tag_settles_stays_joined(t: Transliterator) -> None:
    out = words(t, "They fought against the king.")[2]
    assert out == qs("·Utter·Gay·Et·No·See·Tea") + "⬌" + qs(
        "·Utter·Gay·Eight·No·See·Tea"
    )


# --- possessives and clitics --------------------------------------------------


def test_possessive_s_devoices_after_a_voiceless_final(t: Transliterator) -> None:
    assert words(t, "Jack's hat")[0] == "·" + qs("·Jay·At·Key·See")


def test_possessive_after_a_sibilant_is_bare_zoo(t: Transliterator) -> None:
    assert words(t, "Mr Jones's hat")[1] == qs("·Jay·Owe·No·Zoo·Zoo")


def test_possessive_s_is_voiced_elsewhere(t: Transliterator) -> None:
    assert words(t, "the dog's dinner")[1] == qs("·Day·Ox·Gay·Zoo")


def test_a_bare_possessive_apostrophe_is_dropped(t: Transliterator) -> None:
    assert words(t, "the dogs' dinner")[1] == qs("·Day·Ox·Gay·Zoo")


def test_a_constructed_possessive_is_conditioned_too(t: Transliterator) -> None:
    assert words(t, "Aachen's cathedral")[0] == "·" + qs("·Ah·Key·Utter·No·Zoo")


def test_spoken_contractions_keep_the_apostrophe(t: Transliterator) -> None:
    out = words(t, "They'll say he'd gone; we're sure you've won, I'm told.")
    assert out[0] == qs("·They·Eight") + "’" + qs("·Low")
    assert out[2] == qs("·He·Eat") + "’" + qs("·Day")
    assert out[4] == qs("·Way·Eat") + "’" + qs("·Utter·Roe")
    assert out[6] == qs("·Ye·Ooze") + "’" + qs("·Vie")
    assert out[8] == qs("·I") + "’" + qs("·May")


def test_an_aphetic_word_keeps_its_leading_apostrophe(t: Transliterator) -> None:
    assert words(t, "'Twas the night.")[0] == "’" + qs("·Tea·Way·Utter·Zoo")
    junior = words(t, "'Twas the night.", mode="junior")[0]
    assert junior == "’" + qs("·Tea·Way·Ox·Zoo")


def test_nt_attaches_solid(t: Transliterator) -> None:
    assert words(t, "It wasn't here.")[1] == qs("·Way·Utter·Zoo·No·Tea")
    junior = words(t, "It wasn't here.", mode="junior")[1]
    assert junior == qs("·Way·Ox·Zoo·Utter·No·Tea")
    assert words(t, "You can't win.")[1] == qs("·Key·Ah·No·Tea")


def test_verbal_s_attaches_solid(t: Transliterator) -> None:
    assert words(t, "It's here.")[0] == qs("·It·Tea·See")


def test_all_is_a_word_not_a_contraction_half(t: Transliterator) -> None:
    out = words(t, "I do all the work.")
    assert out[1] == qs("·Day·Ooze")
    assert out[2] == qs("·Awe·Low")


# --- the contraction layer ----------------------------------------------------


def test_the_contraction_layer_is_a_senior_facility(t: Transliterator) -> None:
    with pytest.raises(TransliteratorError, match="Senior facility"):
        Options(mode="junior", contractions=True)


def test_listed_words_contract(t: Transliterator) -> None:
    out = words(t, "I think people can come.", contractions=True)
    assert out[1] == qs("·Thaw")
    assert out[2] == qs("·Pea·Pea·Low")
    assert out[3] == qs("·Key")


def test_a_contracted_stem_takes_its_clitics(t: Transliterator) -> None:
    out = words(t, "She's sure they'll say we'll go.", contractions=True)
    assert out[0] == qs("·She·Zoo")
    assert out[2] == qs("·They·Eight") + "’" + qs("·Low")
    assert out[4] == qs("·Way") + "’" + qs("·Low")


def test_nt_generalises_to_unlisted_stems(t: Transliterator) -> None:
    assert words(t, "You shouldn't go.", contractions=True)[1] == qs("·She·Day·No·Tea")


def test_that_contracts_only_when_not_demonstrative(t: Transliterator) -> None:
    out = words(t, "I know that that man left.", contractions=True)
    assert out[2] == qs("·They·Tea")
    assert out[3] == qs("·They·At·Tea")


def test_a_name_never_contracts(t: Transliterator) -> None:
    assert words(t, "Will Smith arrived.", contractions=True)[0] == "·" + qs(
        "·Way·It·Low"
    )


# --- modes --------------------------------------------------------------------


def test_junior_diverges_at_word_level_only(t: Transliterator) -> None:
    senior = words(t, "I know that it always was.")
    junior = words(t, "I know that it always was.", mode="junior")
    assert senior[2] == qs("·They·Tea")
    assert junior[2] == qs("·They·At·Tea")
    assert senior[4] == qs("·Awe·Low·Way·Utter·Zoo")
    assert junior[4] == qs("·Awe·Low·Way·Eight·Zoo")
    assert senior[5].rstrip(".") == qs("·Way·Utter·Zoo")
    assert junior[5].rstrip(".") == qs("·Way·Ox·Zoo")


def test_the_x_letter_mode_swaps_in_the_x_column(t: Transliterator) -> None:
    senior = words(t, "We expect taxes.")
    x_letter = words(t, "We expect taxes.", mode="x")
    assert senior[1] == qs("·It·Key·See·Pea·Et·Key·Tea")
    assert x_letter[1] == qs("·Et·Excite·Pea·Et·Key·Tea")
    assert x_letter[2].rstrip(".") == qs("·Tea·At·Excite·Zoo")


# --- the namer dot ------------------------------------------------------------


def test_three_name_dots_suffice(t: Transliterator) -> None:
    out = words(t, "At Rome, Jack met Mr Harold Jones")
    assert out[0] == qs("·At·Tea")
    assert out[1].startswith("·" + qs("·Roe"))
    assert out[2] == "·" + qs("·Jay·At·Key")
    assert out[4] == "·" + qs("·May·Roe")
    assert out[5] == qs("·He·At·Roe·Utter·Low·Day")
    assert out[6] == qs("·Jay·Owe·No·Zoo")


def test_the_pronoun_i_takes_no_dot(t: Transliterator) -> None:
    assert words(t, "I agree.")[0] == qs("·I")


def test_a_standalone_letter_takes_a_dot(t: Transliterator) -> None:
    out = words(t, "I need a b and a c now.")
    assert out[2] == qs("·Utter")
    assert out[3] == "·" + qs("·Bay·Eat")


def test_a_name_opening_with_all_takes_its_dot(t: Transliterator) -> None:
    assert words(t, "We met on All Souls Day.")[3] == "·" + qs("·Awe·Low")


def test_an_initialism_takes_one_dot(t: Transliterator) -> None:
    assert words(t, "the BBC reported it")[1] == "·" + qs("·Bay·Eat·Bay·Eat·See·Eat")


def test_an_initialism_no_entity_tags_takes_its_dot(t: Transliterator) -> None:
    assert words(t, "I watched TV last night.")[2] == "·" + qs("·Tea·Eat·Vie·Eat")


def test_shouting_is_not_an_initialism(t: Transliterator) -> None:
    assert words(t, "PLEASE STOP")[0] == qs("·Pea·Low·Eat·Zoo")


# --- punctuation and ordinals -------------------------------------------------


def test_brackets_are_angled(t: Transliterator) -> None:
    out = convert(t, "yes (or no)")
    assert "\ue66e" in out and "\ue66f" in out
    assert "(" not in out and ")" not in out


def test_double_quotes_demote_to_single(t: Transliterator) -> None:
    out = convert(t, '"yes," he said')
    assert "‘" in out and "’" in out
    assert "“" not in out and "”" not in out


def test_etc_is_and_and_and(t: Transliterator) -> None:
    assert words(t, "cats, dogs, etc.")[2].rstrip(".") == qs("·No·No·No")


def test_ordinals_keep_the_numeral(t: Transliterator) -> None:
    out = words(t, "the 21st of May, the 2nd, the 3rd, the 4th, the 1960s")
    assert out[1] == "21" + qs("·See·Tea")
    assert out[5].rstrip(",") == "2" + qs("·No·Day")
    assert out[7].rstrip(",") == "3" + qs("·Roe·Day")
    assert out[9].rstrip(",") == "4" + qs("·Thaw")
    assert out[11] == "1960" + qs("·Zoo")


# --- words the lexicon lacks --------------------------------------------------


def test_an_unmatched_word_is_flagged(t: Transliterator) -> None:
    assert convert(t, "gorblimey xyzzy").endswith("xyzzy✢")


def test_a_constructed_plural_is_conditioned_and_flagged(t: Transliterator) -> None:
    assert (
        words(t, "three abatements here")[1]
        == qs("·Utter·Bay·Eight·Tea·May·No·Tea·See") + "⚠️"
    )


def test_a_constructed_affix_word_is_flagged(t: Transliterator) -> None:
    assert (
        words(t, "it was doglike")[2].rstrip(".") == qs("·Day·Ox·Gay·Low·I·Key") + "⚠️"
    )


def test_the_oer_prefix_builds_the_compounds(t: Transliterator) -> None:
    assert words(t, "the o'erhead beam")[1] == qs("·Owe·Utter·Roe·He·Et·Day") + "⚠️"


def test_affixes_match_what_the_lexicon_does_inside_words(
    t: Transliterator,
) -> None:
    embedded = {
        "anti": "antifreeze",
        "counter": "counterattack",
        "mis": "misspell",
        "non": "nonsense",
        "out": "outbound",
        "over": "overgrown",
        "sub": "subgroup",
        "un": "unhappy",
        "under": "underground",
    }
    for affix, word in embedded.items():
        spelling = t.rows_of[word][-1]["qs"]
        assert spelling.startswith(PREFIXES[affix]), (affix, word)
    embedded = {
        "bound": "outbound",
        "hood": "childhood",
        "ish": "selfish",
        "ism": "capitalism",
        "less": "hopeless",
        "like": "sportsmanlike",
        "ness": "goodness",
        "esque": "statuesque",
    }
    for affix, word in embedded.items():
        spelling = t.rows_of[word][-1]["qs"]
        assert spelling.endswith(SUFFIXES[affix]), (affix, word)


def test_ful_splits_on_the_part_of_speech(t: Transliterator) -> None:
    noun = t.rows_of["spoonful"][-1]["qs"]
    adjective = t.rows_of["careful"][-1]["qs"]
    assert noun.endswith(qs("·Fee·Foot·Low"))
    assert adjective.endswith(qs("·Fee·Utter·Low"))


def test_a_constructed_ful_splits_on_the_part_of_speech(t: Transliterator) -> None:
    assert "capful" not in t.rows_of and "rageful" not in t.rows_of
    noun = words(t, "He drank a capful of it.")[3]
    adjective = words(t, "It was a rageful moment.")[3]
    assert noun == qs("·Key·At·Pea·Fee·Foot·Low") + "⚠️"
    assert adjective == qs("·Roe·Eight·Jay·Fee·Utter·Low") + "⚠️"


# --- words that change before "to" --------------------------------------------


def test_have_to_devoices_before_an_infinitive(t: Transliterator) -> None:
    assert words(t, "I have to go now.")[1] == qs("·He·At·Fee")
    assert words(t, "I have two cats.")[1] == qs("·He·At·Vie")


def test_used_to_devoices_in_the_past_tense(t: Transliterator) -> None:
    assert words(t, "I used to swim.")[1] == qs("·Ye·Ooze·See·Tea")


# --- HTML ---------------------------------------------------------------------


def test_html_markup_passes_through(t: Transliterator) -> None:
    out = t.transliterate("<!doctype html><p>the cat</p>")
    assert out.startswith("<!doctype html><p>")
    assert qs("·Key·At·Tea") in out
    assert out.endswith("</p>")


def test_a_tag_named_like_a_style_block_passes_through(t: Transliterator) -> None:
    body = qs("·They") + " " + qs("·Key·At·Tea")
    out = t.transliterate("<!doctype html><stylesheet></style><p>the cat</p>")
    assert out == "<!doctype html><stylesheet></style><p>" + body + "</p>"
    out = t.transliterate("<!doctype html><scripts><b>hi</b></script>")
    assert out == "<!doctype html><scripts><b>" + qs("·He·I") + "</b></script>"


def test_a_curly_apostrophe_splits_a_contraction_in_html(t: Transliterator) -> None:
    body = qs("·I") + " " + qs("·Day·Owe·No·Tea")
    assert t.transliterate("<!doctype html><p>I don’t</p>") == (
        "<!doctype html><p>" + body + "</p>"
    )


# --- plain text is not HTML ---------------------------------------------------


def test_angle_brackets_are_not_escaped(t: Transliterator) -> None:
    out = convert(t, "1 < 2 and 3 > 2")
    assert out == "1 < 2 " + qs("·No") + " 3 > 2"


def test_an_ampersand_is_not_escaped(t: Transliterator) -> None:
    assert convert(t, "AT&T") == "AT&T"


def test_a_pseudo_tag_gains_no_closing_tag(t: Transliterator) -> None:
    assert convert(t, "a <xyzzy> b") == qs("·Utter") + " <xyzzy✢> ·" + qs("·Bay·Eat")


# --- the Manual's specimen passages -------------------------------------------

# Rows the replay cannot reproduce, each for a reason the layers own: the
# fixture cannot record a leading apostrophe, a phrase match hides a word from
# the word-level contraction layer, Read contracts beyond his own list, and
# the row policy keeps both RRPVar pronunciations of against.
REPLAY_PINS = {
    ("parental-advice", 11): "·Low·It·Tea·Low",
    ("gown-shop", 24): "·Why·Et·Vie",
    ("marys-lamb", 30): "’·Tea·Way·Ox·Zoo",
    ("marys-lamb", 32): "·Utter·Gay·Et·No·See·Tea⬌·Utter·Gay·Eight·No·See·Tea",
}


@pytest.mark.parametrize("passage", sorted(SPECIMENS))
def test_the_specimen_passages_replay(passage: str, t: Transliterator) -> None:
    rows = [w for w in load_passages() if w.passage == passage]
    text = " ".join(w.latin for w in rows)
    if SPECIMENS[passage].level == "senior":
        options = Options(mode="x", contractions=True)
    else:
        options = Options(mode="junior")
    chunks = t.transliterate(text, options).strip().split(" ")
    assert len(chunks) == len(rows)
    for row, chunk in zip(rows, chunks, strict=True):
        if row.verdict == "absent":
            continue
        got = chunk.replace("·", "")
        pin = REPLAY_PINS.get((row.passage, row.index))
        if pin is not None:
            allowed = {render_qs(parse(pin)).replace("·", "")}
        elif row.verdict == "differs":
            allowed = {
                render_qs(parse(row.spelling)).replace("·", ""),
                render_qs(parse(row.ours)).replace("·", ""),
            }
        else:
            allowed = {render_qs(parse(row.spelling)).replace("·", "")}
        assert got in allowed, (
            f"{row.passage} {row.index} {row.latin}: "
            f"got {decoded(got)}, wanted {[decoded(a) for a in allowed]}"
        )
