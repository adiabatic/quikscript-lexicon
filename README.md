# Quikscript lexicon

[Shavian-info/readlex](https://github.com/Shavian-info/readlex), but for Quikscript.

## Layout

- `src/qslex/data/ipa-to-qs.tsv` — the canonical IPA → Quikscript segment mapping (spec: [`docs/ipa-to-qs.md`](docs/ipa-to-qs.md))
- `src/qslex/data/ipa-quirks.tsv` — pre-tokenization fixes for upstream ReadLex quirks
- `src/qslex/data/ipa-overrides.tsv` — per-word stress overrides where the mechanical ɪə rule is wrong
- `src/qslex/data/shavian-divergences.tsv` — words where the Manual deliberately overrules ReadLex's Shavian column
- `src/qslex/` — mapping loader, tokenizer, and exhaustive validator
- `data/readlex/` — the vendored ReadLex corpus the validator runs against ([provenance](data/readlex/README.md))

The mapping tables live inside the package so they are importable from an installed wheel; the corpus lives outside it, because a consumer transcribing IPA does not need 6 MB of ReadLex.

## Proofs

```
uv run pytest
uv run python -m qslex.validate
uv run ruff check . && uv run ruff format --check . && uv run mypy
```

The validator tokenizes every vendored IPA string and fails on any unmapped residue, any mapping row or quirk rule that stops firing, any quirk rule that touches a word it does not declare, any ɪə decision that contradicts the Shavian column without a recorded authority, and any drift in the pinned corpus invariants. It verifies the corpus SHA-256 first, so a corpus bump is always a deliberate, reviewable change.

## Licence

MIT — see [`LICENSE.md`](LICENSE.md). The vendored corpus under `data/readlex/` is separately licensed, also MIT, © 2024 Shavian-info.
