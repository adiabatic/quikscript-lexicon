import dataclasses
import html
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from qslex.build import HUNSPELL_AFF, HUNSPELL_DIC
from qslex.hunspell import LIGATURES, by_frequency
from qslex.letters import parse, render_qs
from qslex.playground import (
    CORE,
    MARKED_JS,
    PAGE,
    PLACEHOLDER,
    SAMPLE_WORDS,
    SHA256,
    SITE,
    WEB,
    PageError,
    artifact,
    asset,
    build,
    contracted,
    crosscheck,
    load_records,
    main,
    payload,
    replacements,
    sample,
    substitute,
    word_list,
)
from qslex.readlex import repo_root
from qslex.words import Contraction, load_contractions

ROOT = repo_root()
RECORDS = load_records(ROOT)
BUILT, COVERAGE = build()
LEXICON = COVERAGE.lexicon

CONTRACTIONS = load_contractions()
MATCHED = contracted(CONTRACTIONS, RECORDS)
CONTRACTED = frozenset(written for written, _ in MATCHED)

DIVERGENT = tuple(row for row in RECORDS if row.junior)
SAMPLE = sample(RECORDS, LEXICON)
QUIKSCRIPT = SAMPLE.splitlines()[-1].split(" ")

NODE = shutil.which("node")
HERE = Path(__file__).resolve().parent
CORE_TESTS, CORE_CHECKS = "playground_core.js", 26
PAGE_TESTS, PAGE_CHECKS = "playground_page.js", 23


def directive(name: str, keyword: str) -> str:
    lines = artifact(name, ROOT).splitlines()
    return next(line for line in lines if line.startswith(keyword + " ")).split(" ", 1)[
        1
    ]


def test_building_the_page_twice_is_byte_identical() -> None:
    again, _ = build()
    assert again.encode("utf-8") == BUILT.encode("utf-8")


def test_the_word_set_is_the_dictionary_the_lexicon_ships() -> None:
    counted, *listed = artifact(HUNSPELL_DIC, ROOT).splitlines()
    assert counted == str(len(LEXICON.listed))
    assert tuple(listed) == LEXICON.listed


def test_the_letter_order_is_the_affix_files_try_order() -> None:
    assert directive(HUNSPELL_AFF, "TRY") == by_frequency(LEXICON.listed)
    assert json.loads(payload(LEXICON))["try_order"] == by_frequency(LEXICON.listed)


def test_the_replacement_table_is_the_affix_files_own() -> None:
    written = [
        line.split(" ")[1:]
        for line in artifact(HUNSPELL_AFF, ROOT).splitlines()
        if line.startswith("REP ") and line.count(" ") == 2
    ]
    assert [list(pair) for pair in replacements()] == written
    assert len(replacements()) == 2 * len(LIGATURES)


def test_both_forms_of_a_divergent_row_are_accepted() -> None:
    """The toggle swaps the face alone, so neither grade narrows the word set."""
    accepted = frozenset(LEXICON.union)
    assert {row.latin for row in DIVERGENT} == {
        "always",
        "that",
        "was",
        "wasn't",
        "'twas",
    }
    for row in DIVERGENT:
        assert row.qs in accepted
        assert row.junior in accepted


def test_the_page_carries_the_dictionary_and_the_senior_contractions() -> None:
    assert LEXICON.union == tuple(sorted(frozenset(LEXICON.listed) | CONTRACTED))
    assert len(LEXICON.listed) == 75568
    assert len(CONTRACTED) == 74
    assert len(LEXICON.union) == 75636


def test_the_contractions_the_dictionary_already_lists_widen_nothing() -> None:
    """Six of the 74 are spellings the columns carry anyway, for six reasons.

    be and that are Manual word signs the senior column already writes, cannot is
    spelt as the list spells it, and do, think and she collide with an unrelated
    entry each — the ordinals nd/rd and th, and the interjection sh. Set arithmetic
    gets all six right; a count of rows would not.
    """
    assert len(CONTRACTED & frozenset(LEXICON.listed)) == 6
    assert len(LEXICON.union) - len(LEXICON.listed) == 68


def test_only_the_word_rows_of_the_contraction_list_reach_the_page() -> None:
    clitics = [entry for entry in CONTRACTIONS if entry.kind == "clitic"]
    assert {entry.word for entry in clitics} == {"'ll", "n't"}
    assert {
        render_qs(parse(entry.contraction))
        for entry in CONTRACTIONS
        if entry.kind == "word"
    } == CONTRACTED
    for entry in clitics:
        assert render_qs(parse(entry.contraction)) not in frozenset(LEXICON.union)


def test_a_contraction_takes_the_frequency_of_the_word_it_writes() -> None:
    for written, row in MATCHED:
        assert LEXICON.frequency[written] >= row.frequency


def test_a_contraction_matching_no_lexicon_row_is_refused() -> None:
    stray = Contraction("qwertyuiop", "", "word", "·Key", "senior-contractions", "")
    with pytest.raises(PageError, match="matches no row"):
        contracted((stray,), RECORDS)


def test_a_contraction_tagged_for_a_part_of_speech_matches_only_that_tag() -> None:
    tagged = [entry for entry in CONTRACTIONS if entry.pos]
    assert {entry.word for entry in tagged} == {"that"}
    for entry in tagged:
        for _, row in contracted((entry,), RECORDS):
            assert (row.latin.lower(), row.pos) == (entry.word, entry.pos)


def test_every_spelling_carries_a_frequency() -> None:
    assert set(LEXICON.frequency) == set(LEXICON.union)


def test_a_sparse_column_inherits_the_frequency_of_the_row_that_writes_it() -> None:
    for row in RECORDS:
        for word in (row.qs, row.junior, row.ligature):
            if word and " " not in word:
                assert LEXICON.frequency[word] >= row.frequency


def test_the_word_list_writes_a_frequency_only_where_there_is_one() -> None:
    lines = word_list(LEXICON).split("\n")
    assert len(lines) == len(LEXICON.union)
    for line, word in zip(lines, LEXICON.union, strict=True):
        spelling, _, frequency = line.partition("\t")
        assert spelling == word
        counted = LEXICON.frequency[word]
        assert frequency == (str(counted) if counted else "")


def test_a_word_set_the_dictionary_does_not_list_is_refused() -> None:
    doctored = dataclasses.replace(LEXICON, listed=LEXICON.listed[:-1])
    with pytest.raises(PageError, match="make artifacts"):
        crosscheck(doctored, ROOT)


def test_every_pinned_asset_verifies() -> None:
    assert len(SHA256) == 6
    for name in SHA256:
        assert asset(name, ROOT)


def test_a_tampered_asset_is_refused(tmp_path: Path) -> None:
    for name in SHA256:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        flipped = bytearray(asset(name, ROOT))
        flipped[0] ^= 0xFF
        target.write_bytes(bytes(flipped))
        with pytest.raises(PageError, match="SHA-256"):
            asset(name, tmp_path)


def test_a_missing_asset_is_refused(tmp_path: Path) -> None:
    with pytest.raises(PageError, match="not found"):
        asset(MARKED_JS, tmp_path)


def test_a_chunk_that_could_close_its_own_script_is_refused() -> None:
    with pytest.raises(PageError, match="truncate"):
        substitute("__QS_APP__", {"__QS_APP__": "if (a </SCRIPT> b) {}"})


def test_a_chunk_with_no_placeholder_to_fill_is_refused() -> None:
    with pytest.raises(PageError, match="not in the template"):
        substitute("nothing to fill", {"__QS_APP__": ""})


def test_a_placeholder_nothing_fills_is_refused() -> None:
    with pytest.raises(PageError, match="nothing filled"):
        substitute("__QS_APP__ __QS_CORE__", {"__QS_APP__": ""})


def test_the_sample_spells_every_word_the_way_the_lexicon_does() -> None:
    spelt = {(row.latin.lower(), row.pos): row.qs for row in RECORDS}
    assert QUIKSCRIPT[: len(SAMPLE_WORDS)] == [spelt[key] for key in SAMPLE_WORDS]


def test_the_sample_carries_exactly_one_word_the_lexicon_does_not() -> None:
    accepted = frozenset(LEXICON.union)
    assert len(QUIKSCRIPT) == len(SAMPLE_WORDS) + 1
    assert [word for word in QUIKSCRIPT if word not in accepted] == [QUIKSCRIPT[-1]]


def test_the_sample_opens_the_textarea() -> None:
    assert f">{html.escape(SAMPLE)}</textarea>" in BUILT


def test_the_page_is_a_whole_document_with_nothing_left_to_fill() -> None:
    assert BUILT.startswith("<!doctype html>")
    assert BUILT.endswith("</html>\n")
    assert PLACEHOLDER.findall(BUILT) == []


def test_the_page_inlines_all_five_faces() -> None:
    assert BUILT.count("data:font/woff2;base64,") == 5


def test_no_injected_chunk_closes_a_script_element_early() -> None:
    assert BUILT.count("<script>") == BUILT.lower().count("</script") == 4


def test_the_page_carries_its_data_as_one_json_object() -> None:
    written = payload(LEXICON)
    assert written in BUILT
    assert sorted(json.loads(written)) == ["rep", "try_order", "words"]


def test_check_reports_a_page_that_is_not_there(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["--out", str(tmp_path / PAGE), "--check"]) == 1
    assert "is missing" in capsys.readouterr().out


def test_the_page_it_writes_passes_its_own_check(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / PAGE
    assert main(["--out", str(out)]) == 0
    assert out.read_text(encoding="utf-8") == BUILT
    assert main(["--out", str(out), "--check"]) == 0
    assert "OK: 1 artifact matches a fresh build" in capsys.readouterr().out


def test_check_fails_on_a_page_that_has_been_edited(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / PAGE
    out.write_text(BUILT.replace("<title>", "<title>edited "), encoding="utf-8")
    assert main(["--out", str(out), "--check"]) == 1
    assert "differs from a fresh build" in capsys.readouterr().out


@pytest.fixture(scope="module")
def written(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """This module's own build, on disk where node can read it.

    A fresh build rather than the committed `site/index.html`, so that the page's
    JavaScript is held to what the builder emits now: whether what is committed
    matches that is `--check`'s question, and the tests above already ask it. It also
    keeps a test run from depending on `make site` having been run, or from leaving
    anything behind in the tree.
    """
    out = tmp_path_factory.mktemp(SITE) / PAGE
    out.write_text(BUILT, encoding="utf-8", newline="\n")
    return out


def under_node(script: str, *arguments: Path) -> str:
    """A JavaScript test file run to the end, with everything it said on failure.

    node exits non-zero on the first failed assertion and each file logs the checks
    that had passed before it, so the report pytest prints is the same one the file
    prints when it is run by hand.
    """
    assert NODE is not None
    finished = subprocess.run(
        [NODE, str(HERE / script), *(str(argument) for argument in arguments)],
        capture_output=True,
        text=True,
        check=False,
    )
    if finished.returncode:
        pytest.fail(
            f"{script} exited {finished.returncode}\n{finished.stdout}{finished.stderr}"
        )
    return finished.stdout


@pytest.mark.skipif(NODE is None, reason="node is not on PATH")
def test_the_pages_logic_holds_against_the_lexicon_it_carries(written: Path) -> None:
    logged = under_node(CORE_TESTS, WEB / CORE, written)
    assert logged.splitlines()[-1] == f"{CORE_CHECKS} checks passed", logged


@pytest.mark.skipif(NODE is None, reason="node is not on PATH")
def test_the_pages_four_scripts_run_together_over_a_shimmed_dom(written: Path) -> None:
    logged = under_node(PAGE_TESTS, written)
    assert logged.splitlines()[-1] == f"{PAGE_CHECKS} checks passed", logged
