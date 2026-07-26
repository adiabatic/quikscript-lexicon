from qslex.mapping import load_mapping
from qslex.overrides import load_overrides
from qslex.roundtrip import (
    EDITS,
    MERGES,
    SEQUENCES,
    align,
    phonemes_of,
    source_phonemes,
    spelt_phonemes,
)
from qslex.tokenizer import tokenize

MAPPING = load_mapping()
OVERRIDES = load_overrides(MAPPING)
READ_BACK = phonemes_of(MAPPING)


def said(ipa: str) -> tuple[str, ...]:
    return source_phonemes(tuple(tokenize(ipa, MAPPING, OVERRIDES)))


def test_every_letter_reads_back_to_at_least_one_phoneme() -> None:
    assert all(phonemes for phonemes in READ_BACK.values())
    assert READ_BACK["Utter"] == ("ə",)
    assert READ_BACK["Roe"] == ("r",)


def test_the_ligature_letters_read_back_to_their_two_sounds() -> None:
    assert READ_BACK["Excite"] == ("k", "s")
    assert READ_BACK["Exam"] == ("ɡ", "z")


def test_the_merges_leave_every_letter_one_reading() -> None:
    written: dict[str, set[str]] = {}
    for entry in MAPPING.entries:
        if len(entry.letters) == 1 and entry.ipa not in SEQUENCES:
            token = MERGES.get(entry.ipa, entry.ipa)
            written.setdefault(entry.letters[0], set()).add(token)
    assert {name: sounds for name, sounds in written.items() if len(sounds) > 1} == {}
    assert written["Utter"] == {"ə"}


def test_stress_marks_and_separators_say_nothing() -> None:
    assert said("ˈkæt") == ("k", "æ", "t")
    assert said("ˌkæt-ˈdɒɡ") == ("k", "æ", "t", "d", "ɒ", "ɡ")


def test_a_spelling_reads_back_letter_by_letter() -> None:
    assert spelt_phonemes("·Key·At·Tea", READ_BACK) == ("k", "æ", "t")
    assert spelt_phonemes("·No·Et·Excite·Tea", READ_BACK) == ("n", "e", "k", "s", "t")


def test_an_untouched_spelling_reads_straight_back() -> None:
    assert said("kæt") == spelt_phonemes("·Key·At·Tea", READ_BACK)


def test_an_elided_vowel_is_a_licensed_difference() -> None:
    assert align(("l", "ɪ", "t", "ə", "l"), ("l", "ɪ", "t", "l")) == (("ə", ""),)


def test_an_inserted_schwa_is_a_licensed_difference() -> None:
    assert align(("k", "l", "ɪ"), ("k", "ə", "l", "ɪ")) == (("", "ə"),)


def test_a_lost_or_changed_consonant_is_not_licensed() -> None:
    assert align(("k", "æ", "p"), ("k", "æ")) is None
    assert align(("k", "æ", "t"), ("ɡ", "æ", "t")) is None


def test_every_licensed_difference_says_why() -> None:
    assert all(EDITS.values())
