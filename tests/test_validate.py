from qslex import load_mapping, load_overrides
from qslex.readlex import (
    CORPUS_HEADWORDS,
    CORPUS_ROWS,
    CORPUS_SHA256,
    default_corpus_path,
    digest,
    load_rows,
)
from qslex.tokenizer import tokenize
from qslex.validate import main, stressed_rhotic_ears

MAPPING = load_mapping()
OVERRIDES = load_overrides(MAPPING)


def test_vendored_corpus_matches_its_recorded_digest() -> None:
    assert digest(default_corpus_path()) == CORPUS_SHA256


def test_corpus_loads_expected_rows() -> None:
    rows = load_rows()
    assert len(rows) == CORPUS_ROWS
    assert len({row.headword for row in rows}) == CORPUS_HEADWORDS
    assert rows[0].word and rows[0].ipa


def test_stressed_rhotic_ears_counts_only_rhotic_stressed() -> None:
    cases = [
        ("dɪəR", 1),
        ("ˈhæpɪəR", 0),
        ("ˈθɪətəR", 0),
        ("ænˈtɪərɪəR", 1),
        ("ˈbeɪkəR", 0),
    ]
    for ipa, expected in cases:
        assert stressed_rhotic_ears(ipa, tokenize(ipa, MAPPING, OVERRIDES)) == expected


def test_validator_passes_on_the_vendored_corpus() -> None:
    assert main([]) == 0
