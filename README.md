# Quikscript lexicon

[https://github.com/Shavian-info/readlex](Shavian-info/readlex), but for Quikscript.

## Layout

- `data/ipa-to-qs.tsv` — the canonical IPA → Quikscript segment mapping (spec: [`docs/ipa-to-qs.md`](docs/ipa-to-qs.md))
- `data/ipa-quirks.tsv` — pre-tokenization fixes for upstream ReadLex quirks
- `src/qslex/` — mapping loader, tokenizer, and exhaustive validator (`uv run python -m qslex.validate tmp/readlex/kingsleyreadlexicon.tsv`)
