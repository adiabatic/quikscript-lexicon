"""The shipped tables and the corpus, loaded once for the whole session.

Every module that spells a word wants the same tables and the same rows, and holding
them per module read readlex.json once per module.
"""

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

MAPPING = load_mapping()
QUIRKS = load_quirks()
OVERRIDES = load_overrides(MAPPING)
TABLES = load_tables()
CORPUS = load_rows()
KEPT = select(load_var_tags(), CORPUS)


def context_of(word: str, row: Row) -> Context:
    ipa, _ = normalize(row.ipa, QUIRKS)
    return Context(word, row.pos, ipa, tuple(tokenize(ipa, MAPPING, OVERRIDES)))
