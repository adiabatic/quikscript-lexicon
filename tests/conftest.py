"""The shipped tables, the corpus and the artifacts, built once for the whole session.

Every module that spells a word wants the same tables and the same rows, and holding them per module read readlex.json once per module. The artifacts are here for the same reason: more than one module reads them, and spelling the corpus twice is the most expensive thing the suite could do.

Spelling it even once is expensive enough to be worth deferring, so the artifacts are cached factories rather than constants. Every module pays for the tables on import; only the two that read the build pay to run it.
"""

import functools

from qslex import (
    Context,
    Row,
    load_mapping,
    load_overrides,
    load_quirks,
    load_rows,
    load_tables,
    load_var_tags,
    normalize,
    select,
    tokenize,
)
from qslex.build import Entry, artifacts, convert

MAPPING = load_mapping()
QUIRKS = load_quirks()
OVERRIDES = load_overrides(MAPPING)
TABLES = load_tables()
CORPUS = load_rows()
KEPT = select(load_var_tags(), CORPUS)


@functools.cache
def entries() -> tuple[Entry, ...]:
    """Every kept row spelt, built on first ask and held for the rest of the run."""
    return convert(KEPT, MAPPING)


@functools.cache
def built() -> dict[str, str]:
    """Every artifact, from the same spelt rows, likewise built once."""
    return artifacts(entries(), MAPPING)


def context_of(word: str, row: Row) -> Context:
    ipa, _ = normalize(row.ipa, QUIRKS)
    return Context(word, row.pos, ipa, tuple(tokenize(ipa, MAPPING, OVERRIDES)))
