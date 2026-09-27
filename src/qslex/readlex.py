from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CORPUS_URL = "https://github.com/Shavian-info/readlex"
CORPUS_COMMIT = "8343343090385938bf8a901748117dce94d9e570"
CORPUS_SHA256 = "0e026ee523fe7beea0a34186e17043d6443e8bbe06a699ed175ad2cf31c332e9"
CORPUS_HEADWORDS = 56649
CORPUS_ROWS = 111214
FIELDS = ("Latn", "Shaw", "pos", "ipa", "freq", "var")


@dataclass(frozen=True)
class Row:
    headword: str
    word: str
    shavian: str
    pos: str
    ipa: str
    frequency: int
    var: str


class CorpusError(RuntimeError):
    pass


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_corpus_path() -> Path:
    return repo_root() / "data" / "readlex" / "readlex.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _entry(source: str, headword: str, index: int, entry: Any) -> Row:
    where = f"{source}: {headword}[{index}]"
    if not isinstance(entry, dict):
        raise CorpusError(f"{where}: expected an object, got {type(entry).__name__}")
    missing = [field for field in FIELDS if field not in entry]
    if missing:
        raise CorpusError(f"{where}: missing {missing}")
    extra = sorted(set(entry) - set(FIELDS))
    if extra:
        raise CorpusError(f"{where}: unexpected fields {extra}")
    frequency = entry["freq"]
    if not isinstance(frequency, int):
        raise CorpusError(f"{where}: freq is not a number: {frequency!r}")
    return Row(
        headword=headword,
        word=entry["Latn"],
        shavian=entry["Shaw"],
        pos=entry["pos"],
        ipa=entry["ipa"],
        frequency=frequency,
        var=entry["var"],
    )


def load_rows(path: Path | None = None, verify: bool = True) -> tuple[Row, ...]:
    """Every entry of readlex.json, flattened in file order.

    readlex.json is the file upstream edits by hand. Upstream’s flat TSV is generated from it and has had generation bugs, and the `var` tags the row policy needs are only in the JSON. Each row keeps its headword, so the build can regroup the rows without a second pass over the file.
    """
    path = path if path is not None else default_corpus_path()
    if not path.is_file():
        raise CorpusError(
            f"ReadLex corpus not found at {path}. It is vendored at "
            f"data/readlex/readlex.json in a source checkout; pass an explicit path "
            f"when running from an installed package."
        )
    if verify:
        actual = digest(path)
        if actual != CORPUS_SHA256:
            raise CorpusError(
                f"{path} has SHA-256 {actual}, expected {CORPUS_SHA256} "
                f"({CORPUS_URL} @ {CORPUS_COMMIT[:7]}). Every corpus invariant in "
                f"validate.py is pinned to that snapshot; bump both together."
            )

    source = str(path)
    try:
        corpus = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise CorpusError(f"{source}: {error}") from error
    if not isinstance(corpus, dict):
        raise CorpusError(f"{source}: expected an object of headwords")

    rows: list[Row] = []
    for headword, entries in corpus.items():
        if not isinstance(entries, list) or not entries:
            raise CorpusError(f"{source}: {headword} is not a non-empty list")
        for index, entry in enumerate(entries):
            rows.append(_entry(source, headword, index, entry))
    if len(corpus) != CORPUS_HEADWORDS:
        raise CorpusError(
            f"{source}: expected {CORPUS_HEADWORDS} headwords, got {len(corpus)}"
        )
    if len(rows) != CORPUS_ROWS:
        raise CorpusError(f"{source}: expected {CORPUS_ROWS} rows, got {len(rows)}")
    return tuple(rows)
