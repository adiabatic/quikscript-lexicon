# Quikscript lexicon

[Shavian-info/readlex](https://github.com/Shavian-info/readlex), but for Quikscript.

A spelling dictionary of 108,425 rows under 56,649 headwords, generated from the Read Lexicon by pivoting on its IPA column and applying Kingsley Read's own conventions — not by transliterating Shavian, which has already thrown away distinctions Quikscript needs.

## The lexicon

Generated into [`lexicon/`](lexicon) and committed, so you can just use them without building anything:

- [`lexicon/quikscript-lexicon.json`](lexicon/quikscript-lexicon.json) — the master, grouped by headword
- [`lexicon/quikscript-lexicon.tsv`](lexicon/quikscript-lexicon.tsv) — the flat projection
- [`lexicon/qs_converter_phrases.txt`](lexicon/qs_converter_phrases.txt) — entries a tokenizer must match whole
- [`lexicon/letters.tsv`](lexicon/letters.tsv) — every Quikscript letter and its codepoint
- [`lexicon/en-Qaas.dic`](lexicon/en-Qaas.dic) and [`lexicon/en-Qaas.aff`](lexicon/en-Qaas.aff) — a Hunspell spelling dictionary; check Quikscript text with `hunspell -i utf-8 -d lexicon/en-Qaas`

Three spelling columns: **`qs`** is Senior, the default; **`qs_junior`** and **`qs_x`** (the ·Excite/·Exam ligature form) are populated only where they differ from it. [`lexicon/README.md`](lexicon/README.md) explains the columns; [`docs/pipeline.md`](docs/pipeline.md) specifies the build.

**The JSON is canonical.** Every other artifact is projected from it in a single reshape, never emitted alongside it — which is what makes upstream's duplicate-row bug ([readlex#124](https://github.com/Shavian-info/readlex/pull/124)) structurally impossible here, and what [`docs/pipeline.md`](docs/pipeline.md#artifacts) means by one master per layer.

It is also the **only** JSON, and it is self-contained: beside its entries it carries the letter table, the C5 → Penn tag map and the phrase list, so that one file regenerates every other. The four that stay are formats rather than restatements — a spreadsheet reads the TSV, hunspell reads the `.dic`. The transliterator's own Latin → spellings dictionary used to be a second 9 MB JSON here; it said nothing the master did not, so it is [rebuilt from the master](docs/pipeline.md#the-converter-shape) instead of shipped.

## Encoding

Quikscript is written in the Private Use Area, **U+E650–U+E67E**, one codepoint per letter, per the [quikscript.net CSUR proposal](https://www.quikscript.net/csur/). Without a Quikscript font every QS column renders as blank boxes; [`lexicon/letters.tsv`](lexicon/letters.tsv) names each codepoint so the text can be read without one.

Worth stating honestly: that range is the de-facto community assignment, but the live Evertype CSUR index still lists it as *unassigned*. The authority here is the proposal, not a registration.

Tag Quikscript text `en-Qaas`, per [quikscript.net/on-the-web](https://www.quikscript.net/on-the-web/).

## Layout

In the order a word passes through the pipeline:

- `data/readlex/` — the vendored ReadLex corpus that goes in, SHA-256 pinned ([provenance](data/readlex/README.md))
- `src/qslex/data/var-tags.tsv` — the row policy: which accent tags the lexicon spells and which it drops (spec: [`docs/pipeline.md`](docs/pipeline.md))
- `src/qslex/data/ipa-quirks.tsv` — pre-tokenization fixes for upstream ReadLex quirks
- `src/qslex/data/ipa-to-qs.tsv` — the canonical IPA → Quikscript segment mapping the tokenizer matches against (spec: [`docs/ipa-to-qs.md`](docs/ipa-to-qs.md))
- `src/qslex/data/ipa-overrides.tsv` — per-word stress overrides consulted while resolving a token, where the mechanical ɪə rule is wrong
- `src/qslex/data/shavian-divergences.tsv` — words where the Manual deliberately overrules ReadLex's Shavian column, so the validator expects that disagreement
- `src/qslex/elements.py` — where an entry's boundaries are: the one split into elements that both the rules and the word signs cut a hyphenated or multi-word entry at
- `src/qslex/rules.py` — Read's terminal, affix and prefix conventions applied on top of the segment mapping, word by word inside a compound, plus the ·Excite/·Exam ligature column (spec: [`docs/orthographic-rules.md`](docs/orthographic-rules.md))
- `src/qslex/data/manual-spellings.tsv` — every spelling the Manual writes out, and every example word it names, as the fixture the rules are held to
- `src/qslex/data/rule-words.tsv` — per-word rulings for the five rules whose trigger the data cannot settle by itself
- `src/qslex/data/x-ligatures.tsv` — the words where the Latin `x` cannot be aligned to a letter pair mechanically
- `src/qslex/words.py` — the lexical layer that runs last: the Manual's word signs, standard word-outlines and abbreviations, and the junior column (spec: [`docs/word-signs.md`](docs/word-signs.md))
- `src/qslex/data/word-signs.tsv` — the core eight, the three abbreviations, and every standard word-outline, with the junior form where it diverges
- `src/qslex/data/contractions.tsv` — the Manual's §III Senior contractions, plus the one the terminal -ing section prints and that list omits, shipped for the transliterator and applied to no column
- `src/qslex/build.py` — the build that writes `lexicon/`, and prints what it touched: rows converted and skipped, and how many rows carry each sparse column
- `src/qslex/data/manual-passages.tsv` — the Manual's eleven specimen passages, word by word, as the fixture the finished spellings are held to (spec: [`docs/validation.md`](docs/validation.md))
- `src/qslex/roundtrip.py` — the reverse of the segment mapping, which reads every shipped spelling back to a phoneme string and lays it beside the IPA it came from
- `src/qslex/lint.py` — the Manual's own lint, every check gated on the Orthodox trigger its rule keys on, with `src/qslex/data/lint-pragmas.tsv` declaring every word allowed to break one and why
- `src/qslex/latin2qs.py` — the consumer at the end: ReadLex's `latin2shaw.py` ported to emit Quikscript from running Latin text (spec: [`docs/latin2qs.md`](docs/latin2qs.md))
- `src/qslex/` — the loaders, tokenizer, and exhaustive validator that run all of the above

The mapping tables live inside the package so they are importable from an installed wheel; the corpus lives outside it, because a consumer transcribing IPA does not need 27 MB of ReadLex.

## Transliterating

```sh
uv run python -m qslex.latin2qs < input.txt                    # Senior
uv run python -m qslex.latin2qs --mode x --contractions in.txt # ligatures + §III contractions
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
