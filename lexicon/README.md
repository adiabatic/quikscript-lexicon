# The lexicon

Generated. Do not edit anything here by hand — `make artifacts` rewrites all of it, and `make check` fails if what is committed differs from a fresh build. The spec is [`docs/pipeline.md`](../docs/pipeline.md).

What the files are, and how many rows each carries, is the spec's [Artifacts](../docs/pipeline.md#artifacts) table; the shape of each is under [Artifact shapes](../docs/pipeline.md#artifact-shapes).

`en-Qaas.dic` and `en-Qaas.aff` are the pair a spell checker wants: `hunspell -i utf-8 -d lexicon/en-Qaas` checks Quikscript text against every unspaced spelling the three columns ship. The `-i` matters — without it hunspell reads the input in the locale's encoding, and under a non-UTF-8 one it skips every Quikscript line without a word of complaint.

## Reading it

Quikscript is written in the Private Use Area, U+E650–U+E67E, one codepoint per letter — so without a Quikscript font every QS column renders as blank boxes. `letters.tsv` names each codepoint; [the README](../README.md#encoding) covers the encoding and how to tag the text.

Three spelling columns, and two of them are sparse:

- **`qs`** — Senior, the default: Read's §III conventions plus the Manual's standard word spellings.
- **`qs_junior`** — present only where the Junior spelling genuinely differs, which is 8 rows. The Manual's affix conventions are how Quikscript is spelt in both grades, so rule-driven spellings never diverge; only word-level cases do.
- **`qs_x`** — the ·Excite/·Exam ligature form, built on `qs`, present only where it differs (2,347 rows). Stored rather than derived, because the surrounding letters change too: expect is ·It·Key·See·Pea·Et·Key·Tea in `qs` and ·Et·Excite·Pea·Et·Key·Tea here.

An absent JSON key and an empty TSV cell both mean "same as `qs`".

## Provenance and licence

Derived from [Shavian-info/readlex](https://github.com/Shavian-info/readlex) at commit `8343343`, MIT, © 2024 Shavian-info ([full provenance](../data/readlex/README.md)). This repository is MIT too — see [`LICENSE.md`](../LICENSE.md).
