# Layout

In the order a word passes through the pipeline:

- `data/readlex/` — the vendored ReadLex corpus that goes in, SHA-256 pinned ([provenance](data/readlex/README.md))
- `src/qslex/data/var-tags.tsv` — the row policy: which accent tags the lexicon spells and which it drops (spec: [`docs/pipeline.md`](docs/pipeline.md))
- `src/qslex/data/ipa-quirks.tsv` — pre-tokenization fixes for upstream ReadLex quirks
- `src/qslex/csur.py` — the alphabet everything downstream is written in: each letter’s name and PUA codepoint, which the mapping loader self-verifies against and the shipped `letters` table is derived from (spec: [`docs/conformance.md`](docs/conformance.md))
- `src/qslex/data/ipa-to-qs.tsv` — the canonical IPA → Quikscript segment mapping the tokenizer matches against (spec: [`docs/ipa-to-qs.md`](docs/ipa-to-qs.md))
- `src/qslex/data/ipa-overrides.tsv` — per-word stress overrides consulted while resolving a token, where the mechanical ɪə rule is wrong
- `src/qslex/data/shavian-divergences.tsv` — words where the Manual deliberately overrules ReadLex’s Shavian column, so the validator expects that disagreement
- `src/qslex/elements.py` — where an entry’s boundaries are: the one split into elements that both the rules and the word signs cut a hyphenated or multi-word entry at
- `src/qslex/rules.py` — Read’s terminal, affix and prefix conventions applied on top of the segment mapping, word by word inside a compound, plus the ·Excite/·Exam X-letter column and the senior-only n't elision the junior column declines (spec: [`docs/orthographic-rules.md`](docs/orthographic-rules.md))
- `src/qslex/data/manual-spellings.tsv` — every spelling the Manual writes out, and every example word it names, as the fixture the rules are held to
- `src/qslex/data/rule-words.tsv` — per-word rulings for the five rules whose trigger the data cannot settle by itself
- `src/qslex/data/x-rulings.tsv` — the words where the Latin `x` cannot be aligned to a letter pair mechanically
- `src/qslex/words.py` — the lexical layer that runs last: the Manual’s word signs, standard word-outlines and abbreviations, and the junior forms where they diverge (spec: [`docs/word-signs.md`](docs/word-signs.md))
- `src/qslex/data/word-signs.tsv` — the core eight, the three abbreviations, and every standard word-outline, with the junior form where it diverges
- `src/qslex/data/contractions.tsv` — the Manual’s §III Senior contractions, plus the one the terminal -ing section prints and that list omits, shipped for the transliterator and applied to no column
- `src/qslex/added.py` and `src/qslex/data/added-words.tsv` — the words the corpus has not got, the alphabet’s own name among them: entries in a corpus row’s shape, appended after the row policy and spelled by the same rules, each declaring the spelling those rules must give it (spec: [`docs/pipeline.md`](docs/pipeline.md#words-the-corpus-lacks))
- `src/qslex/build.py` — the build that writes `lexicon/`, and prints what it touched: rows converted, skipped and added, and how many rows carry each sparse column
- `src/qslex/data/manual-passages.tsv` — the Manual’s eleven specimen passages, word by word, as the fixture the finished spellings are held to (spec: [`docs/validation.md`](docs/validation.md))
- `src/qslex/roundtrip.py` — the reverse of the segment mapping, which reads every shipped spelling back to a phoneme string and lays it beside the IPA it came from
- `src/qslex/lint.py` — the Manual’s own lint, every check gated on the Orthodox trigger its rule keys on, with `src/qslex/data/lint-pragmas.tsv` declaring every word allowed to break one and why
- `src/qslex/latin2qs.py` — the consumer at the end: ReadLex’s `latin2shaw.py` ported to emit Quikscript from running Latin text (spec: [`docs/latin2qs.md`](docs/latin2qs.md))
- `src/qslex/projection.py` — the derivation every spelling checker shares: the union word set with its frequencies, the suggestion tables, and the crosschecks that hold them to the shipped hunspell artifacts
- `src/qslex/desk.py` — the Quikscript Desk page: the projection inlined into one self-contained `site/index.html` beside the vendored fonts and Markdown parser it renders with
- `src/qslex/payload.py` — the same projection written to `editor/server/payload.json` for the `quikscript-lsp` language server: generated, committed, and byte-compared by `make check` like every artifact
- `editor/` — the editor integrations in progress: `server/` holds the language server’s committed payload, the editor work’s one committed build product; server bundles and the VS Code `.vsix` are built on demand instead
- `src/qslex/` — the loaders, tokenizer, and exhaustive validator that run all of the above

The mapping tables live inside the package so they are importable from an installed wheel; the corpus lives outside it, because a consumer transcribing IPA does not need 27 MB of ReadLex.
