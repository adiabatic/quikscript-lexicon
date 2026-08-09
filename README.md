# Quikscript lexicon

[Shavian-info/readlex](https://github.com/Shavian-info/readlex), but for Quikscript.

## The lexicon

Generated into [`lexicon/`](lexicon) and committed, so you can just use them without building anything:

- [`lexicon/quikscript-lexicon.json`](lexicon/quikscript-lexicon.json) — the master, grouped by headword

And then there are more things generated from it:

- [`lexicon/quikscript-lexicon.tsv`](lexicon/quikscript-lexicon.tsv) — the flat projection
- [`lexicon/qs_converter_phrases.txt`](lexicon/qs_converter_phrases.txt) — entries a tokenizer must match whole
- [`lexicon/en-Qaas.dic`](lexicon/en-Qaas.dic) and [`lexicon/en-Qaas.aff`](lexicon/en-Qaas.aff) — a Hunspell spelling dictionary; check Quikscript text with `hunspell -i utf-8 -d lexicon/en-Qaas`

Three spelling columns: **`qs`** is Senior, the default; **`qs_junior`** and **`qs_x`** (the ·Excite/·Exam X-letter form) are populated only where they differ from it. [`lexicon/README.md`](lexicon/README.md) explains the columns; [`docs/pipeline.md`](docs/pipeline.md) specifies the build.

## Encoding

Quikscript is written in the Private Use Area, **U+E650–U+E67E**, one codepoint per letter, per the [quikscript.net CSUR proposal](https://www.quikscript.net/csur/). Without a Quikscript font every QS column renders as blank boxes; the `letters` table in [`lexicon/quikscript-lexicon.json`](lexicon/quikscript-lexicon.json) names each codepoint so the text can be read without one.

Tag Quikscript text `en-Qaas`, per [quikscript.net/on-the-web](https://www.quikscript.net/on-the-web/).

## Layout

What each file is, in the order a word passes through the pipeline, is in [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Transliterating

```sh
uv run python -m qslex.latin2qs < input.txt                    # Senior
uv run python -m qslex.latin2qs --mode x --contractions in.txt # X-letters + §III contractions
```

spaCy tokenizes and tags, the master supplies the spellings, the part of speech settles the heteronyms, and the Manual's conventions govern namer dots, apostrophes and punctuation. Words the lexicon lacks are constructed from affixes and flagged ⚠️, or passed through flagged ✢. The spec, the output modes and every deliberate departure from upstream's `latin2shaw.py` are in [`docs/latin2qs.md`](docs/latin2qs.md).

## Desk

[`site/index.html`](site/index.html) is the lexicon with a user interface on it: type Markdown in one pane, read it set in Quikscript in the other, and every Quikscript word the lexicon does not accept gets a dotted red underline you can click for suggestions that edit the source back, or to ignore that occurrence or the word from then on. A toggle button switches Junior/Senior, which swaps the face alone — the accepted set is always the whole lexicon plus the Manual's §III contractions, which no column carries.

```sh
make site          # rewrite site/index.html
```

Then open the file — there is nothing to install, no server to run and no request to anywhere, because the whole word list, [marked](https://github.com/markedjs/marked) and five [Abbots Morton Spaceport](https://github.com/adiabatic/abbots-morton-spaceport) faces (SIL OFL 1.1, © Nathan Galt) are inlined in it. Those faces are pixel fonts, so every font size the page sets is a multiple of 11px. The spec is [`docs/desk.md`](docs/desk.md).

## Regenerating

```sh
make artifacts     # rewrite lexicon/
```

What keeps a stale `lexicon/` from being committed, and what a corpus bump involves, are in [`docs/pipeline.md`](docs/pipeline.md#regenerating).

## Proofs

```sh
make check         # lint, types, tests, validator, and artifact freshness
```

The validator verifies the corpus SHA-256 first, so a corpus bump is always a deliberate, reviewable change; it then makes one pass over the corpus and holds two row sets to account — the segment mapping over every row upstream ships, the spellings over the rows the lexicon spells. What it demands of each layer is stated by that layer's own spec — [`docs/ipa-to-qs.md`](docs/ipa-to-qs.md), [Read's orthographic rules](docs/orthographic-rules.md#what-the-validator-checks), [the word signs](docs/word-signs.md#what-the-validator-checks), and [`docs/validation.md`](docs/validation.md) for the specimen passages, the round trip and the Manual's own lint — and why the pass splits at all, with what that costs, is in [`docs/pipeline.md`](docs/pipeline.md#where-the-validator-runs-and-why-it-splits).

## License

MIT — see [`LICENSE.md`](LICENSE.md). The vendored corpus under `data/readlex/`, and everything under `lexicon/` derived from it, is separately licensed, also MIT, © 2024 Shavian-info.
