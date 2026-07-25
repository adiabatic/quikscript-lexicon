# Vendored ReadLex corpus

`readlex.json` is vendored verbatim from [Shavian-info/readlex](https://github.com/Shavian-info/readlex) so that the build and the validator's coverage proof are reproducible from a clean checkout, with no network access.

| | |
|---|---|
| Upstream | <https://github.com/Shavian-info/readlex> |
| Commit | `8343343090385938bf8a901748117dce94d9e570` ("Add words", 2026-03-01) |
| SHA-256 | `0e026ee523fe7beea0a34186e17043d6443e8bbe06a699ed175ad2cf31c332e9` |
| Headwords | 56,649 |
| Entries | 111,214 |
| Licence | MIT, © 2024 Shavian-info — see [`LICENSE`](LICENSE) |

Words are grouped by headword. Each entry carries the Latin spelling, the Shavian spelling, the [C5](http://www.natcorp.ox.ac.uk/docs/c5spec.html) part of speech, the IPA, the BNC frequency, and a `var` tag naming the accent it transcribes.

The IPA field carries the capital-letter conventions this project depends on: word signs `Ð T N V F`, reinserted rhotic `R`, TRAP-BATH variants `Ɑː`/`Æ`, the Shavian-convention sites `Ə`/`I`, and — the reason this project reads IPA rather than the Shavian column — the `ʍ`/`w` distinction, which upstream documents as being preserved "for those who want it (e.g. to generate Quikscript spellings)".

## Why this file and not the TSV

Upstream hand-edits `readlex.json` alone and generates `kingsleyreadlexicon.tsv` and every other format from it by script — stated only in pull request comments ([#124](https://github.com/Shavian-info/readlex/pull/124), [#70](https://github.com/Shavian-info/readlex/pull/70)). The generated TSV has carried generation bugs, and the `var` tags this project's row policy needs appear nowhere else.

That relationship was checked rather than assumed: flattening this file, keeping only the `RRP` and `TrapBath` rows and deduplicating on the five-tuple reproduces the TSV exactly, all 110,056 rows, with nothing left over on either side. So the TSV was a lossy projection of what is now vendored here, and it is no longer carried.

## Bumping it

`src/qslex/validate.py` verifies this file's SHA-256 before use, so a corpus bump is always a deliberate, reviewable change rather than a silent one. Replace the file, update the commit and digest above and in `src/qslex/readlex.py`, then run `make check` and reconcile any invariant that moves.
