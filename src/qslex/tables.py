from __future__ import annotations

import csv
import io
from collections.abc import Iterator
from contextlib import contextmanager
from importlib import resources
from pathlib import Path
from typing import IO

DATA_PACKAGE = "qslex.data"


@contextmanager
def open_data(path: Path | None, name: str) -> Iterator[tuple[IO[str], str]]:
    if path is not None:
        with path.open(encoding="utf-8", newline="") as f:
            yield f, str(path)
        return
    resource = resources.files(DATA_PACKAGE) / name
    with io.StringIO(resource.read_text(encoding="utf-8"), newline="") as f:
        yield f, f"{DATA_PACKAGE}/{name}"


def rows_of(
    path: Path | None, name: str, header: list[str]
) -> Iterator[tuple[int, str, list[str]]]:
    """Every data row of one of this project’s TSV tables, in file order.

    A row comes with the line number and the source name its loader needs to say where a bad row is, so that every table reports a defect the same way.
    """
    with open_data(path, name) as (f, source):
        reader = csv.reader(f, delimiter="\t")
        found = next(reader)
        if found != header:
            raise ValueError(f"unexpected header in {source}: {found}")
        for lineno, row in enumerate(reader, start=2):
            if len(row) != len(header):
                raise ValueError(
                    f"{source}:{lineno}: expected {len(header)} fields, got {len(row)}"
                )
            yield lineno, source, row


class Declares:
    """A table row that names the words its rule is allowed to touch."""

    words: str

    @property
    def declared_words(self) -> tuple[str, ...]:
        return tuple(w.strip() for w in self.words.split(",") if w.strip())
