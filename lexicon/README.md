# The lexicon

Every file here except this README is generated. Do not edit them by hand: `make artifacts` rewrites them, and `make check` fails if a committed file differs from a fresh build. The spec is [`docs/pipeline.md`](../docs/pipeline.md).

The spec’s [Artifacts](../docs/pipeline.md#artifacts) table says what each file is, and [Artifact formats](../docs/pipeline.md#artifact-formats) describes the format of each. No document states how many rows each file has. `meta.counts` in the lexicon JSON has the counts it records, and `make check` compares every file with a fresh build.

`quikscript-lexicon.json` is the source JSON, and the only JSON file here. It has five keys:

- `entries` is the lexicon itself.
- `letters`, `c5_to_penn` and `phrases` are the small tables needed to generate the other files from this one. That includes the transliterator’s Latin-to-spellings table, which is [rebuilt at startup rather than shipped](../docs/pipeline.md#the-converter-table).
- `meta` records the schema version, the corpus repository, commit and SHA-256 the file was built from, the PUA block, and the counts.

The other four files are for tools that do not read JSON. A spreadsheet reads the TSV, a tokenizer reads `qs_converter_phrases.txt`, and hunspell reads the `.dic` and `.aff`.

`en-Qaas.dic` and `en-Qaas.aff` are a hunspell dictionary. `hunspell -i utf-8 -d lexicon/en-Qaas` checks Quikscript text against every unspaced spelling in the three spelling columns. The `-i utf-8` is required: without it hunspell reads the input in the locale’s encoding, and under a non-UTF-8 locale it silently skips every Quikscript line.

## Reading it

Quikscript is written in the Private Use Area, U+E650–U+E67E, one codepoint per letter. Without a Quikscript font, every QS column renders as boxes. The `letters` key in the lexicon JSON maps each codepoint to its letter name, class and IPA. [`docs/conformance.md`](../docs/conformance.md) covers the encoding and how to tag the text.

There are three spelling columns, and two of them are sparse:

- **`qs`** is Senior, the default: Read’s §III conventions plus the Manual’s standard word spellings.
- **`qs_junior`** is present only where the Junior spelling differs, which is a small number of rows. These are the word-level cases and the n't words, whose linking vowel the senior column elides and the junior column keeps ([`docs/orthographic-rules.md`](../docs/orthographic-rules.md#decisions)). The Manual’s affix conventions apply in both grades, so no other rule-driven spelling differs.
- **`qs_x`** is the ·Excite/·Exam X-letter form, built on `qs` and present only where it differs. It is stored rather than derived, because the letters around the X-letter change too: expect is ·It·Key·See·Pea·Et·Key·Tea in `qs` and ·Et·Excite·Pea·Et·Key·Tea in `qs_x`.

An absent JSON key and an empty TSV cell both mean “same as `qs`”.

## Provenance and license

Derived from [Shavian-info/readlex](https://github.com/Shavian-info/readlex) at commit `8343343`, MIT, © 2024 Shavian-info ([full provenance](../data/readlex/README.md)). This repository is also MIT-licensed; see [`LICENSE.md`](../LICENSE.md).

Some entries are not from that corpus. They are listed in [`src/qslex/data/added-words.tsv`](../src/qslex/data/added-words.tsv) and spelled by the same rules as every other entry. `meta.counts.added` in the lexicon JSON is how many there are, and [`docs/pipeline.md`](../docs/pipeline.md#words-the-corpus-lacks) says where each field came from. They include quikscript and quickscript, each as a proper noun, an adjective and a possessive, so that the lexicon has an entry for the name of its own alphabet.
