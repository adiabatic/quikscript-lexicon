# The lexicon

Generated. Do not edit anything here by hand — `make artifacts` rewrites all of it, and `make check` fails if what is committed differs from a fresh build. The spec is [`docs/pipeline.md`](../docs/pipeline.md).

| File | What it is |
|---|---|
| `quikscript-lexicon.json` | The master: 56,649 headwords, 108,425 entries |
| `quikscript-lexicon.tsv` | The flat projection, 108,375 rows, with a header |
| `qs_converter.json` | Latin → spellings by part of speech, for the transliterator |
| `qs_converter_phrases.txt` | Entries a tokenizer has to match whole |
| `letters.tsv` | Every Quikscript letter and its codepoint |

## Reading it

Quikscript is written in the Private Use Area, U+E650–U+E67E, one codepoint per letter — so without a Quikscript font every QS column renders as blank boxes. `letters.tsv` names each codepoint; [the README](../README.md#encoding) covers the encoding and how to tag the text.

Three spelling columns, and two of them are sparse:

- **`qs`** — Senior, the default: Read's §III conventions plus the Manual's standard word spellings.
- **`qs_junior`** — present only where the Junior spelling genuinely differs, which is 5 rows. The Manual's affix conventions are how Quikscript is spelt in both grades, so rule-driven spellings never diverge; only word-level cases do.
- **`qs_x`** — the ·Excite/·Exam ligature form, built on `qs`, present only where it differs (2,347 rows). Stored rather than derived, because the surrounding letters change too: expect is ·It·Key·See·Pea·Et·Key·Tea in `qs` and ·Et·Excite·Pea·Et·Key·Tea here.

An absent JSON key and an empty TSV cell both mean "same as `qs`".

## Provenance and licence

Derived from [Shavian-info/readlex](https://github.com/Shavian-info/readlex) at commit `8343343`, MIT, © 2024 Shavian-info ([full provenance](../data/readlex/README.md)). This repository is MIT too — see [`LICENSE.md`](../LICENSE.md).
