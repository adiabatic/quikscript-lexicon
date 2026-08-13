import pytest

from qslex import letters, normalize, tokenize
from qslex.tokenizer import TokenizeError, is_stressed

from conftest import MAPPING, OVERRIDES, QUIRKS

MANUAL_ANCHORED = [
    ("year", "jɪəR", "·Ye·Eat·Utter·Roe"),
    ("moor", "mʊəR", "·May·Ooze·Utter·Roe"),
    ("mere", "mɪəR", "·May·Eat·Utter·Roe"),
    ("mire", "ˈmaɪəR", "·May·I·Roe"),
    ("sour", "ˈsaʊəR", "·See·Out·Roe"),
    ("our", "ˈaʊəR", "·Out·Roe"),
    ("career", "kəˈrɪəR", "·Key·Utter·Roe·Eat·Utter·Roe"),
    ("appear", "əˈpɪəR", "·Utter·Pea·Eat·Utter·Roe"),
    ("carrier", "ˈkærɪəR", "·Key·At·Roe·It·Utter·Roe"),
    ("happier", "ˈhæpɪəR", "·He·At·Pea·It·Utter·Roe"),
    ("senior", "ˈsiːnɪəR", "·See·Eat·No·It·Utter·Roe"),
    ("idea", "aɪˈdɪə", "·I·Day·Eat·Utter"),
    ("there", "ðeəR", "·They·Eight·Roe"),
    ("few", "fjuː", "·Fee·Ye·Ooze"),
    ("hut", "hʌt", "·He·Utter·Tea"),
    ("hurt", "hɜːRt", "·He·Utter·Roe·Tea"),
    ("are", "ɑːR", "·Ah·Roe"),
    ("baker", "ˈbeɪkəR", "·Bay·Eight·Key·Utter·Roe"),
    ("loyal", "ˈlɔɪəl", "·Low·Oy·Utter·Low"),
    ("india", "ˈɪndɪə", "·It·No·Day·It·Utter"),
    ("area", "ˈeərɪə", "·Eight·Roe·It·Utter"),
]

MANUAL_MODERNIZED = [
    ("visual", "ˈvɪʒuəl", "·Vie·It·Zhivago·Ooze·Utter·Low"),
]

RULE_EDGES = [
    ("thereafter", "ðeəˈrÆftəR", "·They·Eight·Roe·At·Fee·Tea·Utter·Roe"),
    ("coyote", "kaɪˈəʊti", "·Key·I·Owe·Tea·It"),
    ("period", "ˈpɪərɪəd", "·Pea·Eat·Utter·Roe·It·Utter·Day"),
    ("geographic", "ˌdʒɪəˈɡræfɪk", "·Jay·Eat·Utter·Gay·Roe·At·Fee·It·Key"),
    ("bell-flower", "ˈbel-flaʊəR", "·Bay·Et·Low-·Fee·Low·Out·Roe"),
    ("anti-hero", "ˈænti-hɪərəʊ", "·At·No·Tea·It-·He·Eat·Utter·Roe·Owe"),
    ("world-weary", "ˈwɜːRld-wɪəri", "·Way·Utter·Roe·Low·Day-·Way·Eat·Utter·Roe·It"),
    ("theatre", "ˈθɪətəR", "·Thaw·Eat·Utter·Tea·Utter·Roe"),
    ("player", "ˈpleɪəR", "·Pea·Low·Eight·Utter·Roe"),
    ("lawyer", "ˈlɔɪəR", "·Low·Oy·Utter·Roe"),
    ("science", "ˈsaɪəns", "·See·I·Utter·No·See"),
    ("bio", "ˈbaɪəʊ", "·Bay·I·Owe"),
    ("diode", "ˈdaɪəʊd", "·Day·I·Owe·Day"),
    ("flyover", "ˈflaɪəʊvəR", "·Fee·Low·I·Owe·Vie·Utter·Roe"),
    ("heliograph", "ˈhiːlɪəʊɡræf", "·He·Eat·Low·It·Owe·Gay·Roe·At·Fee"),
    ("radio", "ˈreɪdiəʊ", "·Roe·Eight·Day·It·Owe"),
    ("bowel", "ˈbaʊəl", "·Bay·Out·Utter·Low"),
    ("yeah", "ˈjeə", "·Ye·Et·Utter"),
    ("koch", "kɒx", "·Key·Ox·Loch"),
    ("kisses", "ˈkɪsƏz", "·Key·It·See·Utter·Zoo"),
    ("banquet", "ˈbæŋkwIt", "·Bay·At·Oolong·Key·Way·It·Tea"),
    ("bath-broad", "bⱭːθ", "·Bay·Ah·Thaw"),
    ("bath-flat", "bÆθ", "·Bay·At·Thaw"),
    ("the", "Ð", "·They"),
    ("awhile", "əˈʍaɪl", "·Utter·Why·I·Low"),
]

HIATUS_IS_NOT_SPELLED = [
    ("angrier", "ˈæŋɡrɪ+əR", "·At·Oolong·Gay·Roe·It·Utter·Roe"),
    ("courtship", "ˈkɔːRt+ʃɪp", "·Key·Awe·Roe·Tea·She·It·Pea"),
]

STRESS_OVERRIDDEN = [
    ("reindeer", "ˈreɪndɪəR", "·Roe·Eight·No·Day·Eat·Utter·Roe"),
    ("atmosphere", "ˈætməsfɪəR", "·At·Tea·May·Utter·See·Fee·Eat·Utter·Roe"),
    ("headgear", "ˈhedɡɪəR", "·He·Et·Day·Gay·Eat·Utter·Roe"),
    ("windermere", "ˈwɪndəRmɪəR", "·Way·It·No·Day·Utter·Roe·May·Eat·Utter·Roe"),
    ("hereafter", "hɪəˈrÆftəR", "·He·Eat·Utter·Roe·At·Fee·Tea·Utter·Roe"),
    ("theoretical", "θɪəˈretɪkəl", "·Thaw·Eat·Utter·Roe·Et·Tea·It·Key·Utter·Low"),
    ("nirvana", "nɪəRˈvɑːnə", "·No·Eat·Utter·Roe·Vie·Ah·No·Utter"),
    ("compeer", "ˈkɒmpɪəR", "·Key·Ox·May·Pea·Eat·Utter·Roe"),
    ("greybeard", "ˈɡreɪbɪəRd", "·Gay·Roe·Eight·Bay·Eat·Utter·Roe·Day"),
]

QUIRK_ROWS = [
    ("llanfair", "Lænˈfeər", "·Llan·At·No·Fee·Eight·Roe"),
    ("nauvoo", "nɔˈːvuː", "·No·Awe·Vie·Ooze"),
    ("brainpan", "ˈbrainpæn", "·Bay·Roe·Eight·No·Pea·At·No"),
    ("lobotomise", "ləˈbɒtəmaiz", "·Low·Utter·Bay·Ox·Tea·Utter·May·I·Zoo"),
    ("sabah", "ˈsaːbɑː", "·See·Ah·Bay·Ah"),
    ("hodler", "ˈhɑdləR", "·He·Ox·Day·Low·Utter·Roe"),
    ("snowboard", "ˈsnəʊbɔRd", "·See·No·Owe·Bay·Awe·Roe·Day"),
    ("hyperfocus", "ˌhaɪpəRˈf𐑴kəs", "·He·I·Pea·Utter·Roe·Fee·Owe·Key·Utter·See"),
    ("oakshott", "ˈəʊ𐑑ʃɒt", "·Owe·Key·She·Ox·Tea"),
    ("juliana", "ˌdʒuːliˈⱭː.nə", "·Jay·Ooze·Low·It·Ah·No·Utter"),
    (
        "tradesperson",
        "ˈtreɪdzpɛːRsən",
        "·Tea·Roe·Eight·Day·Zoo·Pea·Utter·Roe·See·Utter·No",
    ),
    ("yevgeny", "yevˈɡeni", "·Ye·Et·Vie·Gay·Et·No·It"),
    ("drm", "ˈdiːɑrˈem", "·Day·Eat·Ah·Roe·Et·May"),
    ("goulburn", "ˈɡəʊlbəːRn", "·Gay·Owe·Low·Bay·Utter·Roe·No"),
    ("bimorphic", "̩ˌbaɪˈmɔːRfɪk", "·Bay·I·May·Awe·Roe·Fee·It·Key"),
    ("teabag", "ˈtiːbæg", "·Tea·Eat·Bay·At·Gay"),
    ("sweatshirt", "ˈswetʃɜːRt", "·See·Way·Et·Tea·She·Utter·Roe·Tea"),
    ("wiltshire", "ˈwɪltʃəR", "·Way·It·Low·Tea·She·Utter·Roe"),
    (
        "somersetshire",
        "ˈsʌməRsetʃəR",
        "·See·Utter·May·Utter·Roe·See·Et·Tea·She·Utter·Roe",
    ),
    (
        "ursae majoris",
        "ˌɜːRsaɪ mədˈʒɔːRɪs",
        "·Utter·Roe·See·I ·May·Utter·Jay·Awe·Roe·It·See",
    ),
    ("jonnie", "ˈdzɒni", "·Jay·Ox·No·It"),
    ("whate'er", "ʍɒtˈe+əR", "·Why·Ox·Tea·Eight·Roe"),
    ("whatsoe'er", "ˌʍɒtsəʊˈe+əR", "·Why·Ox·Tea·See·Owe·Eight·Roe"),
    ("sierra leone", "sɪˌerə lɪˈəʊn", "·See·It·Eight·Roe·Utter ·Low·It·Owe·No"),
]

ALL_CASES = (
    MANUAL_ANCHORED
    + MANUAL_MODERNIZED
    + RULE_EDGES
    + HIATUS_IS_NOT_SPELLED
    + STRESS_OVERRIDDEN
    + QUIRK_ROWS
)


def transcribe(ipa: str) -> str:
    normalized, _ = normalize(ipa, QUIRKS)
    return letters(tokenize(normalized, MAPPING, OVERRIDES))


@pytest.mark.parametrize("word,ipa,expected", ALL_CASES)
def test_transcription(word: str, ipa: str, expected: str) -> None:
    assert transcribe(ipa) == expected, word


def test_unmapped_symbol_raises() -> None:
    with pytest.raises(TokenizeError) as caught:
        tokenize("pȹt", MAPPING)
    assert caught.value.position == 1


def test_mapping_self_consistency() -> None:
    assert MAPPING.lookup["ɪə"]["stressed"].letters == ("Eat", "Utter")
    assert MAPPING.lookup["ɪə"]["unstressed"].letters == ("It", "Utter")
    assert MAPPING.lookup["eə"]["pre-r"].qs == chr(0xE673)
    assert MAPPING.lookup["u"][""].letters == ("Ooze",)
    assert MAPPING.lookup["ˈ"][""].letters == ()
    assert MAPPING.lookup["Ə"][""].kind == "tag"
    assert MAPPING.lookup["Ð"][""].kind == "word-sign"
    assert MAPPING.lookup["+"][""].kind == "hiatus"


def test_stress_marks_do_not_join_split_vowels() -> None:
    normalized, _ = normalize("kaɪˈəʊti", QUIRKS)
    tokens = [t.ipa for t in tokenize(normalized, MAPPING, OVERRIDES)]
    assert "aɪə" not in tokens
    assert "aɪ" in tokens and "əʊ" in tokens


def test_stress_marks_do_not_break_vowel_r_context() -> None:
    normalized, _ = normalize("ðeəˈrÆftəR", QUIRKS)
    tokens = tokenize(normalized, MAPPING, OVERRIDES)
    eas = [t for t in tokens if t.ipa == "eə"]
    assert eas[0].entry.condition == "pre-r"


def test_a_schwa_only_hiatus_tail_is_not_a_word_of_its_own() -> None:
    assert not is_stressed("ˈkiːn+nəs", 7)
    assert not is_stressed("ˈfriː+əst", 6)
    assert not is_stressed("ˈjʊk+kə", 6)
    assert not is_stressed("ˈwɪlt+ʃəR", 7)


def test_a_hiatus_tail_with_a_stressable_vowel_keeps_the_fallback() -> None:
    assert is_stressed("ˈbʊk+kiːpɪŋ", 6)
    assert is_stressed("ˈswet+ʃɜːRt", 7)
    assert is_stressed("ˈklɪp+bɔːRd", 7)
    assert is_stressed("ˈkɔːRt+ʃɪp", 8)
    assert is_stressed("ˈkuːl+li", 7)
    assert is_stressed("ˈsəʊl+ləsli", 7)


def test_overrides_only_fire_on_their_own_string() -> None:
    assert transcribe("ˈhedɡɪəR") == "·He·Et·Day·Gay·Eat·Utter·Roe"
    assert transcribe("ˈhedɡɪəRz") == "·He·Et·Day·Gay·It·Utter·Roe·Zoo"
