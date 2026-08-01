# The build, the row policy, and the artifacts

This is the spec for [`src/qslex/build.py`](../src/qslex/build.py), [`src/qslex/variants.py`](../src/qslex/variants.py), [`src/qslex/converter.py`](../src/qslex/converter.py) and [`src/qslex/hunspell.py`](../src/qslex/hunspell.py) — the layer that runs after the segment mapping ([`docs/ipa-to-qs.md`](ipa-to-qs.md)), the orthographic rules ([`docs/orthographic-rules.md`](orthographic-rules.md)) and the word signs ([`docs/word-signs.md`](word-signs.md)) have decided how a word is spelt, and turns 108,425 spelt rows into files.

It decides nothing about spelling. Everything below is about which rows are carried, what shape they are written in, and how the result is kept honest.

## Artifacts

Everything is generated into [`lexicon/`](../lexicon) and committed, so the files can be used without running the build.

| File                          | What it is                                                                                               |
| ----------------------------- | -------------------------------------------------------------------------------------------------------- |
| `quikscript-lexicon.json`     | The master, and the only JSON. Grouped by headword, 56,649 of them, 108,425 entries.                     |
| `quikscript-lexicon.tsv`      | The flat projection, 108,375 rows after deduplication.                                                   |
| `qs_converter_phrases.txt`    | The 1,600 entries a tokenizer must match whole.                                                          |
| `en-Qaas.dic` / `en-Qaas.aff` | The Hunspell spelling dictionary, 75,581 entries.                                                        |

**JSON-primary, and strictly so.** `quikscript-lexicon.json` is built first and everything else is projected from it in one reshape. Nothing is emitted in parallel, because parallel generation is what produced upstream's duplicate-row TSV ([Shavian-info/readlex#124](https://github.com/Shavian-info/readlex/pull/124)) — the exact bug this arrangement makes structurally impossible. There is one master per layer: `readlex.json` upstream, the rule and override tables in `src/qslex/data/`, `quikscript-lexicon.json` out. Nothing downstream of the build is hand-edited.

**One JSON, and only one.** A second JSON was shipped until it was measured: `qs_converter.json` covered the same 78,135 words, carried the same spelling in every one of the three columns, and differed only in writing a Penn tag where the master writes the C5 tag it is a rename of. Nine megabytes to say what the master already said. It is [rebuilt, not shipped](#the-converter-shape) — the master now carries the tag map it is keyed by, so the file it used to be comes back byte for byte from the master alone. The other three artifacts stay committed because they are formats, not restatements: a spreadsheet reads the TSV and hunspell reads the `.dic`, and neither can read JSON.

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

| Policy                    | Tags                                           |
| ------------------------- | ---------------------------------------------- |
| keep, normalised to `RRP` | `RRP`, `RRPVar`, `RRPvar`                      |
| drop                      | `TrapBath`, `GenAm`, `Gen Am`, `GenAus`, `SSB` |

Four of them are malformed — `RRPVar`/`RRPvar` are the same tag under two capitalisations, `Gen Am` is `GenAm` with a space, and `SSB` is an accent label nothing else in the corpus uses. They are enumerated in [#7](https://github.com/adiabatic/quikscript-lexicon/issues/7); normalising them is done here rather than there because the filter cannot run without it. Every tag outside upstream's documented four must declare the words it covers, and the validator holds it to that list, so an upstream fix shows up as a rule that stopped matching rather than as a silent change of contents.

Two of those rulings deserve their reasoning on the record:

- **`RRPVar`/`RRPvar` are kept**, normalised to `RRP`. They are second RRP pronunciations, not second accents: again `əˈɡeɪn` beside `əˈɡen`, stance `stɑːns` beside `stæns`, mushy `ˈmʊʃi` beside `ˈmʌʃi`. Upstream's own TSV drops them; we do not, because a variant pronunciation within the accent we spell is a spelling we should carry. Note what is lost by normalising: the artifacts no longer say which of a word's spellings was upstream's primary. With `var` collapsing anyway that information had nowhere to go, and the converter's `⬌` join preserves corpus order, which puts the primary first.
- **`SSB` is dropped.** Its one row is pasta `ˈpæstə`, against the RRP row's `ˈpɑːstə` — a TRAP-BATH variant wearing an accent label instead of the `Æ` capital, so the TrapBath ruling covers it.

With only RRP surviving, the `var` field carries no information and is dropped from the artifacts. The dual `Ɑː`/`Æ` rows in the segment mapping stay, which keeps TrapBath cheap to revisit.

Every one of the 56,649 headwords keeps at least one row, so the filter loses no words — only alternative pronunciations of words it also keeps.

### Where the validator runs, and why it splits

[`src/qslex/validate.py`](../src/qslex/validate.py) makes one pass over the corpus but holds two different row sets to account:

- **The segment layer sees all 111,214 rows.** Mapping-row coverage, quirk rules, stress overrides, token counts, raw-pattern counts and the Shavian EAR oracle all run over everything upstream ships. They have to: the `Æ` mapping row and the `hɪəˈrÆftəR` stress override are exercised *only* by TrapBath rows, so scoping this layer to what we ship would put two correct, still-present rows out of reach of their own never-exercised checks. It also means the tokenizer is proved against the General American rows — which it passes, with zero unmapped residue and no quirk rule of its own.
- **The spelling layer sees only the 108,425 rows the lexicon spells.** Rules, word signs, the junior and X-letter columns, and the Manual fixtures are all counted over those. Scoping this layer to everything was tried and rejected: the GenAm rows make `new` and `news` rewrite 14 rows apiece (GenAm `nuː` where RRP `njuː` already gives ·No·Ye·Ooze), and the validator would then demand Manual fixtures justifying spellings that never ship.

One consequence is worth stating plainly, because it looks like a regression and is not. Two of the Manual's own example words, **contrast** and **example**, are spelt in this lexicon with ·Ah where the Manual writes ·At. Both fixtures were derived from ReadLex's TrapBath row, which the row policy drops; re-derived from the surviving BATH row they give ·Key·Ox·No·Tea·Roe·**Ah**·See·Tea and ·It·Gay·Zoo·**Ah**·May·Pea·Low. The Manual's vowel is recorded in the note on each fixture row. This is the TRAP-BATH split itself, and it is the price of the RRP-only ruling.

## Artifact shapes

### quikscript-lexicon.json

Five top-level keys, of which `entries` is all but forty kilobytes of the file:

```json
{
    "meta": {"version": 1, "source": {"repo": "…", "commit": "…", "sha256": "…"},
             "encoding": {"block": "U+E650–U+E67E"},
             "counts": {"headwords": 56649, "entries": 108425, "phrases": 1600}},
    "letters": [{"codepoint": "U+E650", "qs": "…", "name": "Pea", "class": "consonant", "ipa": "p"}],
    "c5_to_penn": {"AJ0": "JJ", "AJC": "JJR"},
    "phrases": ["&amp;", "'em", "'neath"],
    "entries": {
        "again_AV0_𐑩𐑜𐑧𐑯": [{"Latn": "again", "qs": "…", "Shaw": "𐑩𐑜𐑧𐑯", "pos": "AV0", "ipa": "əˈɡen", "freq": 12345}]
    }
}
```

The four small keys are what makes this the only file a consumer needs. `letters` is the decoder ring, without which every QS string is a row of boxes: `codepoint`, `qs`, `name`, `class`, `ipa` for all 44 letters, derived from `src/qslex/csur.py` and the segment mapping. The `name` is the letter's own example word, which is how [the CSUR proposal](https://www.quikscript.net/csur/) names them; the `ipa` lists every mapping token that produces the letter, and is empty for ·Excite and ·Exam, which no segment mapping can reach. `c5_to_penn` is the tag map the converter shape's rows are keyed by. `phrases` is the one projection no property of the entries can reveal, because it is the orthographic rules and not the data that decide what fails to compose. `meta` says which corpus commit the file came from and how much of it there is.

Two of the three duplicate a file that also ships: `src/qslex/data/c5-to-penn.tsv` and `qs_converter_phrases.txt`. Duplication is normally how two copies drift, and it cannot here: all three are written by the same pass of `build.artifacts()`, and `make check` rebuilds and byte-compares every one of them. `letters` ships nowhere else — the master is the only place the alphabet is named.

The `entries` key is upstream's headword key, verbatim, mapping to the entries under it. The key is treated as an opaque upstream identifier, not as data — it is kept so that every group is traceable to the group it came from and an upstream bump diffs cleanly. It is *not* re-derived: upstream's own keys can be stale with respect to the entries under them (`'twas_PNP+VBD_𐑑𐑢𐑪𐑟` heads an entry whose Shavian is 𐑑𐑢𐑳𐑟), which is a further reason to carry it rather than to compute one.

`Shaw` is kept. It costs little, it is what the validator's EAR oracle reads, and it makes a row diffable against upstream. `var` is dropped, per the row policy. `qs_junior` and `qs_x` are **absent unless they differ** from `qs` — the sparse encoding, so that the delta stays obvious and a diff stays small.

`ipa` is the **quirk-normalised** string, not the corpus's own, so that every row explains its own spelling rather than the one upstream's unrepaired IPA would have produced. It differs on 124 rows; upstream's original is in the vendored corpus, which is where a diff against ReadLex should read from.

**One headword to a line**, and one letter and one phrase to a line likewise; `meta` and `c5_to_penn` are small enough to indent four spaces in the ordinary way. The file is generated, so the diff worth reading is which entries moved, and that reads as one changed line each rather than as a field adrift in a nine-line block. It costs ten megabytes less than a field to a line did. `ensure_ascii=False`, LF, trailing newline, headwords in corpus order.

### quikscript-lexicon.tsv

`Latn`, `qs`, `qs_junior`, `qs_x`, `Shaw`, `pos`, `ipa`, `freq` — upstream's five columns with the Quikscript spelling taking the position the Shavian one held, and the Shavian pushed right rather than dropped. Unlike upstream's, it carries a header row, because eight columns of which two are usually empty are not self-describing.

Sparse columns are empty strings where they do not diverge: 2,347 rows carry a `qs_x`, 27 carry a `qs_junior`. Those bounds are checked, not assumed — `qs_x` may differ only on a word with an `x` in it, and `qs_junior` only on the word-level cases [#3](https://github.com/adiabatic/quikscript-lexicon/issues/3) enumerates plus the rows whose linking vowel [`terminal-nt`](orthographic-rules.md#decisions) elides in senior alone.

The projection **deduplicates**. Two headwords can list the same inflected form — ax and axe both own axed — which is 50 rows in this corpus, and flattening without collapsing them is precisely upstream's #124 bug.

### The converter shape

Not an artifact. It is built on the way to the phrase list, handed to the transliterator, and never written — but it is still a shape this repository specifies, because [#6](https://github.com/adiabatic/quikscript-lexicon/issues/6)'s transliterator is a port of `latin2shaw.py` and the shape is what makes the port a port.

Latin → a list of rows:

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

**Rebuilding it.** Every input is in the master: the five fields `converter()` reads are `entries`, and the tag map is `c5_to_penn`. Nothing else is opened.

```python
import json
from qslex.converter import TagMap, converter

master = json.load(open("lexicon/quikscript-lexicon.json", encoding="utf-8"))
rows = converter(
    (
        (e["Latn"], e["pos"], e["qs"], e.get("qs_junior", ""), e.get("qs_x", ""))
        for group in master["entries"].values()
        for e in group
    ),
    {c5: TagMap(c5, penn, "upstream", "") for c5, penn in master["c5_to_penn"].items()},
)
```

That reproduces the 9 MB file this repository used to commit byte for byte, and a test holds it to the rows the build derives in memory, so the shape cannot quietly stop being recoverable.

### qs_converter_phrases.txt

The entries a tokenizer must match as one unit before it splits the text, because splitting them first would spell their pieces and get a different answer.

**Regenerated, not copied.** Upstream ships this list twice, as `readlex_converter_phrases.json` and `.csv`, and the two disagree by 17 lines: the `.csv` tracks the corpus, while the `.json` has not been touched since June 2025 — and the `.json` is the one `latin2shaw.py` actually opens. Neither file is JSON or CSV; both are CRLF plain text. So "reuse the phrase list" has no single referent, and the honest move is to derive it, from our own spellings, under an honest extension.

The predicate is compositionality, not a character test: an entry is listed when spelling its pieces separately and rejoining them does not reproduce the entry's own spelling, when a piece is not in the lexicon at all, or — for a single word — when it contains an apostrophe, which a tokenizer splits at. On top of that sit 14 declared exceptions in `src/qslex/data/phrase-exceptions.tsv`: three HTML entities that are not lexicon entries at all, and eleven words spaCy's tokenizer splits, which no property of the lexicon can reveal.

The list is longer than upstream's — 1,600 against 1,406 — and the reason is real: Quikscript's terminal and prefix conventions are genuinely more context-sensitive than Shavian's, so hundreds of compounds legitimately fail to compose where their Shavian spellings do. It was longer still, 2,171, until the rules learnt to see inside a compound ([#9](https://github.com/adiabatic/quikscript-lexicon/issues/9)); 571 entries were on it only because their elements were spelt one way alone and another way in the compound. The list is regenerated from the spellings either way, so it cannot disagree with them.

It is also *shorter* in eight places, and those are real: at-home, lean-to, set-to, aged care, school-aged and three more compose in Quikscript because a standard word-outline collapses a stressed/unstressed pair that Shavian spells two ways.

### en-Qaas.dic / en-Qaas.aff

A [Hunspell](https://github.com/hunspell/hunspell) dictionary, named for the language tag [the README](../README.md#encoding) says to write Quikscript text under. Point a checker at it with `hunspell -i utf-8 -d lexicon/en-Qaas`. The `-i` is not optional. hunspell decodes its input in the locale's encoding and every Quikscript letter is outside ASCII, so under `LC_ALL=C` a line of Quikscript is skipped in silence — nothing accepted, nothing flagged, the same failure mode `WORDCHARS` fixes from the other side — and with no locale set at all hunspell errors out of iconv and prints mangled tokens instead. Naming the input encoding is correct in every locale.

The `.dic` is **every distinct spelling any of the three columns ships**, one per line, sorted by codepoint, counted on the first line as the format wants. All three go in, so the dictionary accepts Senior, Junior and the X-letter form alike; a spelling several rows share is listed once.

Two rulings shape it:

- **Spaced entries are dropped**, 605 of the 76,186 distinct spellings. A tokenizer splits at a space before it consults a dictionary, so no such string can ever reach hunspell, and listing one would be a line that cannot match. Hyphenated entries are kept whole, and are reachable — see `WORDCHARS` below.
- **No word carries an affix flag.** ReadLex lists every inflected form as a row of its own, so the affix machinery would encode nothing the word list does not already state, and a flag standing for no rule is a flag that can only go wrong. The `.aff` declares no `PFX` or `SFX` at all.

The `.aff` is four directives, all of them derived:

- **`SET UTF-8`**, because the spellings are.
- **`WORDCHARS`**, all 44 letters and the hyphen. Without it hunspell's own tokenizer takes PUA codepoints for punctuation and skips every Quikscript word silently — neither accepted nor flagged. The hyphen is in it against the en_US precedent, which leaves it out: 569 of the 6,058 hyphenated entries have a non-empty piece that is not itself an entry — papier-mache, bob-omb, terra-cotta — and without it the tokenizer splits them and flags the pieces. The 43 prefix-style entries that end in a hyphen, pre- among them, are outside that count, because the empty piece an edge hyphen leaves is nothing to look up and they pass either way. Nothing is lost by including it, because hunspell's default `BREAK` still checks the pieces of a hyphenated word the dictionary does not carry whole. The cost is that a bare hyphen run becomes a token of its own and is flagged — a spaced dash, `--` or `---` between spaces, the `- ` opening a Markdown-style bullet — though a hyphen run inside a word is still accepted. Recorded and not fixed: that same default `BREAK` accepts any hyphenated join of two entries whether or not the join is a word, and with 20 single-letter entries in the `.dic` that reaches down to ·Zoo-·Vie.
- **`TRY`**, the 44 letters ordered by how often each occurs across the word list, commonest first, ties by codepoint. hunspell walks it in order when it tries one letter in place of another, so it is counted off the list rather than chosen.
- **`REP`**, bridging ·Excite to ·Key·See and ·Exam to ·Gay·Zoo, in both directions. Both directions earn their place, because the letters around an X-letter change with it: expect is ·It·Key·See·Pea·Et·Key·Tea in `qs` and ·Et·Excite·Pea·Et·Key·Tea in `qs_x`, so neither form is a single-letter edit from the other. Without the table the ngram suggester still turns the other form up about half the time, but buried in a list and effectively never first; with it, writing either an X-letter or the pair it stands for gets exactly one suggestion and it is the right form. A `MAP` table over the same two pairs was tried and dropped: on its own it works, and beside `REP` it changed no suggestion.

**The apostrophe stays out of `WORDCHARS`**, and that is a ruling rather than an omission. No spelling column carries an apostrophe anywhere, so no `.dic` entry can: the corpus spells they'll solid, ·They·Eight·Low. The transliterator does write one — [`src/qslex/latin2qs.py`](../src/qslex/latin2qs.py) reinserts U+2019 before a kept clitic's letters in every mode, giving the Manual's ·They·Eight’·Low ([Apostrophes](latin2qs.md#apostrophes)) — and against this `.aff` hunspell splits at it, passes the host word and flags the clitic half ·Low alone. Putting ’ in `WORDCHARS` would be strictly worse: the whole token would then be looked up, no entry carries an apostrophe, and default `BREAK` does not break at one, so the entire word would be flagged instead of just the clitic. Clitic-bearing transliterator output is outside what a dictionary generated from the columns can bless, and the cheaper failure is the one that still blesses the host word.

This word set, this `TRY` order and this `REP` table are also what [the desk](desk.md) checks against in a browser — widened only by [the §III contractions](desk.md#the-iii-senior-contractions) its checker adds, which no column and so no `.dic` entry can carry — re-derived from the master and asserted against these two files on every build of it.

## Regenerating

```sh
make artifacts     # rewrite lexicon/
make check         # lint, types, tests, validator, and artifact freshness
```

`make check`'s last step rebuilds every artifact in memory and fails if what is on disk differs, so a stale `lexicon/` cannot be committed. Combined with a clean `git diff` after `make artifacts`, that is the byte-identical-regeneration proof: same checkout, same bytes, every time.

To bump the corpus, replace `data/readlex/readlex.json`, update the commit and digest in [`data/readlex/README.md`](../data/readlex/README.md) and `src/qslex/readlex.py`, then run `make check` and reconcile every invariant that moves. There will be several, and that is the design: a corpus bump is meant to be a reviewable change, not a silent one.

Almost every invariant that moves fails loudly and says what it wanted: the counts pinned in `src/qslex/validate.py`, the row counts in `src/qslex/data/var-tags.tsv`, and the artifacts themselves. Prose cannot, so the numbers still written out in it are the ones to re-read by hand — in this file, its opening line, the [artifact table](#artifacts), the [artifact shapes](#artifact-shapes), [Row policy](#row-policy-the-rrp-family-only) and [Where the validator runs](#where-the-validator-runs-and-why-it-splits); elsewhere, the opening sentence of the [README](../README.md), the sparse-column counts in [`lexicon/README.md`](../lexicon/README.md), the provenance table in [`data/readlex/README.md`](../data/readlex/README.md), and whatever each other spec counts over the corpus.

## Declined, deliberately

**`readlex.dict` and `addendum.dict`.** Upstream ships these for [Dave Coffin's Dechifro scripts](https://www.dechifro.org/shavian/), which render Shavian. Nothing in the Quikscript ecosystem consumes the format, and its `^prefix`/`$suffix` affix machinery encodes Shavian's affixes rather than Read's. Recorded as a decision rather than left as an omission; if a QS toolchain ever wants it, it projects from the JSON like everything else.

**`readlex_search.json`.** 29 MB serving [readlex.pythonanywhere.com](https://readlex.pythonanywhere.com/). Worth building if and when a search site for Quikscript exists.
