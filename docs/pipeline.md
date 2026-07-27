# The build, the row policy, and the artifacts

This is the spec for [`src/qslex/build.py`](../src/qslex/build.py), [`src/qslex/variants.py`](../src/qslex/variants.py) and [`src/qslex/converter.py`](../src/qslex/converter.py) — the layer that runs after the segment mapping ([`docs/ipa-to-qs.md`](ipa-to-qs.md)), the orthographic rules ([`docs/orthographic-rules.md`](orthographic-rules.md)) and the word signs ([`docs/word-signs.md`](word-signs.md)) have decided how a word is spelt, and turns 108,425 spelt rows into files.

It decides nothing about spelling. Everything below is about which rows are carried, what shape they are written in, and how the result is kept honest.

## Artifacts

Everything is generated into [`lexicon/`](../lexicon) and committed, so the files can be used without running the build.

| File | What it is |
|---|---|
| `quikscript-lexicon.json` | The master. Grouped by headword, 56,649 of them, 108,425 entries. |
| `quikscript-lexicon.tsv` | The flat projection, 108,375 rows after deduplication. |
| `qs_converter.json` | Latin → spellings for the transliterator, 78,135 keys, 79,217 rows. |
| `qs_converter_phrases.txt` | The 1,600 entries a tokenizer must match whole. |
| `letters.tsv` | All 44 Quikscript letters with their codepoints — the decoder ring for the PUA text in every other file. |

**JSON-primary, and strictly so.** `quikscript-lexicon.json` is built first and everything else is projected from it in one reshape. Nothing is emitted in parallel, because parallel generation is what produced upstream's duplicate-row TSV ([Shavian-info/readlex#124](https://github.com/Shavian-info/readlex/pull/124)) — the exact bug this arrangement makes structurally impossible. There is one master per layer: `readlex.json` upstream, the rule and override tables in `src/qslex/data/`, `quikscript-lexicon.json` out. Nothing downstream of the build is hand-edited.

## Encoding

Every QS column is [PUA](https://www.quikscript.net/csur/) U+E650–U+E67E, one codepoint per letter, with the corpus's own separators (space, hyphen, apostrophe) passed through as themselves. See [Encoding](../README.md#encoding) in the README for the caveat about that block's status and for language tagging.

## Source of truth: readlex.json, not the TSV

Upstream hand-edits `readlex.json` and generates everything else from it by script. This is stated nowhere in their repo — only in pull request comments ([#124](https://github.com/Shavian-info/readlex/pull/124): "I generate these files from readlex.json, which is the only file I manually edit"; [#70](https://github.com/Shavian-info/readlex/pull/70): the JSON "is more data rich"). Three reasons to follow it rather than read the convenient flat file:

1. **The generated TSV has carried generation bugs** — duplicate rows, PR #124.
2. **The `var` tags the row policy needs exist only in the JSON.** The TSV is five bare columns with no variant field.
3. **It is verifiable, and was verified.** Flattening `readlex.json`, dropping every row whose `var` is not `RRP` or `TrapBath`, and deduplicating on the five-tuple reproduces the vendored TSV **exactly** — all 110,056 rows, nothing left over on either side. So the TSV is a lossy projection of the JSON and the switch loses nothing.

The corpus is vendored at a pinned commit with its SHA-256 recorded, and the loader verifies the digest before use ([provenance](../data/readlex/README.md)). 27 MB is a lot to check in; offline, reproducible builds and a diff that shows exactly what an upstream bump changed are worth it.

## Row policy: the RRP family only

ReadLex carries four accents. This lexicon spells one: **rhotic RP**, which is the standard the corpus is transcribed in and the one Read's own rules assume. `src/qslex/data/var-tags.tsv` states the policy tag by tag and pins the row count for each, and is the only place to read those counts; the validator fails on a count that has drifted.

| Policy | Tags |
|---|---|
| keep, normalised to `RRP` | `RRP`, `RRPVar`, `RRPvar` |
| drop | `TrapBath`, `GenAm`, `Gen Am`, `GenAus`, `SSB` |

Four of them are malformed — `RRPVar`/`RRPvar` are the same tag under two capitalisations, `Gen Am` is `GenAm` with a space, and `SSB` is an accent label nothing else in the corpus uses. They are enumerated in [#7](https://github.com/adiabatic/quikscript-lexicon/issues/7); normalising them is done here rather than there because the filter cannot run without it. Every tag outside upstream's documented four must declare the words it covers, and the validator holds it to that list, so an upstream fix shows up as a rule that stopped matching rather than as a silent change of contents.

Two of those rulings deserve their reasoning on the record:

- **`RRPVar`/`RRPvar` are kept**, normalised to `RRP`. They are second RRP pronunciations, not second accents: again `əˈɡeɪn` beside `əˈɡen`, stance `stɑːns` beside `stæns`, mushy `ˈmʊʃi` beside `ˈmʌʃi`. Upstream's own TSV drops them; we do not, because a variant pronunciation within the accent we spell is a spelling we should carry. Note what is lost by normalising: the artifacts no longer say which of a word's spellings was upstream's primary. With `var` collapsing anyway that information had nowhere to go, and the converter's `⬌` join preserves corpus order, which puts the primary first.
- **`SSB` is dropped.** Its one row is pasta `ˈpæstə`, against the RRP row's `ˈpɑːstə` — a TRAP-BATH variant wearing an accent label instead of the `Æ` capital, so the TrapBath ruling covers it.

With only RRP surviving, the `var` field carries no information and is dropped from the artifacts. The dual `Ɑː`/`Æ` rows in the segment mapping stay, which keeps TrapBath cheap to revisit.

Every one of the 56,649 headwords keeps at least one row, so the filter loses no words — only alternative pronunciations of words it also keeps.

### Where the validator runs, and why it splits

[`src/qslex/validate.py`](../src/qslex/validate.py) makes one pass over the corpus but holds two different row sets to account:

- **The segment layer sees all 111,214 rows.** Mapping-row coverage, quirk rules, stress overrides, token counts, raw-pattern counts and the Shavian EAR oracle all run over everything upstream ships. They have to: the `Æ` mapping row and the `hɪəˈrÆftəR` stress override are exercised *only* by TrapBath rows, so scoping this layer to what we ship would put two correct, still-present rows out of reach of their own never-exercised checks. It also means the tokenizer is proved against the General American rows — which it passes, with zero unmapped residue and no quirk rule of its own.
- **The spelling layer sees only the 108,425 rows the lexicon spells.** Rules, word signs, the junior and ligature columns, and the Manual fixtures are all counted over those. Scoping this layer to everything was tried and rejected: the GenAm rows make `new` and `news` rewrite 14 rows apiece (GenAm `nuː` where RRP `njuː` already gives ·No·Ye·Ooze), and the validator would then demand Manual fixtures justifying spellings that never ship.

One consequence is worth stating plainly, because it looks like a regression and is not. Two of the Manual's own example words, **contrast** and **example**, are spelt in this lexicon with ·Ah where the Manual writes ·At. Both fixtures were derived from ReadLex's TrapBath row, which the row policy drops; re-derived from the surviving BATH row they give ·Key·Ox·No·Tea·Roe·**Ah**·See·Tea and ·It·Gay·Zoo·**Ah**·May·Pea·Low. The Manual's vowel is recorded in the note on each fixture row. This is the TRAP-BATH split itself, and it is the price of the RRP-only ruling.

## Artifact shapes

### quikscript-lexicon.json

Upstream's headword key, verbatim, mapping to the entries under it:

```json
"again_AV0_𐑩𐑜𐑧𐑯": [
    {"Latn": "again", "qs": "…", "Shaw": "𐑩𐑜𐑧𐑯", "pos": "AV0", "ipa": "əˈɡen", "freq": 12345}
]
```

The key is treated as an opaque upstream identifier, not as data — it is kept so that every group is traceable to the group it came from and an upstream bump diffs cleanly. It is *not* re-derived: upstream's own keys can be stale with respect to the entries under them (`'twas_PNP+VBD_𐑑𐑢𐑪𐑟` heads an entry whose Shavian is 𐑑𐑢𐑳𐑟), which is a further reason to carry it rather than to compute one.

`Shaw` is kept. It costs little, it is what the validator's EAR oracle reads, and it makes a row diffable against upstream. `var` is dropped, per the row policy. `qs_junior` and `qs_x` are **absent unless they differ** from `qs` — the sparse encoding, so that the delta stays obvious and a diff stays small.

`ipa` is the **quirk-normalised** string, not the corpus's own, so that every row explains its own spelling rather than the one upstream's unrepaired IPA would have produced. It differs on 124 rows; upstream's original is in the vendored corpus, which is where a diff against ReadLex should read from.

4-space indent, `ensure_ascii=False`, LF, trailing newline, headwords in corpus order.

### quikscript-lexicon.tsv

`Latn`, `qs`, `qs_junior`, `qs_x`, `Shaw`, `pos`, `ipa`, `freq` — upstream's five columns with the Quikscript spelling taking the position the Shavian one held, and the Shavian pushed right rather than dropped. Unlike upstream's, it carries a header row, because eight columns of which two are usually empty are not self-describing.

Sparse columns are empty strings where they do not diverge: 2,347 rows carry a `qs_x`, 5 carry a `qs_junior`. Those bounds are checked, not assumed — `qs_x` may differ only on a word with an `x` in it, and `qs_junior` only on the word-level cases [#3](https://github.com/adiabatic/quikscript-lexicon/issues/3) enumerates.

The projection **deduplicates**. Two headwords can list the same inflected form — ax and axe both own axed — which is 50 rows in this corpus, and flattening without collapsing them is precisely upstream's #124 bug.

### qs_converter.json

Latin → a list of rows, for [#6](https://github.com/adiabatic/quikscript-lexicon/issues/6)'s transliterator:

```json
"absent": [
    {"qs": "…", "tag": "JJ"},
    {"qs": "…", "tag": "NN"},
    {"qs": "…", "tag": "VB"},
    {"qs": "…⬌…", "tag": "0"}
]
```

The shape is upstream's, and it is upstream's for a good reason: `latin2shaw.py` looks a token up by `token.lower_`, walks the rows, and takes the first whose `tag` matches spaCy's Penn `token.tag_`, with `"0"` as the universal fallback. Porting that logic wholesale is the point of matching the shape.

- **Tagged rows appear only where they can settle something** — a word needs both more than one spelling and more than one Penn tag before a part of speech can choose between them. 403 of the 78,135 keys qualify.
- **The `0` row is always present and always last**, its `qs` the `⬌`-joined distinct spellings sorted by codepoint. `⬌` is a "pick one" marker the consumer never splits; upstream punts on disambiguation here and so, for now, do we.
- **`qs_junior` and `qs_x` ride along**, sparse as elsewhere, with their alternatives in the same order as `qs` so the three columns line up positionally.

The C5 → Penn table this needs is `src/qslex/data/c5-to-penn.tsv`. It was not guessed: reimplementing upstream's generator and reproducing `readlex_converter.json` **byte for byte** (9,565,065 bytes) forces a unique Penn tag for 21 of the C5 tags. The rest are marked `standard` and say why — either upstream's file cannot separate them (`VVI`/`VVB` and `VVD`/`VVN` have identical spellings for all 78,135 keys) or upstream never reaches them. Only heteronyms consult the table, so the corpus's other 74 C5 tags need no Penn equivalent and are given none; the build raises rather than guessing if a bump ever makes one relevant.

Two deliberate departures from upstream's file:

- **Row order puts `NNP` first**, then the rest alphabetically. Upstream writes `NN` before `NNP`, and because its consumer's fallback from `NNP` to the `NN` row is tested per row, that fallback fires before the exact `NNP` row is ever reached — making the proper-noun spelling unreachable for 27 keys, among them august, derby, reading and slough. Writing `NNP` first fixes it in the data, with no change needed in any consumer.
- **The row set is our row policy's, not upstream's.** Upstream's converter keeps `var == "RRP"` strictly, so it drops the 16 `RRPVar`/`RRPvar` rows its own TSV also drops. We keep them, so a handful of keys carry one more alternative than upstream's file does.

Quikscript also makes heteronyms Shavian does not. `that` is one spelling in ReadLex and two here — ·They·Tea for the conjunction against ·They·At·Tea for the demonstrative — which is why `CJT` and `DT0` need Penn equivalents that upstream's file never forced.

### qs_converter_phrases.txt

The entries a tokenizer must match as one unit before it splits the text, because splitting them first would spell their pieces and get a different answer.

**Regenerated, not copied.** Upstream ships this list twice, as `readlex_converter_phrases.json` and `.csv`, and the two disagree by 17 lines: the `.csv` tracks the corpus, while the `.json` has not been touched since June 2025 — and the `.json` is the one `latin2shaw.py` actually opens. Neither file is JSON or CSV; both are CRLF plain text. So "reuse the phrase list" has no single referent, and the honest move is to derive it, from our own spellings, under an honest extension.

The predicate is compositionality, not a character test: an entry is listed when spelling its pieces separately and rejoining them does not reproduce the entry's own spelling, when a piece is not in the lexicon at all, or — for a single word — when it contains an apostrophe, which a tokenizer splits at. On top of that sit 14 declared exceptions in `src/qslex/data/phrase-exceptions.tsv`: three HTML entities that are not lexicon entries at all, and eleven words spaCy's tokenizer splits, which no property of the lexicon can reveal.

The list is longer than upstream's — 1,600 against 1,406 — and the reason is real: Quikscript's terminal and prefix conventions are genuinely more context-sensitive than Shavian's, so hundreds of compounds legitimately fail to compose where their Shavian spellings do. It was longer still, 2,171, until the rules learnt to see inside a compound ([#9](https://github.com/adiabatic/quikscript-lexicon/issues/9)); 571 entries were on it only because their elements were spelt one way alone and another way in the compound. The list is regenerated from the spellings either way, so it cannot disagree with them.

It is also *shorter* in eight places, and those are real: at-home, lean-to, set-to, aged care, school-aged and three more compose in Quikscript because a standard word-outline collapses a stressed/unstressed pair that Shavian spells two ways.

### letters.tsv

`codepoint`, `qs`, `name`, `class`, `ipa` for all 44 letters, derived from `src/qslex/csur.py` and the segment mapping. The `name` column is the letter's own example word, which is how [the CSUR proposal](https://www.quikscript.net/csur/) names them; the `ipa` column lists every mapping token that produces the letter, and is empty for ·Excite and ·Exam, which no segment mapping can reach.

## Regenerating

```sh
make artifacts     # rewrite lexicon/
make check         # lint, types, tests, validator, and artifact freshness
```

`make check`'s last step rebuilds every artifact in memory and fails if what is on disk differs, so a stale `lexicon/` cannot be committed. Combined with a clean `git diff` after `make artifacts`, that is the byte-identical-regeneration proof: same checkout, same bytes, every time.

To bump the corpus, replace `data/readlex/readlex.json`, update the commit and digest in [`data/readlex/README.md`](../data/readlex/README.md) and `src/qslex/readlex.py`, then run `make check` and reconcile every invariant that moves. There will be several, and that is the design: a corpus bump is meant to be a reviewable change, not a silent one.

Almost every invariant that moves fails loudly and says what it wanted: the counts pinned in `src/qslex/validate.py`, the row counts in `src/qslex/data/var-tags.tsv`, and the artifacts themselves. Prose cannot, so the numbers still written out in it are the ones to re-read by hand — in this file, its opening line, the [artifact table](#artifacts), the [artifact shapes](#artifact-shapes), [Row policy](#row-policy-the-rrp-family-only) and [Where the validator runs](#where-the-validator-runs-and-why-it-splits); elsewhere, the opening sentence of the [README](../README.md), the sparse-column counts in [`lexicon/README.md`](../lexicon/README.md), the provenance table in [`data/readlex/README.md`](../data/readlex/README.md), and whatever each other spec counts over the corpus.

## Declined, deliberately

**`readlex.dict` and `addendum.dict`.** Upstream ships these for [Dave Coffin's Dechifro scripts](https://www.dechifro.org/shavian/), which render Shavian. Nothing in the Quikscript ecosystem consumes the format, and its `^prefix`/`$suffix` affix machinery duplicates what [hunspell-dict-qs](https://github.com/adiabatic/hunspell-dict-qs) already does for Quikscript. Recorded as a decision rather than left as an omission; if a QS toolchain ever wants it, it projects from the JSON like everything else.

**`readlex_search.json`.** 29 MB serving [readlex.pythonanywhere.com](https://readlex.pythonanywhere.com/). Worth building if and when a search site for Quikscript exists.
