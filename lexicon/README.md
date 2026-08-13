# The lexicon

Generated. Do not edit anything here by hand — `make artifacts` rewrites all of it, and `make check` fails if what is committed differs from a fresh build. The spec is [`docs/pipeline.md`](../docs/pipeline.md).

What the files are is the spec’s [Artifacts](../docs/pipeline.md#artifacts) table; the shape of each is under [Artifact shapes](../docs/pipeline.md#artifact-shapes). No document restates how many rows each carries: `meta.counts` in the master is the live figure for the counts it holds, and `make check` byte-compares every file against a fresh build for the rest.

`quikscript-lexicon.json` is the master, and the only JSON here. Five keys: `entries` is the lexicon itself, and `letters`, `c5_to_penn` and `phrases` are the small tables a projection needs, so that this one file regenerates every other — including the transliterator’s Latin → spellings dictionary, which is [rebuilt rather than shipped](../docs/pipeline.md#the-converter-shape). `meta` records the corpus commit it came from and the counts it holds. The other four files are here because they are formats this one is not: a spreadsheet reads the TSV, hunspell reads the `.dic`.

`en-Qaas.dic` and `en-Qaas.aff` are the pair a spell checker wants: `hunspell -i utf-8 -d lexicon/en-Qaas` checks Quikscript text against every unspaced spelling the three columns ship. The `-i` matters — without it hunspell reads the input in the locale’s encoding, and under a non-UTF-8 one it skips every Quikscript line without a word of complaint.

## Reading it

Quikscript is written in the Private Use Area, U+E650–U+E67E, one codepoint per letter — so without a Quikscript font every QS column renders as blank boxes. The master’s `letters` key names each codepoint; [`docs/conformance.md`](../docs/conformance.md) covers the encoding and how to tag the text.

Three spelling columns, and two of them are sparse:

- **`qs`** — Senior, the default: Read’s §III conventions plus the Manual’s standard word spellings.
- **`qs_junior`** — present only where the Junior spelling genuinely differs, which is a handful of rows: the word-level cases, and the n't words, whose linking vowel the senior column elides and the junior column keeps ([`docs/orthographic-rules.md`](../docs/orthographic-rules.md#decisions)). The Manual’s own affix conventions are how Quikscript is spelled in both grades, so no other rule-driven spelling diverges.
- **`qs_x`** — the ·Excite/·Exam X-letter form, built on `qs`, present only where it differs. Stored rather than derived, because the surrounding letters change too: expect is ·It·Key·See·Pea·Et·Key·Tea in `qs` and ·Et·Excite·Pea·Et·Key·Tea here.

An absent JSON key and an empty TSV cell both mean “same as `qs`”.

## Provenance and license

Derived from [Shavian-info/readlex](https://github.com/Shavian-info/readlex) at commit `8343343`, MIT, © 2024 Shavian-info ([full provenance](../data/readlex/README.md)). This repository is MIT too — see [`LICENSE.md`](../LICENSE.md).

Some entries are not from that corpus — today quikscript and quickscript, each as a proper noun, an adjective and a possessive — because a Quikscript lexicon with no entry for its own alphabet is a gap a reader finds at once. They are declared in [`src/qslex/data/added-words.tsv`](../src/qslex/data/added-words.tsv) and spelled by the same rules as everything else; `meta.counts.added` in the master is how many there are, and [`docs/pipeline.md`](../docs/pipeline.md#words-the-corpus-lacks) says where each field came from.
