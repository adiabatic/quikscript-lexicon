from pathlib import Path

import pytest

from qslex import load_mapping, load_overrides
from qslex.readlex import (
    CORPUS_ROWS,
    CORPUS_SHA256,
    CorpusError,
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
    assert rows[0].word and rows[0].ipa


def test_missing_corpus_is_a_clear_error(tmp_path: Path) -> None:
    with pytest.raises(CorpusError, match="not found"):
        load_rows(tmp_path / "absent.tsv")


def test_tampered_corpus_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "corpus.tsv"
    path.write_text("a\tb\tc\td\te\n", encoding="utf-8")
    with pytest.raises(CorpusError, match="SHA-256"):
        load_rows(path)


def test_wrong_field_count_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "corpus.tsv"
    path.write_text("a\tb\tc\n", encoding="utf-8")
    with pytest.raises(CorpusError, match="expected 5 fields"):
        load_rows(path, verify=False)


def test_wrong_row_count_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "corpus.tsv"
    path.write_text("a\tb\tc\td\te\n", encoding="utf-8")
    with pytest.raises(CorpusError, match="expected 110056 rows"):
        load_rows(path, verify=False)


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
