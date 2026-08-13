# Vendored ReadLex corpus

`readlex.json` is vendored verbatim from [Shavian-info/readlex](https://github.com/Shavian-info/readlex) so that the build and the validator's coverage proof are reproducible from a clean checkout, with no network access.

|           |                                                                      |
| --------- | -------------------------------------------------------------------- |
| Upstream  | <https://github.com/Shavian-info/readlex>                            |
| Commit    | `8343343090385938bf8a901748117dce94d9e570` ("Add words", 2026-03-01) |
| SHA-256   | `0e026ee523fe7beea0a34186e17043d6443e8bbe06a699ed175ad2cf31c332e9`   |
| Headwords | 56,649                                                               |
| Entries   | 111,214                                                              |
| License   | MIT, © 2024 Shavian-info — see [`LICENSE`](LICENSE)                  |

Words are grouped by headword. Each entry carries the Latin spelling, the Shavian spelling, the [C5](http://www.natcorp.ox.ac.uk/docs/c5spec.html) part of speech, the IPA, the BNC frequency, and a `var` tag naming the accent it transcribes.

The IPA field carries the capital-letter conventions this project depends on: word signs `Ð T N V F`, reinserted rhotic `R`, TRAP-BATH variants `Ɑː`/`Æ`, the Shavian-convention sites `Ə`/`I`, and — the reason this project reads IPA rather than the Shavian column — the `ʍ`/`w` distinction, which upstream documents as being preserved "for those who want it (e.g. to generate Quikscript spellings)".

## Why this file and not the TSV

Upstream hand-edits `readlex.json` alone and generates every other format from it by script, the `var` tags this project's row policy needs appear nowhere else, and the generated TSV was checked to be a lossy projection of this file rather than a second source — so it is not vendored beside it. The argument, with the pull requests it rests on and the check that was run, is in [`docs/pipeline.md`](../../docs/pipeline.md#source-of-truth-readlexjson-not-the-tsv).

## Bumping it

`src/qslex/validate.py` verifies this file's SHA-256 before use, so a corpus bump is always a deliberate, reviewable change rather than a silent one. The recipe is in [`docs/pipeline.md`](../../docs/pipeline.md#regenerating); the commit and digest above are one of the two places it has you update.
