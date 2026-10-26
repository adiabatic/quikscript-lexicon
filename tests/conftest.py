"""The shipped tables, the corpus and the build artifacts, loaded once per test session.

Every test module that spells words uses the same tables and rows. Loading them here reads readlex.json once per session instead of once per module. The artifacts are here for the same reason: more than one module reads them, and spelling the corpus is the most expensive step in the suite.

The artifacts come from cached functions rather than module constants, so the corpus is spelled only if a test module calls one of them. The tables are loaded in every session, because pytest imports this file first.
"""

import functools

from qslex import (
    Context,
    Row,
    added_rows,
    load_added_words,
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
ADDED = load_added_words()


@functools.cache
def entries() -> tuple[Entry, ...]:
    """Every kept corpus row and added word, spelled on the first call and cached for the rest of the session."""
    return convert(KEPT + added_rows(ADDED), MAPPING)


@functools.cache
def built() -> dict[str, str]:
    """Every artifact, built from `entries()` on the first call and cached."""
    return artifacts(entries(), MAPPING, len(ADDED))


def context_of(word: str, row: Row) -> Context:
    ipa, _ = normalize(row.ipa, QUIRKS)
    return Context(word, row.pos, ipa, tuple(tokenize(ipa, MAPPING, OVERRIDES)))
