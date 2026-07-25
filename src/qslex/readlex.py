from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

CORPUS_URL = "https://github.com/Shavian-info/readlex"
CORPUS_COMMIT = "8343343090385938bf8a901748117dce94d9e570"
CORPUS_SHA256 = "6f71dc6179fc9c579930a38693e445cb5fd491771fde7bcecf310e2352126038"
CORPUS_ROWS = 110056
FIELDS = 5


@dataclass(frozen=True)
class Row:
    word: str
    shavian: str
    pos: str
    ipa: str
    frequency: str


class CorpusError(RuntimeError):
    pass


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_corpus_path() -> Path:
    return repo_root() / "data" / "readlex" / "kingsleyreadlexicon.tsv"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_rows(path: Path | None = None, verify: bool = True) -> tuple[Row, ...]:
    path = path if path is not None else default_corpus_path()
    if not path.is_file():
        raise CorpusError(
            f"ReadLex corpus not found at {path}. It is vendored at "
            f"data/readlex/kingsleyreadlexicon.tsv in a source checkout; pass an "
            f"explicit path when running from an installed package."
        )
    if verify:
        actual = digest(path)
        if actual != CORPUS_SHA256:
            raise CorpusError(
                f"{path} has SHA-256 {actual}, expected {CORPUS_SHA256} "
                f"({CORPUS_URL} @ {CORPUS_COMMIT[:7]}). Every corpus invariant in "
                f"validate.py is pinned to that snapshot; bump both together."
            )

    rows: list[Row] = []
    with path.open(encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            fields = line.rstrip("\n").split("\t")
            if len(fields) != FIELDS:
                raise CorpusError(
                    f"{path}:{lineno}: expected {FIELDS} fields, got {len(fields)}"
                )
            rows.append(Row(*fields))
    if len(rows) != CORPUS_ROWS:
        raise CorpusError(f"{path}: expected {CORPUS_ROWS} rows, got {len(rows)}")
    return tuple(rows)
