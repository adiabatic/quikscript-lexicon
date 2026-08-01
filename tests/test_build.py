import json

from qslex.build import (
    HUNSPELL_AFF,
    HUNSPELL_DIC,
    LETTERS_HEADER,
    LEXICON_JSON,
    LEXICON_TSV,
    PHRASES_TXT,
    SCHEMA_VERSION,
    TSV_HEADER,
    artifacts,
)
from qslex.converter import TagMap, converter, load_penn
from qslex.csur import CODEPOINT_OF
from qslex.letters import VOWELS

from conftest import MAPPING, built, entries

ENTRIES = entries()
BUILT = built()

ALPHABET = frozenset(chr(codepoint) for codepoint in CODEPOINT_OF.values())
SEPARATORS = frozenset(" -'’./0123456789")


def table(text: str) -> tuple[list[str], list[list[str]]]:
    lines = text.splitlines()
    return lines[0].split("\t"), [line.split("\t") for line in lines[1:]]


MASTER = json.loads(BUILT[LEXICON_JSON])


def test_the_build_emits_every_declared_artifact() -> None:
    assert set(BUILT) == {
        LEXICON_JSON,
        LEXICON_TSV,
        PHRASES_TXT,
        HUNSPELL_DIC,
        HUNSPELL_AFF,
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
    grouped = MASTER["entries"]
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


def test_the_junior_column_is_confined_to_the_word_level_cases_and_nt() -> None:
    juniors = [entry for entry in ENTRIES if entry.junior]
    assert {entry.latin for entry in juniors} == {
        "always",
        "that",
        "was",
        "'twas",
        "couldn't",
        "didn't",
        "doesn't",
        "hadn't",
        "hasn't",
        "haven't",
        "isn't",
        "mightn't",
        "mustn't",
        "needn't",
        "oughtn't",
        "shouldn't",
        "wasn't",
        "wouldn't",
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


def test_the_master_declares_what_it_holds() -> None:
    assert MASTER["meta"]["version"] == SCHEMA_VERSION
    assert MASTER["meta"]["counts"] == {
        "headwords": len({entry.headword for entry in ENTRIES}),
        "entries": len(ENTRIES),
        "phrases": len(BUILT[PHRASES_TXT].splitlines()),
    }
    assert set(MASTER) == {"meta", "letters", "c5_to_penn", "phrases", "entries"}


def test_the_master_carries_the_converter_shape_it_no_longer_ships() -> None:
    """The proof that dropping qs_converter.json lost nothing.

    Rebuilt from the master's own entries and its own tag map — no other file read —
    and held to what the build derives from the entries in memory.
    """
    rebuilt = converter(
        (
            (
                entry["Latn"],
                entry["pos"],
                entry["qs"],
                entry.get("qs_junior", ""),
                entry.get("qs_x", ""),
            )
            for group in MASTER["entries"].values()
            for entry in group
        ),
        {
            c5: TagMap(c5, penn, "upstream", "")
            for c5, penn in MASTER["c5_to_penn"].items()
        },
    )
    assert rebuilt == converter(
        ((e.latin, e.pos, e.qs, e.junior, e.ligature) for e in ENTRIES), load_penn()
    )


def test_the_masters_tag_map_is_the_table_the_converter_reads() -> None:
    assert MASTER["c5_to_penn"] == {c5: tag.penn for c5, tag in load_penn().items()}


def test_the_masters_phrases_are_the_file_beside_them() -> None:
    assert MASTER["phrases"] == BUILT[PHRASES_TXT].splitlines()


def test_the_masters_letters_name_every_codepoint() -> None:
    assert {tuple(letter) for letter in MASTER["letters"]} == {LETTERS_HEADER}
    assert [letter["name"] for letter in MASTER["letters"]] == list(CODEPOINT_OF)


def test_each_letter_row_carries_the_character_for_its_codepoint() -> None:
    for letter in MASTER["letters"]:
        codepoint = CODEPOINT_OF[letter["name"]]
        assert int(letter["codepoint"].removeprefix("U+"), 16) == codepoint
        assert letter["qs"] == chr(codepoint)


def test_every_letter_is_a_consonant_a_vowel_or_a_ligature() -> None:
    kinds = {letter["name"]: letter["class"] for letter in MASTER["letters"]}
    assert set(kinds.values()) == {"consonant", "vowel", "ligature"}
    assert {name for name, kind in kinds.items() if kind == "vowel"} == set(VOWELS)
    assert {name for name, kind in kinds.items() if kind == "ligature"} == {
        "Excite",
        "Exam",
    }
