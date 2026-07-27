import json

from qslex.build import (
    CONVERTER_JSON,
    LETTERS_HEADER,
    LETTERS_TSV,
    LEXICON_JSON,
    LEXICON_TSV,
    PHRASES_TXT,
    TSV_HEADER,
    artifacts,
    convert,
    letters_tsv,
)
from qslex.csur import CODEPOINT_OF
from qslex.letters import VOWELS

from conftest import KEPT, MAPPING

ENTRIES = convert(KEPT, MAPPING)
BUILT = artifacts(ENTRIES, MAPPING)

ALPHABET = frozenset(chr(codepoint) for codepoint in CODEPOINT_OF.values())
SEPARATORS = frozenset(" -'’./0123456789")


def table(text: str) -> tuple[list[str], list[list[str]]]:
    lines = text.splitlines()
    return lines[0].split("\t"), [line.split("\t") for line in lines[1:]]


def test_the_build_emits_every_declared_artifact() -> None:
    assert set(BUILT) == {
        LEXICON_JSON,
        LEXICON_TSV,
        CONVERTER_JSON,
        PHRASES_TXT,
        LETTERS_TSV,
    }


def test_the_tsv_projection_declares_its_header_and_keeps_to_it() -> None:
    header, rows = table(BUILT[LEXICON_TSV])
    assert tuple(header) == TSV_HEADER
    assert {len(row) for row in rows} == {len(TSV_HEADER)}


def test_the_tsv_projection_is_deduplicated() -> None:
    _, rows = table(BUILT[LEXICON_TSV])
    flat = [tuple(row) for row in rows]
    assert len(flat) == len(set(flat))
    assert len(flat) < len(ENTRIES)


def test_the_two_lexicon_artifacts_are_the_same_projection() -> None:
    _, rows = table(BUILT[LEXICON_TSV])
    grouped = json.loads(BUILT[LEXICON_JSON])
    assert set(grouped) == {entry.headword for entry in ENTRIES}
    records = [record for group in grouped.values() for record in group]
    assert len(records) == len(ENTRIES)
    projection = {
        (
            record["Latn"],
            record["qs"],
            record.get("qs_junior", ""),
            record.get("qs_x", ""),
            record["Shaw"],
            record["pos"],
            record["ipa"],
            str(record["freq"]),
        )
        for record in records
    }
    assert projection == {tuple(row) for row in rows}


def test_the_x_column_is_confined_to_words_with_an_x() -> None:
    ligatures = [entry for entry in ENTRIES if entry.ligature]
    assert ligatures
    assert all("x" in entry.latin.lower() for entry in ligatures)


def test_the_junior_column_is_confined_to_the_word_level_cases() -> None:
    juniors = [entry for entry in ENTRIES if entry.junior]
    assert {entry.latin for entry in juniors} == {
        "always",
        "that",
        "was",
        "wasn't",
        "'twas",
    }


def test_every_qs_string_is_letters_and_separators() -> None:
    allowed = ALPHABET | SEPARATORS
    stray = {
        character
        for entry in ENTRIES
        for column in (entry.qs, entry.junior, entry.ligature)
        for character in column
        if character not in allowed
    }
    assert stray == set()


def test_rendering_the_same_entries_twice_is_byte_identical() -> None:
    again = artifacts(ENTRIES, MAPPING)
    assert {name: text.encode("utf-8") for name, text in again.items()} == {
        name: text.encode("utf-8") for name, text in BUILT.items()
    }


def test_letters_tsv_names_every_codepoint() -> None:
    header, rows = table(letters_tsv(MAPPING))
    assert tuple(header) == LETTERS_HEADER
    assert [row[2] for row in rows] == list(CODEPOINT_OF)


def test_each_letter_row_carries_the_character_for_its_codepoint() -> None:
    _, rows = table(letters_tsv(MAPPING))
    for codepoint, character, name, _, _ in rows:
        assert int(codepoint.removeprefix("U+"), 16) == CODEPOINT_OF[name]
        assert character == chr(CODEPOINT_OF[name])


def test_every_letter_is_a_consonant_a_vowel_or_a_ligature() -> None:
    _, rows = table(letters_tsv(MAPPING))
    kinds = {row[2]: row[3] for row in rows}
    assert set(kinds.values()) == {"consonant", "vowel", "ligature"}
    assert {name for name, kind in kinds.items() if kind == "vowel"} == set(VOWELS)
    assert {name for name, kind in kinds.items() if kind == "ligature"} == {
        "Excite",
        "Exam",
    }
