# Vendored ReadLex corpus

`kingsleyreadlexicon.tsv` is vendored verbatim from [Shavian-info/readlex](https://github.com/Shavian-info/readlex) so that the validator's coverage proof is reproducible from a clean checkout, with no network access.

| | |
|---|---|
| Upstream | <https://github.com/Shavian-info/readlex> |
| Commit | `8343343090385938bf8a901748117dce94d9e570` ("Add words", 2026-03-01) |
| SHA-256 | `6f71dc6179fc9c579930a38693e445cb5fd491771fde7bcecf310e2352126038` |
| Rows | 110,056 |
| Licence | MIT, © 2024 Shavian-info — see [`LICENSE`](LICENSE) |

Columns: Latin spelling, Shavian spelling, [C5](http://www.natcorp.ox.ac.uk/docs/c5spec.html) part of speech, IPA, BNC frequency.

The IPA column carries the capital-letter conventions this project depends on: word signs `Ð T N V F`, reinserted rhotic `R`, TRAP-BATH variants `Ɑː`/`Æ`, the Shavian-convention sites `Ə`/`I`, and — the reason this project reads IPA rather than the Shavian column — the `ʍ`/`w` distinction, which upstream documents as being preserved "for those who want it (e.g. to generate Quikscript spellings)".

`src/qslex/validate.py` verifies this file's SHA-256 before use, so a corpus bump is always a deliberate, reviewable change rather than a silent one. To bump it: replace the file, update the commit and digest above and in `src/qslex/readlex.py`, then re-run the validator and reconcile any invariant that moves.
