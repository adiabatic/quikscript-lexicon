import json
from pathlib import Path

import pytest

from qslex.added import ADDED_HEADER, load_added_words
from qslex.build import LEXICON_JSON, LEXICON_TSV, PHRASES_TXT
from qslex.letters import parse, render_qs
from qslex.rules import spell

from conftest import ADDED, CORPUS, TABLES, built, context_of
from tsv import write_tsv

BUILT = built()
MASTER = json.loads(BUILT[LEXICON_JSON])

GOOD = [
    "quikscript",
    "NP0",
    "ˈkwɪkskrɪpt",
    "𐑒𐑢𐑦𐑒𐑕𐑒𐑮𐑦𐑐𐑑",
    "0",
    "·Key·Way·It·Key·See·Key·Roe·It·Pea·Tea",
    "quikscript.net",
    "a note",
]


def added_file(tmp_path: Path, rows: list[list[str]]) -> Path:
    return write_tsv(tmp_path / "added-words.tsv", ADDED_HEADER, rows)


def test_the_shipped_table_loads_and_every_row_declares_its_provenance() -> None:
    assert ADDED
    for entry in ADDED:
        assert entry.source and entry.note
        assert entry.word == entry.word.lower()
        assert entry.headword == f"{entry.word}_{entry.pos}_{entry.shavian}"


def test_the_rules_produce_every_spelling_the_table_declares() -> None:
    """The build spells added words with the rules and never reads their `qs` column, so this test checks that column against the rules.

    The validator runs the same check. This copy covers a run of the test suite alone.
    """
    for entry in ADDED:
        result = spell(context_of(entry.word, entry.row), TABLES)
        assert result.senior == entry.qs, entry.word
        assert not result.junior and not result.x_letter, entry.word


def test_no_added_word_duplicates_a_word_the_corpus_already_carries() -> None:
    corpus = {row.word.lower() for row in CORPUS}
    assert not {entry.word for entry in ADDED} & corpus


def test_both_spellings_of_the_name_share_one_quikscript_spelling() -> None:
    """quikscript and quickscript are one word under two Latin spellings.

    The possessive is that spelling plus ·See, devoiced after the voiceless ·Tea. It needs its own row. There is no plural row, so no other entry in the lexicon has that spelling.
    """
    by_word = {entry.word: entry.qs for entry in ADDED}
    base = by_word["quikscript"]
    assert by_word["quickscript"] == base
    assert by_word["quikscript's"] == base + "·See"
    assert by_word["quickscript's"] == base + "·See"


def test_the_added_words_reach_the_master_and_the_flat_projection() -> None:
    rows = {tuple(line.split("\t")[:2]) for line in BUILT[LEXICON_TSV].splitlines()[1:]}
    for entry in ADDED:
        assert entry.headword in MASTER["entries"]
        assert (entry.word, render_qs(parse(entry.qs))) in rows


def test_the_master_counts_the_added_words_separately() -> None:
    """`meta.source` names the ReadLex repository and commit, and ReadLex is no longer the source of every entry."""
    assert MASTER["meta"]["counts"]["added"] == len(ADDED)


def test_the_possessives_are_listed_as_phrases() -> None:
    """A single word with an apostrophe never composes, so a tokenizer must match it whole. Upstream’s guy's, lloyd's and parkinson's are listed for the same reason."""
    listed = set(BUILT[PHRASES_TXT].split())
    assert {"quikscript's", "quickscript's"} <= listed


@pytest.mark.parametrize(
    ("field", "value", "complaint"),
    [
        (0, "", "word, pos and ipa are all required"),
        (0, "Quikscript", "must be lowercase"),
        (1, "", "word, pos and ipa are all required"),
        (2, "", "word, pos and ipa are all required"),
        (3, "quikscript", "must be written in the Shavian block"),
        (3, "", "must be written in the Shavian block"),
        (4, "often", "freq must be a number"),
        (5, "Key·Way", "qs must be ·-prefixed"),
        (5, "·Kee·Way", "unknown letter names"),
        (6, "", "needs a source"),
        (7, "", "needs a note"),
    ],
)
def test_a_malformed_row_is_rejected(
    tmp_path: Path, field: int, value: str, complaint: str
) -> None:
    row = list(GOOD)
    row[field] = value
    with pytest.raises(ValueError, match=complaint):
        load_added_words(added_file(tmp_path, [row]))


def test_two_rows_for_one_word_and_tag_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="duplicate row"):
        load_added_words(added_file(tmp_path, [GOOD, GOOD]))


def test_the_same_word_under_two_tags_is_allowed(tmp_path: Path) -> None:
    second = list(GOOD)
    second[1] = "AJ0"
    assert len(load_added_words(added_file(tmp_path, [GOOD, second]))) == 2


def test_an_added_row_wears_no_variant_tag(tmp_path: Path) -> None:
    """An added row belongs to no accent, so its `var` tag is empty. `variants.kept` raises on an empty tag. An added row that reached the row policy would therefore raise an error instead of being counted in the per-tag row counts in var-tags.tsv."""
    entry = load_added_words(added_file(tmp_path, [GOOD]))[0]
    assert entry.row.var == ""
    assert entry.row.headword == "quikscript_NP0_𐑒𐑢𐑦𐑒𐑕𐑒𐑮𐑦𐑐𐑑"
