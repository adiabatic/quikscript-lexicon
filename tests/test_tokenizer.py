import pytest

from qslex import letters, load_mapping, load_quirks, normalize, tokenize

MAPPING = load_mapping()
QUIRKS = load_quirks()

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
    ("visual", "ˈvɪʒuəl", "·Vie·It·Zhivago·Ooze·Utter·Low"),
    ("loyal", "ˈlɔɪəl", "·Low·Oy·Utter·Low"),
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
    ("area", "ˈeərɪə", "·Eight·Roe·It·Utter"),
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
]


def transcribe(ipa: str) -> str:
    normalized, _ = normalize(ipa, QUIRKS)
    return letters(tokenize(normalized, MAPPING))


@pytest.mark.parametrize("word,ipa,expected", MANUAL_ANCHORED + RULE_EDGES + QUIRK_ROWS)
def test_transcription(word: str, ipa: str, expected: str):
    assert transcribe(ipa) == expected, word


def test_mapping_self_consistency():
    assert MAPPING.lookup["ɪə"]["stressed"].letters == ("Eat", "Utter")
    assert MAPPING.lookup["ɪə"]["unstressed"].letters == ("It", "Utter")
    assert MAPPING.lookup["eə"]["pre-r"].qs == ""
    assert MAPPING.lookup["u"][""].letters == ("Ooze",)
    assert MAPPING.lookup["ˈ"][""].letters == ()
    assert MAPPING.lookup["Ə"][""].kind == "tag"
    assert MAPPING.lookup["Ð"][""].kind == "word-sign"


def test_stress_marks_do_not_join_split_vowels():
    normalized, _ = normalize("kaɪˈəʊti", QUIRKS)
    tokens = [t.ipa for t in tokenize(normalized, MAPPING)]
    assert "aɪə" not in tokens
    assert "aɪ" in tokens and "əʊ" in tokens


def test_stress_marks_do_not_break_vowel_r_context():
    normalized, _ = normalize("ðeəˈrÆftəR", QUIRKS)
    tokens = tokenize(normalized, MAPPING)
    eas = [t for t in tokens if t.ipa == "eə"]
    assert eas[0].entry.condition == "pre-r"
