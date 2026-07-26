# Quikscript lexicon

[Shavian-info/readlex](https://github.com/Shavian-info/readlex), but for Quikscript.

A spelling dictionary of 108,425 rows under 56,649 headwords, generated from the Read Lexicon by pivoting on its IPA column and applying Kingsley Read's own conventions — not by transliterating Shavian, which has already thrown away distinctions Quikscript needs.

## The lexicon

Generated into [`lexicon/`](lexicon) and committed, so it can be used without running the build:

- [`lexicon/quikscript-lexicon.json`](lexicon/quikscript-lexicon.json) — the master, grouped by headword
- [`lexicon/quikscript-lexicon.tsv`](lexicon/quikscript-lexicon.tsv) — the flat projection, 108,375 rows
- [`lexicon/qs_converter.json`](lexicon/qs_converter.json) — Latin → spellings by part of speech, for a transliterator
- [`lexicon/qs_converter_phrases.txt`](lexicon/qs_converter_phrases.txt) — entries a tokenizer must match whole
- [`lexicon/letters.tsv`](lexicon/letters.tsv) — every Quikscript letter and its codepoint

Three spelling columns: **`qs`** is Senior, the default; **`qs_junior`** and **`qs_x`** (the ·Excite/·Exam ligature form) are populated only where they differ from it. [`lexicon/README.md`](lexicon/README.md) explains the columns; [`docs/pipeline.md`](docs/pipeline.md) specifies the build.

**The JSON is canonical.** Every other artifact is projected from it in a single reshape, never emitted alongside it — which is what makes upstream's duplicate-row bug ([readlex#124](https://github.com/Shavian-info/readlex/pull/124)) structurally impossible here. There is exactly one master per layer: `readlex.json` upstream, the rule and override tables in `src/qslex/data/`, `quikscript-lexicon.json` out. Nothing downstream of the build is hand-edited.

Only **rhotic RP** is spelt. ReadLex's TrapBath, General American and General Australian rows are dropped; its two RRP-variant tags are kept and normalised. See [Row policy](docs/pipeline.md#row-policy-the-rrp-family-only).

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
- `src/qslex/data/rule-words.tsv` — per-word rulings for the four rules whose trigger the data cannot settle by itself
- `src/qslex/data/x-ligatures.tsv` — the words where the Latin `x` cannot be aligned to a letter pair mechanically
- `src/qslex/words.py` — the lexical layer that runs last: the Manual's word signs, standard word-outlines and abbreviations, and the junior column (spec: [`docs/word-signs.md`](docs/word-signs.md))
- `src/qslex/data/word-signs.tsv` — the core eight, the three abbreviations, and every standard word-outline, with the junior form where it diverges
- `src/qslex/data/contractions.tsv` — the Manual's ~50 Senior contractions, shipped for the transliterator and applied to no column
- `src/qslex/build.py` — the build that writes `lexicon/`, and prints what it touched: rows converted and skipped, and what each rule and sign rewrote
- `src/qslex/data/manual-passages.tsv` — the Manual's eleven specimen passages, word by word, as the fixture the finished spellings are held to (spec: [`docs/validation.md`](docs/validation.md))
- `src/qslex/roundtrip.py` — the reverse of the segment mapping, which reads every shipped spelling back to a phoneme string and lays it beside the IPA it came from
- `src/qslex/lint.py` — the Manual's own lint, re-derived rule by rule from hunspell-dict-qs's hand-written checks, with `src/qslex/data/lint-pragmas.tsv` declaring every word allowed to break one and why
- `src/qslex/latin2qs.py` — the consumer at the end: ReadLex's `latin2shaw.py` ported to emit Quikscript from running Latin text (spec: [`docs/latin2qs.md`](docs/latin2qs.md))
- `src/qslex/` — the loaders, tokenizer, and exhaustive validator that run all of the above

The mapping tables live inside the package so they are importable from an installed wheel; the corpus lives outside it, because a consumer transcribing IPA does not need 27 MB of ReadLex.

## Transliterating

```sh
uv run python -m qslex.latin2qs < input.txt                    # Senior
uv run python -m qslex.latin2qs --mode x --contractions in.txt # ligatures + §III contractions
```

spaCy tokenizes and tags, `lexicon/qs_converter.json` supplies the spellings, the part of speech settles the heteronyms, and the Manual's conventions govern namer dots, apostrophes and punctuation. Words the lexicon lacks are constructed from affixes and flagged ⚠️, or passed through flagged ✢. The spec, the output modes and every deliberate departure from upstream's `latin2shaw.py` are in [`docs/latin2qs.md`](docs/latin2qs.md).

## Regenerating

```sh
make artifacts     # rewrite lexicon/
make check         # lint, types, tests, validator, and artifact freshness
```

`make check` ends by rebuilding every artifact in memory and failing if what is on disk differs, so a stale `lexicon/` cannot be committed. That, plus a clean `git diff` after `make artifacts`, is the byte-identical-regeneration proof.

## Proofs

```sh
uv run pytest
uv run python -m qslex.validate
uv run ruff check . && uv run ruff format --check . && uv run mypy
```

The validator verifies the corpus SHA-256 first, so a corpus bump is always a deliberate, reviewable change. It then makes one pass over all 111,214 corpus rows and holds two row sets to account.

Over **every** row — including the variants the lexicon does not spell, because the mapping still has to be right about them — it fails on any unmapped residue, any mapping row or quirk rule that stops firing, any quirk rule that touches a word it does not declare, any ɪə decision that contradicts the Shavian column without a recorded authority, any accent tag with no row policy or whose row count has drifted, and any drift in the pinned corpus invariants.

Over the **108,425 rows the lexicon spells**, it applies Read's orthographic rules and fails on any spelling the Manual writes out that the rules no longer reproduce, any rule whose rewrite count has drifted, any ruling that has gone stale, and any word left undecided. It then substitutes the word signs and fails on any sign row the corpus never reaches, any word whose rewrite count is unpinned or has drifted, any core-eight row spelt out in full, and any junior spelling that is not simply the spelling with the override left unapplied.

It then holds the finished spellings to three further checks, specified in [`docs/validation.md`](docs/validation.md): the Manual's specimen passages word by word, all 674 of them; a round trip that reads every spelling back to a phoneme string and fails unless every difference from its own IPA is one the mapping and the conventions license; and the Manual's own lint, re-derived rule by rule and run over every spelt row.

Why the corpus split, and what it costs, is in [`docs/pipeline.md`](docs/pipeline.md#where-the-validator-runs-and-why-it-splits).

## License

MIT — see [`LICENSE.md`](LICENSE.md). The vendored corpus under `data/readlex/`, and everything under `lexicon/` derived from it, is separately licensed, also MIT, © 2024 Shavian-info.
