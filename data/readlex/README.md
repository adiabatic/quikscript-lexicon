# Vendored ReadLex corpus

`readlex.json` is an unmodified copy of the file from [Shavian-info/readlex](https://github.com/Shavian-info/readlex). It is vendored so that the build and the validator’s coverage check can run from a clean checkout without network access.

|           |                                                                      |
| --------- | -------------------------------------------------------------------- |
| Upstream  | <https://github.com/Shavian-info/readlex>                            |
| Commit    | `8343343090385938bf8a901748117dce94d9e570` ("Add words", 2026-03-01) |
| SHA-256   | `0e026ee523fe7beea0a34186e17043d6443e8bbe06a699ed175ad2cf31c332e9`   |
| Headwords | 56,649                                                               |
| Entries   | 111,214                                                              |
| License   | MIT, © 2024 Shavian-info. See [`LICENSE`](LICENSE).                  |

Entries are grouped by headword. Each entry has the Latin spelling, the Shavian spelling, the [C5](http://www.natcorp.ox.ac.uk/docs/c5spec.html) part of speech, the IPA, the BNC frequency, and a `var` tag naming the accent the entry transcribes.

The IPA field uses capital letters for several conventions this project depends on:

- the word signs `Ð T N V F`;
- reinserted rhotic `R`;
- the TRAP-BATH variants `Ɑː` and `Æ`;
- `Ə` and `I`, which mark places where Shavian spelling conventions apply.

The IPA also distinguishes `ʍ` from `w`. Upstream says this distinction is kept “for those who want it (e.g. to generate Quikscript spellings)”. The Shavian column writes both as 𐑢, which is the reason this project reads the IPA and not the Shavian column.

## Why this file and not the TSV

Upstream edits only `readlex.json` by hand and generates every other format from it with a script. The `var` tags that this project’s row policy needs appear only in this file. A check found that the generated TSV can be derived from this file and contains less information, so the TSV is not vendored. [`docs/pipeline.md`](../../docs/pipeline.md#source-of-truth-readlexjson-not-the-tsv) gives the full argument, the pull requests it relies on, and the check that was run.

## Bumping it

`src/qslex/readlex.py` checks this file’s SHA-256 before reading it, so replacing the file fails the build until the recorded SHA-256 is updated to match. The steps are in [`docs/pipeline.md`](../../docs/pipeline.md#regenerating). They include updating the commit, digest, headword count and entry count in the table above and in `src/qslex/readlex.py`. `load_rows` checks the counts against `CORPUS_HEADWORDS` and `CORPUS_ROWS`.
