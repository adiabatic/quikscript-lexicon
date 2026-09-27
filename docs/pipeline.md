# The build, the row policy, and the artifacts

This is the spec for [`src/qslex/build.py`](../src/qslex/build.py), [`src/qslex/variants.py`](../src/qslex/variants.py), [`src/qslex/added.py`](../src/qslex/added.py), [`src/qslex/converter.py`](../src/qslex/converter.py) and [`src/qslex/hunspell.py`](../src/qslex/hunspell.py). This layer runs after the segment mapping ([`docs/ipa-to-qs.md`](ipa-to-qs.md)), the orthographic rules ([`docs/orthographic-rules.md`](orthographic-rules.md)) and the word signs ([`docs/word-signs.md`](word-signs.md)) have decided how a word is spelled. It writes the spelled rows to files.

It makes no spelling decisions. This document covers which corpus rows are included, the format of each output file, and how the result is checked.

## Artifacts

Everything is generated into [`lexicon/`](../lexicon) and committed, so the files can be used without running the build.

| File                          | What it is                                                                                               |
| ----------------------------- | -------------------------------------------------------------------------------------------------------- |
| `quikscript-lexicon.json`     | The source JSON, and the only JSON. Every entry, grouped by headword.                                    |
| `quikscript-lexicon.tsv`      | The same entries as a flat table, one row per entry, deduplicated.                                       |
| `qs_converter_phrases.txt`    | The entries a tokenizer must match whole.                                                                |
| `en-Qaas.dic` / `en-Qaas.aff` | The Hunspell spelling dictionary: every unspaced spelling in the three spelling columns.                 |

**This file gives no counts for the artifacts.** A corpus update changes all of them at once, and prose that states them becomes wrong without any check failing. `meta.counts` in the lexicon JSON has the headword, entry, phrase and added-word counts. The expected counts in `src/qslex/validate.py` and `src/qslex/readlex.py` cover what it does not. Anything neither names is covered by `make check`, which fails when a committed artifact differs from a fresh build.

**One set of entries.** `build.artifacts()` generates every artifact from the same list of spelled entries in one call, and the lexicon JSON contains everything the other artifacts are derived from. This rules out the kind of generation bug that gave upstream’s TSV duplicate rows ([Shavian-info/readlex#124](https://github.com/Shavian-info/readlex/pull/124)). Each stage has one source file. Upstream edits `readlex.json`. This repository edits the rule and override tables in `src/qslex/data/`. The build writes `quikscript-lexicon.json`. Nothing the build writes is edited by hand.

**One JSON file.** The repository used to commit a second JSON file, `qs_converter.json`. It covered the same words and had the same spelling in each of the three columns. It differed only in writing a Penn tag where the lexicon JSON writes the C5 tag that maps to it. It was 9 MB. It is no longer committed. The lexicon JSON now includes the tag map, so the file the build used to write can be [rebuilt from the lexicon JSON alone](#the-converter-table). The other three artifacts stay committed because they are in formats other tools read. A spreadsheet reads the TSV and hunspell reads the `.dic`, and neither reads JSON.

## Encoding

Every QS column uses [PUA](https://www.quikscript.net/csur/) U+E650–U+E67E, one codepoint per letter. The corpus’s spaces and hyphens are kept as they are. See [what we conform to](conformance.md) for the caveat about that block’s status and for language tagging.

## Source of truth: readlex.json, not the TSV

Upstream edits `readlex.json` by hand and generates everything else from it by script. Upstream’s repository does not document this. It is stated only in pull request comments ([#124](https://github.com/Shavian-info/readlex/pull/124): “I generate these files from readlex.json, which is the only file I manually edit”; [#70](https://github.com/Shavian-info/readlex/pull/70): the JSON “is more data rich”). This repository reads the JSON instead of the flat TSV, for three reasons:

1. **The generated TSV has had generation bugs**, such as the duplicate rows in PR #124.
2. **The `var` tags the row policy needs are only in the JSON.** The TSV has five columns and no variant field.
3. **The TSV was checked against the JSON.** Flattening `readlex.json`, dropping every row whose `var` is not `RRP` or `TrapBath`, and deduplicating on the five columns reproduces upstream’s TSV at the vendored commit exactly: all 110,056 rows, with nothing extra on either side. So the TSV is the JSON with information removed, and reading the JSON loses nothing.

The corpus is vendored at a pinned commit with its SHA-256 recorded, and the loader verifies the digest before use ([provenance](../data/readlex/README.md)). The file is 27 MB. Committing it makes builds reproducible offline, and a diff shows what a corpus update changed.

## Row policy: the RRP family only

ReadLex has rows for four accents. This lexicon spells one: **rhotic RP**. The corpus is transcribed in it, and Read’s own rules assume it. `src/qslex/data/var-tags.tsv` gives the policy for each tag and the expected row count for each. It is the only place those counts are written. The validator fails when a tag’s row count changes.

| Policy                    | Tags                                           |
| ------------------------- | ---------------------------------------------- |
| keep, normalized to `RRP` | `RRP`, `RRPVar`, `RRPvar`                      |
| drop                      | `TrapBath`, `GenAm`, `Gen Am`, `GenAus`, `SSB` |

Four of the tags are malformed:

- `RRPVar` and `RRPvar` are the same tag with two capitalizations.
- `Gen Am` is `GenAm` with a space.
- `SSB` is an accent label that no other corpus row uses.

[#7](https://github.com/adiabatic/quikscript-lexicon/issues/7) lists them. They are normalized here rather than upstream because the filter cannot run without it. Every tag outside upstream’s four documented tags must list the words it covers, and the validator checks the tag’s rows against that list. If upstream fixes a tag, the validator fails because a listed word no longer has that tag.

Two of these decisions need explanation:

- **`RRPVar`/`RRPvar` are kept**, normalized to `RRP`. They are second RRP pronunciations, not second accents: again `əˈɡeɪn` beside `əˈɡen`, stance `stɑːns` beside `stæns`, mushy `ˈmʊʃi` beside `ˈmʌʃi`. Upstream’s own TSV drops them. This lexicon keeps them, because a variant pronunciation within the accent it spells is a spelling it should include. Normalizing them loses one piece of information: the artifacts no longer mark which of a word’s spellings was upstream’s primary. The `var` field is dropped anyway, so that information has nowhere to go. The lexicon JSON and the TSV keep corpus order, and in the corpus each word’s `RRP` row comes before its `RRPVar` or `RRPvar` row. The converter’s `⬌` join sorts by codepoint instead.
- **`SSB` is dropped.** Its one row is pasta `ˈpæstə`, against the RRP row’s `ˈpɑːstə`. It is a TRAP-BATH variant tagged with an accent label instead of written with the `Æ` capital, so the TrapBath decision covers it.

With only RRP rows left, the `var` field has no information and is dropped from the artifacts. The segment mapping keeps its dual `Ɑː`/`Æ` rows, so the TrapBath decision is easy to revisit.

Every headword keeps at least one row, so the filter removes no words, only alternative pronunciations of words it keeps.

### Where the validator runs, and why it splits

[`src/qslex/validate.py`](../src/qslex/validate.py) makes one pass over the corpus but checks two different sets of rows:

- **The segment layer checks every row in the corpus.** Mapping-row coverage, quirk rules, stress overrides, token counts, raw-pattern counts and the Shavian EAR cross-check all run over every row. The `Æ` mapping row and the `hɪəˈrÆftəR` stress override are used *only* by TrapBath rows. If this layer checked only the rows the lexicon spells, the validator would report those two correct rows as unused. Checking every row also tests the tokenizer against the General American rows. It tokenizes them with no unmapped IPA and no quirk rule of their own.
- **The spelling layer checks only the corpus rows the lexicon spells.** Rules, word signs, the junior and X-letter columns, and the Manual examples are counted over those rows. Running this layer over every row was tried and rejected. The GenAm rows have `nuː` where RRP’s `njuː` already gives ·No·Ye·Ooze, so the `new` and `news` word signs would rewrite 14 GenAm rows between them. The validator requires a `manual-spellings.tsv` row for every word sign that rewrites a row, so it would then require Manual examples for spellings the lexicon does not contain.

The [added words](#words-the-corpus-lacks) are in neither set. They are checked separately, against stricter requirements.

One consequence looks like a regression but is not. Two of the Manual’s own example words, **contrast** and **example**, are spelled in this lexicon with ·Ah where the Manual writes ·At. Their expected spellings in `manual-spellings.tsv` were first derived from ReadLex’s TrapBath row, which the row policy drops. Derived from the remaining BATH row, they are ·Key·Ox·No·Tea·Roe·**Ah**·See·Tea and ·It·Gay·Zoo·**Ah**·May·Pea·Low. The note on each of those rows records the Manual’s vowel. This is the TRAP-BATH split itself, and it follows from the RRP-only row policy.

## Words the corpus lacks

ReadLex does not have every word this lexicon needs. The first missing word is the alphabet’s own name. A Quikscript lexicon with no entry for **Quikscript** has an obvious gap, and the corpus has no row for it.

[`src/qslex/data/added-words.tsv`](../src/qslex/data/added-words.tsv) lists those words, and [`src/qslex/added.py`](../src/qslex/added.py) loads it. A row has the same fields as a corpus row: `word`, `pos`, `ipa`, `shavian`, `freq`. The build appends the added rows after the row policy has run and spells them with the same `convert()`. The spelling code does not distinguish them from corpus rows, so an added word is either spelled by Read’s rules or left out of the lexicon.

Two fields are specific to this table. `source` says where the word comes from, following the requirement in [`shavian-divergences.tsv`](../src/qslex/data/shavian-divergences.tsv) that a hand-written row cites an authority. `qs` is the expected spelling, not an input. The build never reads it, and the validator fails if the rules stop producing it. [`manual-spellings.tsv`](../src/qslex/data/manual-spellings.tsv) works the same way.

The table’s rows fall into seven groups:

- Six rows are the alphabet’s name.
- Eight rows are three products of one family, of which the corpus has a single row.
- Four rows are two compounds whose parts the corpus spells.
- Nine rows are a verb, its inflections and its noun, whose parts the corpus spells.
- Four rows are an Italian loan, under its two plurals and its Italian singular.
- Three rows are an adjective with its comparative and superlative, where the corpus has the noun and verb.
- Three rows are a trade name, its plural and its possessive, whose parts the corpus spells.

| word | pos | ipa | qs |
| --- | --- | --- | --- |
| quikscript | `NP0` | ˈkwɪkskrɪpt | ·Key·Way·It·Key·See·Key·Roe·It·Pea·Tea |
| quikscript | `AJ0` | ˈkwɪkskrɪpt | ·Key·Way·It·Key·See·Key·Roe·It·Pea·Tea |
| quikscript's | `NP0+POS` | ˈkwɪkskrɪpts | ·Key·Way·It·Key·See·Key·Roe·It·Pea·Tea·See |
| quickscript | `NP0` | ˈkwɪkskrɪpt | ·Key·Way·It·Key·See·Key·Roe·It·Pea·Tea |
| quickscript | `AJ0` | ˈkwɪkskrɪpt | ·Key·Way·It·Key·See·Key·Roe·It·Pea·Tea |
| quickscript's | `NP0+POS` | ˈkwɪkskrɪpts | ·Key·Way·It·Key·See·Key·Roe·It·Pea·Tea·See |
| ipad | `NP0` | ˈaɪpæd | ·I·Pea·At·Day |
| ipads | `NN2` | ˈaɪpædz | ·I·Pea·At·Day·Zoo |
| ipad's | `NP0+POS` | ˈaɪpædz | ·I·Pea·At·Day·Zoo |
| iphone | `NP0` | ˈaɪfəʊn | ·I·Fee·Owe·No |
| iphones | `NN2` | ˈaɪfəʊnz | ·I·Fee·Owe·No·Zoo |
| iphone's | `NP0+POS` | ˈaɪfəʊnz | ·I·Fee·Owe·No·Zoo |
| ipods | `NN2` | ˈaɪpɒdz | ·I·Pea·Ox·Day·Zoo |
| ipod's | `NP0+POS` | ˈaɪpɒdz | ·I·Pea·Ox·Day·Zoo |
| eggnog | `NN1` | ˈeɡnɒɡ | ·Et·Gay·No·Ox·Gay |
| eggnogs | `NN2` | ˈeɡnɒɡz | ·Et·Gay·No·Ox·Gay·Zoo |
| ligate | `VVI` | laɪˈɡeɪt | ·Low·I·Gay·Eight·Tea |
| ligate | `VVB` | laɪˈɡeɪt | ·Low·I·Gay·Eight·Tea |
| ligates | `VVZ` | laɪˈɡeɪts | ·Low·I·Gay·Eight·Tea·See |
| ligated | `VVN` | laɪˈɡeɪtƏd | ·Low·I·Gay·Eight·Tea·Day |
| ligated | `VVD` | laɪˈɡeɪtƏd | ·Low·I·Gay·Eight·Tea·Day |
| ligated | `AJ0` | laɪˈɡeɪtƏd | ·Low·I·Gay·Eight·Tea·Day |
| ligating | `VVG` | laɪˈɡeɪtɪŋ | ·Low·I·Gay·Eight·Tea·-ing |
| ligating | `AJ0` | laɪˈɡeɪtɪŋ | ·Low·I·Gay·Eight·Tea·-ing |
| ligation | `NN1` | laɪˈɡeɪʃən | ·Low·I·Gay·Eight·She·No |
| blueberry | `NN1` | ˈbluːbəri | ·Bay·Low·Ooze·Bay·Utter·Roe·It |
| blueberries | `NN2` | ˈbluːbəriz | ·Bay·Low·Ooze·Bay·Utter·Roe·It·Zoo |
| cannoli | `NN1` | kəˈnəʊli | ·Key·Utter·No·Owe·Low·It |
| cannoli | `NN2` | kəˈnəʊli | ·Key·Utter·No·Owe·Low·It |
| cannolis | `NN2` | kəˈnəʊliz | ·Key·Utter·No·Owe·Low·It·Zoo |
| cannolo | `NN1` | kəˈnəʊləʊ | ·Key·Utter·No·Owe·Low·Owe |
| crispy | `AJ0` | ˈkrɪspi | ·Key·Roe·It·See·Pea·It |
| crispier | `AJC` | ˈkrɪspɪəR | ·Key·Roe·It·See·Pea·It·Utter·Roe |
| crispiest | `AJS` | ˈkrɪspiəst | ·Key·Roe·It·See·Pea·It·Et·See·Tea |
| ziploc | `NP0` | ˈzɪplɒk | ·Zoo·It·Pea·Low·Ox·Key |
| ziplocs | `NN2` | ˈzɪplɒks | ·Zoo·It·Pea·Low·Ox·Key·See |
| ziploc's | `NP0+POS` | ˈzɪplɒks | ·Zoo·It·Pea·Low·Ox·Key·See |

Both spellings of the name are included because both are used. The Manual writes **Quickscript** throughout: “even writers of Junior Quickscript should soon contract to single letters” ([p.12](https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#junior-contractions)). [quikscript.net](https://www.quikscript.net/) and this repository write **Quikscript**. They are one word, and they share one Quikscript spelling.

No field in the table is invented. For the name’s rows, each field follows the corpus:

- **The Latin is lowercase**, as in every corpus row, including `unicode` and `shaw`.
- **The IPA is upstream’s own.** It joins `quick` and `script` the way upstream joins them for quicksand `ˈkwɪksænd` and quickstep `ˈkwɪkstep`.
- **The Shavian is joined the same way.** The corpus spells quick 𐑒𐑢𐑦𐑒 and script 𐑕𐑒𐑮𐑦𐑐𐑑, and the compound is their concatenation, so the row makes no claim of its own about Shavian spelling.
- **`freq` is 0**, the value the corpus gives a word outside its frequency data: `unicode` `NP0`, `esperanto` `NP0`.
- **`NP0`, `AJ0` and `NP0+POS`** are the tags ReadLex gives a named writing system and its possessive. `esperanto` has `NP0` and `AJ0` rows, and `shavian` has an `AJ0` row. `guy's`, `lloyd's` and `parkinson's` have `NP0+POS` rows. There is no plural row, because the name is not used in the plural.

**The possessive needs its own row.** The transliterator already builds the possessive from the bare word. It writes `'s` [solid, with the apostrophe dropped](latin2qs.md#apostrophes), and voices it by the class of the final letter, so it becomes ·See after voiceless ·Tea. But a spell checker accepts only strings that some column contains. Most words do not need the row, because the plural has the same spelling as the possessive and the corpus has the plural: jack's and jacks are both ·Jay·At·Key·See. The name has no plural row, so without the possessive row no entry would contain ·Key·Way·It·Key·See·Key·Roe·It·Pea·Tea·See, and the Desk would flag a word this repository uses constantly.

Both possessives are added to the [phrase list](#qs_converter_phrasestxt) automatically, because a single word containing an apostrophe never composes. That is also why upstream’s `guy's`, `lloyd's` and `parkinson's` are on the list.

**iPad and iPhone** follow the same pattern with a different source. ReadLex has `ipod` `NP0` ˈaɪpɒd 𐑲𐑐𐑪𐑛 at `freq` 0, and neither sibling. Each name takes that row’s `NP0` tag and `freq` of 0, and joins upstream’s aɪ to its pad pæd 𐑐𐑨𐑛 or phone fəʊn 𐑓𐑴𐑯, as `ipod` joins it to pod. The corpus has only the bare name, so `ipod` also gets the plural and possessive rows its siblings have. The Latin is lowercase, as `ipod` is. The row does not add the namer dot. The transliterator adds it when spaCy marks the word as the start of a named entity ([The namer dot](latin2qs.md#the-namer-dot)). The plural takes `NN2`, the tag ReadLex gives the plural of a trade name (`biros`, `hoovers`, `macs`). The possessive takes `NP0+POS`, as the name’s possessive does. The plural and the possessive share one spelling, because `'s` voices to ·Zoo after ·Day or ·No as the plural does. So here the possessive row adds no new spelling to the dictionary. It adds an entry with an apostrophe to the phrase list.

**Eggnog** is an ordinary compound that ReadLex does not have. It follows upstream’s `eggplant` `NN1` ˈeɡplⱭːnt 𐑧𐑜𐑐𐑤𐑭𐑯𐑑: unhyphenated and stressed on the first element. It joins upstream’s egg eɡ 𐑧𐑜 to nog, which upstream’s `noggin` ˈnɒɡɪn 𐑯𐑪𐑜𐑦𐑯 and `snog` snɒɡ 𐑕𐑯𐑪𐑜 already spell ·No·Ox·Gay. The plural takes the `NN2` tag of `eggplants` and the voiced ending of `eggs` eɡz 𐑧𐑜𐑟, ·Zoo after ·Gay. No possessive row is needed, because the plural has the same spelling.

**Ligate** is a verb that ReadLex does not have, though it has `ligature`. It follows upstream’s `negate` `VVI` nɪˈɡeɪt 𐑯𐑦𐑜𐑱𐑑, which is stressed on the -gate, as `migrate` maɪˈɡreɪt 𐑥𐑲𐑜𐑮𐑱𐑑 and `dilate` daɪˈleɪt 𐑛𐑲𐑤𐑱𐑑 are. It joins upstream’s lie laɪ 𐑤𐑲 to its gate ɡeɪt 𐑜𐑱𐑑. It has both a `VVI` and a `VVB` row, because ReadLex gives every such verb both. The third-person singular takes `VVZ` and the voiceless ending of `negates` nɪˈɡeɪts 𐑯𐑦𐑜𐑱𐑑𐑕, ·See after ·Tea. The inflections and the noun follow the same family row for row:

- `ligated` takes the `VVN`, `VVD` and `AJ0` rows and the tagged -Əd ending of `negated` nɪˈɡeɪtƏd 𐑯𐑦𐑜𐑱𐑑𐑩𐑛. The Ə marks the vowel the Manual says must be spoken between T and D (its TD pair), which Quikscript does not write.
- `ligating` takes the `VVG` and `AJ0` rows of `negating` nɪˈɡeɪtɪŋ 𐑯𐑦𐑜𐑱𐑑𐑦𐑙.
- `ligation` takes the `NN1` row and the -ʃən ending of `negation` nɪˈɡeɪʃən 𐑯𐑦𐑜𐑱𐑖𐑩𐑯 and `dilation` daɪˈleɪʃən 𐑛𐑲𐑤𐑱𐑖𐑩𐑯.

**Blueberry** is built like eggnog, from a different family. It follows upstream’s `blackberry` `NN1` ˈblækbəri 𐑚𐑤𐑨𐑒𐑚𐑼𐑦, and its `cranberry`, `raspberry` and `strawberry`, all stressed on the first element. It joins upstream’s blue bluː 𐑚𐑤𐑵 to the -berry those rows share. The plural takes `NN2` and the voiced ending of `blackberries` ˈblækbəriz 𐑚𐑤𐑨𐑒𐑚𐑼𐑦𐑟. There is no possessive row, because ReadLex has no possessive for any berry.

**Cannoli** is an Italian loan that the corpus does not have. It follows ReadLex’s rows for similar loans. The English singular follows upstream’s `ravioli` `NN1` ˌrævɪˈəʊli 𐑮𐑨𐑝𐑦𐑴𐑤𐑦, an Italian plural that English uses as a singular. It joins the unstressed kə of `canal` kəˈnæl 𐑒𐑩𐑯𐑨𐑤 to ravioli’s -oli. The word has a second row as `NN2`, because it is also its own plural, as ReadLex does for `graffiti` and `paparazzi` beside their -o singulars. `cannolis` is the English plural, following `raviolis` ˌrævɪˈəʊliz 𐑮𐑨𐑝𐑦𐑴𐑤𐑦𐑟. **Cannolo**, the Italian singular, follows the `NN1` rows of `graffito` ɡrəˈfiːtəʊ 𐑜𐑮𐑩𐑓𐑰𐑑𐑴 and `paparazzo`. Its final -o is the əʊ of `polo` ˈpəʊləʊ 𐑐𐑴𐑤𐑴.

**Crispy** is missing although the corpus has the word it comes from. ReadLex has `crisp` krɪsp 𐑒𐑮𐑦𐑕𐑐 as adjective, noun and verb, and `crispness`, but not the -y adjective. It follows the `AJ0` rows of `wispy` ˈwɪspi 𐑢𐑦𐑕𐑐𐑦 and `frisky` ˈfrɪski 𐑓𐑮𐑦𐑕𐑒𐑦: upstream’s crisp plus the terminal -y those rows end in, which the rules write ·It. Its comparative and superlative follow `risky` ˈrɪski 𐑮𐑦𐑕𐑒𐑦. Upstream’s `riskier` ˈrɪskɪəR 𐑮𐑦𐑕𐑒𐑦𐑼 and `riskiest` ˈrɪskiəst 𐑮𐑦𐑕𐑒𐑦𐑩𐑕𐑑 give the `AJC` and `AJS` rows their endings. ReadLex writes the comparative’s vowel ɪə and the superlative’s iə, and the rules write the -est terminal ·Et. The corpus’s own `crisper` and `crispest` are unchanged. They are the comparative and superlative of crisp.

**Ziploc** is a trade name that follows the iPad pattern, spelled from parts the corpus has. It follows upstream’s `ipod` `NP0` ˈaɪpɒd 𐑲𐑐𐑪𐑛 row at `freq` 0. It joins ReadLex’s zip zɪp 𐑟𐑦𐑐 to its lock lɒk 𐑤𐑪𐑒, stressed on the first element as upstream’s `zip code` ˈzɪp kəʊd is. So the -loc of the trademark is spelled as the lock it is pronounced as. The plural takes `NN2` and the voiceless ending of `locks` lɒks 𐑤𐑪𐑒𐑕, ·See after ·Key. The possessive takes `NP0+POS` and has the same spelling, so like `ipad's` it adds an entry with an apostrophe to the phrase list. As with iPad, the transliterator adds the namer dot, not the row.

**What the validator requires of added words** is stricter than what it requires of corpus rows, because rows we wrote ourselves get no per-row tolerances. Each added row must:

- produce the `qs` it lists;
- pass every lint check;
- read back to its own IPA using only the allowed differences in [`roundtrip.EDITS`](../src/qslex/roundtrip.py);
- not be rewritten by any word sign.

These are absolute requirements, not expected counts, because the table is small. The differences in `roundtrip.EDITS` are the only exceptions, and they apply to every word, not to one row. For example, `ligated` drops the schwa of its -Əd ending because Quikscript writes every such -ted ending that way. A hand-written row cannot be required to read back without that difference. The validator also fails if ReadLex adds the word. The added row must then be removed or its reason for staying recorded, so the lexicon cannot gain a second row for the word without a check failing. Checking added words in a separate pass leaves every corpus check unchanged, so a corpus update is still compared against ReadLex alone.

## Artifact formats

### quikscript-lexicon.json

The file has five top-level keys, and `entries` is almost all of it:

```json
{
    "meta": {"version": 2, "source": {"repo": "…", "commit": "…", "sha256": "…"},
             "encoding": {"block": "U+E650–U+E67E"},
             "counts": {"headwords": 12345, "entries": 12345, "phrases": 12345, "added": 12345}},
    "letters": [{"codepoint": "U+E650", "qs": "…", "name": "Pea", "class": "consonant", "ipa": "p"}],
    "c5_to_penn": {"AJ0": "JJ", "AJC": "JJR"},
    "phrases": ["&amp;", "&gt;", "&lt;"],
    "entries": {
        "again_AV0_𐑩𐑜𐑧𐑯": [{"Latn": "again", "qs": "…", "Shaw": "𐑩𐑜𐑧𐑯", "pos": "AV0", "ipa": "əˈɡen", "freq": 12345}]
    }
}
```

With the four small keys, a consumer needs no other file:

- `letters` maps each codepoint to its letter name, class and IPA. Without a Quikscript font, QS text displays as empty boxes, and this table is what lets a consumer decode it. It lists `codepoint`, `qs`, `name`, `class` and `ipa` for all 44 letters, derived from `src/qslex/csur.py` and the segment mapping. The `name` is the letter’s example word, which is how [the CSUR proposal](https://www.quikscript.net/csur/) names the letters. The `ipa` lists every mapping token that produces the letter. It is empty for ·Excite and ·Exam, which no segment mapping produces.
- `c5_to_penn` is the tag map that the converter table’s tagged rows are keyed by.
- `phrases` is the phrase list. Part of it comes from `phrase-exceptions.tsv`, which cannot be derived from the entries.
- `meta` says which corpus commit the file came from and how many headwords, entries, phrases and added words it has.

`counts.added` is the number of entries that do not come from that corpus commit (see [Words the corpus lacks](#words-the-corpus-lacks)). It is the reason the schema is version 2. `meta.source` no longer accounts for every row, and a consumer written for version 1 should notice the change instead of receiving entries that the named commit does not contain. `added-words.tsv` lists which entries they are. This number says whether there are any.

Two of the small keys duplicate other files:

- `phrases` duplicates `qs_converter_phrases.txt`. The same call to `build.artifacts()` writes both, and `make check` rebuilds and byte-compares both.
- `c5_to_penn` duplicates `src/qslex/data/c5-to-penn.tsv`, which is a hand-edited input that the build reads. `test_the_lexicon_jsons_tag_map_equals_c5_to_penn_tsv` in `tests/test_build.py` checks that the two are equal.

`letters` appears in no other file. The lexicon JSON is the only place the alphabet is named.

Each key in `entries` is upstream’s headword key, copied verbatim, and maps to the entries under it. The key is treated as an opaque upstream identifier. It is kept so that every group can be traced to the upstream group it came from, and so that a corpus update diffs cleanly. It is *not* re-derived. Upstream’s keys do not always match the entries under them: `bevel_VVI_𐑚𐑧𐑝𐑩𐑤𐑟` heads a group whose `bevel` rows have the Shavian 𐑚𐑧𐑝𐑩𐑤. That is another reason to copy the key instead of computing one.

`Shaw` is kept. It adds little to the file, the validator’s Shavian EAR cross-check reads it, and it lets a row be compared with upstream. `var` is dropped, per the row policy. `qs_junior` and `qs_x` are **omitted unless they differ** from `qs`. This sparse encoding makes the differences easy to see and keeps diffs small.

`ipa` is the **quirk-normalized** string, not the corpus’s own, so that each row has the IPA its spelling was made from. It differs from upstream’s IPA on every row that an `ipa-quirks.tsv` rule changes. Upstream’s original is in the vendored corpus, so a diff against ReadLex should read from there.

The file has **one headword per line**, and likewise one letter and one phrase per line. `meta` and `c5_to_penn` are small, so they use ordinary four-space indentation. The file is generated, so the useful diff shows which entries changed, and each changed entry is one changed line. With one field per line, the same change would be one line inside a nine-line block. The file is also ten megabytes smaller than it was with one field per line. It is written with `ensure_ascii=False`, LF line endings and a trailing newline. Headwords are in corpus order, and the added words come last.

### quikscript-lexicon.tsv

The columns are `Latn`, `qs`, `qs_junior`, `qs_x`, `Shaw`, `pos`, `ipa`, `freq`. These are upstream’s five columns, with the Quikscript spelling in the position the Shavian spelling had and the Shavian moved to the right. Unlike upstream’s TSV, it has a header row, because eight columns, two of them usually empty, need labels.

The sparse columns are empty strings on rows where they do not differ from `qs`. The limits on them are checked. `qs_x` may differ only on a word with an `x` in it. `qs_junior` may differ only on the word-level cases [#3](https://github.com/adiabatic/quikscript-lexicon/issues/3) lists, plus the rows whose linking vowel [`terminal-nt`](orthographic-rules.md#decisions) elides in senior only.

The TSV **is deduplicated**. Two headwords can list the same inflected form (ax and axe both list axed). Flattening them without removing the duplicate is upstream’s #124 bug.

### The converter table

The converter table is not an artifact. The build computes it to derive the phrase list, and the transliterator computes it again from the lexicon JSON when it starts. Neither writes it to a file. This repository still specifies its format, because the transliterator from [#6](https://github.com/adiabatic/quikscript-lexicon/issues/6) is a port of `latin2shaw.py`, and the port depends on using upstream’s format.

It maps each Latin word to a list of rows:

```json
"absent": [
    {"qs": "…", "tag": "JJ"},
    {"qs": "…", "tag": "NN"},
    {"qs": "…", "tag": "VB"},
    {"qs": "…", "tag": "VBP"},
    {"qs": "…⬌…", "tag": "0"}
]
```

The format is upstream’s. `latin2shaw.py` looks a token up by `token.lower_`, walks the rows, and takes the first row whose `tag` matches spaCy’s Penn `token.tag_`, with `"0"` as the fallback for any tag. Using the same format lets the transliterator port that lookup unchanged.

- **Tagged rows are written only where a tag can choose between spellings.** The word needs more than one spelling and more than one Penn tag.
- **The `0` row is always present and always last.** Its `qs` is the word’s distinct spellings, sorted by codepoint and joined with `⬌`. `⬌` is a “pick one” marker. The table does not choose between the alternatives. `latin2shaw.py` writes a `⬌`-joined row out as is, and for now this repository’s transliterator does the same.
- **`qs_junior` and `qs_x` are included in each row**, sparse as elsewhere. Their alternatives are in the same order as those in `qs`, so the three columns line up position by position.

The C5-to-Penn table this needs is `src/qslex/data/c5-to-penn.tsv`. It was not guessed. Reimplementing upstream’s generator and reproducing `readlex_converter.json` **byte for byte** (9,565,065 bytes) determines a unique Penn tag for every C5 tag that file can distinguish. The rest are marked `standard`, and their notes say why. Either upstream’s file cannot separate them (`VVI`/`VVB` and `VVD`/`VVN` have identical spellings for every key), or upstream never uses them. Only heteronyms and the tagged rows of `contractions.tsv` (`AJ0`, `AV0`, `CJT`) use the table, so the corpus’s other C5 tags need no Penn equivalent and have none. If a corpus update makes one of them necessary, the build raises an error instead of guessing.

Two differences from upstream’s file:

- **Row order puts `NNP` first**, then the rest alphabetically. Upstream writes `NN` before `NNP`. Its consumer checks each row in turn and accepts the `NN` row as a fallback for `NNP`, so it takes the `NN` row before it reaches the exact `NNP` row. That makes the proper-noun spelling unreachable for every key whose `NN` row is spelled differently, among them derby, reading and slough. Writing `NNP` first fixes this in the data, with no change needed in any consumer.
- **The row set follows this repository’s row policy.** Upstream’s converter keeps only rows with `var == "RRP"`, so it drops the `RRPVar`/`RRPvar` rows that its own TSV also drops. This repository keeps them, so a few keys have one more alternative than they do in upstream’s file.

Quikscript also has heteronyms that Shavian does not. `that` has one spelling in ReadLex and two here: ·They·Tea for the conjunction and ·They·At·Tea for the demonstrative. That is why `CJT` and `DT0` need Penn equivalents that upstream’s file never required.

**Rebuilding it.** Every input is in the lexicon JSON. The five fields `converter()` reads are in `entries`, and the tag map is `c5_to_penn`. No other file is opened.

```python
import json
from qslex.converter import TagMap, converter

lexicon_json = json.load(open("lexicon/quikscript-lexicon.json", encoding="utf-8"))
rows = converter(
    (
        (e["Latn"], e["pos"], e["qs"], e.get("qs_junior", ""), e.get("qs_x", ""))
        for group in lexicon_json["entries"].values()
        for e in group
    ),
    {
        c5: TagMap(c5, penn, "upstream", "")
        for c5, penn in lexicon_json["c5_to_penn"].items()
    },
)
```

Written out with `json.dumps(rows, ensure_ascii=False, indent=4)` and a trailing newline, that gives the same bytes the build used to write as `qs_converter.json`. `test_the_converter_table_can_be_rebuilt_from_the_lexicon_json` in `tests/test_build.py` checks that this rebuild equals the table the build computes in memory. It fails if the lexicon JSON stops containing what the rebuild needs.

### qs_converter_phrases.txt

These are the entries a tokenizer must match as one unit before it splits the text. Splitting them first would spell their pieces and give a different spelling.

**Derived here, not copied.** Upstream ships this list twice, as `readlex_converter_phrases.json` and `.csv`, and the two differ by 17 lines. The `.csv` follows the corpus. The `.json` has not changed since June 2025, and it is the one `latin2shaw.py` opens. Neither file is JSON or CSV; both are CRLF plain text. So “reuse the phrase list” has no single meaning, and this repository derives the list from its own spellings and gives it a `.txt` extension.

An entry is listed by a compositionality test, not a character test. It is listed when any of these holds:

- spelling its pieces separately and joining them does not give the entry’s own spelling;
- a piece is not in the lexicon;
- it is a single word that contains an apostrophe, which a tokenizer splits at.

`src/qslex/data/phrase-exceptions.tsv` adds more entries: HTML entities, which are not lexicon entries, and words that spaCy’s tokenizer splits, which no property of the lexicon shows.

The list is longer than upstream’s. Quikscript’s terminal and prefix conventions depend more on context than Shavian’s spelling does, so hundreds of compounds fail to compose in Quikscript where their Shavian spellings compose. The list was longer still, at 2,171 entries, until the rules were applied to each element of a compound ([#9](https://github.com/adiabatic/quikscript-lexicon/issues/9)). 571 of those entries were listed only because an element was spelled one way alone and another way in the compound. The list is regenerated from the spellings either way, so it always matches them.

In some places it is *shorter* than upstream’s. at-home, lean-to, set-to, aged care and school-aged compose in Quikscript, because a standard word-outline gives one spelling to a stressed/unstressed pair that Shavian spells two ways.

### en-Qaas.dic / en-Qaas.aff

This is a [Hunspell](https://github.com/hunspell/hunspell) dictionary, named for [the language tag](conformance.md#the-language-tag) that Quikscript text is written under. Point a checker at it with `hunspell -i utf-8 -d lexicon/en-Qaas`. The `-i` is required. hunspell decodes its input in the locale’s encoding, and every Quikscript letter is outside ASCII. Under `LC_ALL=C`, hunspell skips a line of Quikscript silently: it accepts nothing and flags nothing. This is the same failure that `WORDCHARS` fixes from the other side. With no locale set at all, hunspell gets an error from iconv and prints garbled tokens. Naming the input encoding works in every locale.

The `.dic` lists **every distinct spelling in any of the three columns**, one per line, sorted by codepoint, with the count on the first line as the format requires. All three columns are included, so the dictionary accepts Senior, Junior and the X-letter form. A spelling that several rows share is listed once.

Two decisions shape it:

- **Spaced entries are dropped.** A tokenizer splits at a space before it consults a dictionary, so hunspell never receives such a string, and a listed one could never match. Hyphenated entries are kept whole, and hunspell can match them because of `WORDCHARS` (below).
- **No word has an affix flag.** ReadLex lists every inflected form as its own row, so affix rules would add nothing the word list does not already have, and a flag with no rule behind it could only cause errors. The `.aff` has no `PFX` or `SFX` at all.

The `.aff` has four directives, all of them derived:

- **`SET UTF-8`**, because the spellings are UTF-8.
- **`WORDCHARS`**, all 44 letters and the hyphen. Without it, hunspell’s own tokenizer treats PUA codepoints as punctuation and skips every Quikscript word silently, neither accepting nor flagging it.
  - The hyphen is included, unlike in en_US. Hundreds of the hyphenated entries have a non-empty piece that is not itself an entry (papier-mache, bob-omb, terra-cotta). Without the hyphen, the tokenizer splits them and flags the pieces. Some entries with a hyphen at one edge are among them, such as neo- and ultra-.
  - Including it loses nothing, because hunspell’s default `BREAK` still checks the pieces of a hyphenated word that the dictionary does not list whole.
  - The downside is that a bare run of hyphens becomes a token of its own and is flagged: a spaced dash, `--` or `---` between spaces, or the `- ` that opens a Markdown-style bullet. A run of hyphens inside a word is still accepted.
  - A known problem, not fixed: the default `BREAK` accepts any hyphenated join of two entries, whether or not the join is a word. The `.dic` has single-letter entries, so this accepts even ·Zoo-·Vie.
- **`TRY`**, the 44 letters ordered by how often each occurs across the word list, most frequent first, with ties broken by codepoint. hunspell tries TRY letters in order when it substitutes one letter for another, so the order is computed from letter frequency in the word list.
- **`REP`**, which maps ·Excite to ·Key·See and ·Exam to ·Gay·Zoo, and each pair back to its X-letter. Both directions are needed, because the letters around an X-letter change with it. expect is ·It·Key·See·Pea·Et·Key·Tea in `qs` and ·Et·Excite·Pea·Et·Key·Tea in `qs_x`, so neither form is a single-letter edit from the other. Without the table, the ngram suggester still finds the other form about half the time, but low in the list and almost never first. With it, writing either an X-letter or the pair it stands for gets exactly one suggestion, and it is the right form. A `MAP` table over the same two pairs was tried and removed. It works on its own, but beside `REP` it changed no suggestion.

**The apostrophe is not in `WORDCHARS`.** No spelling column contains an apostrophe, so no `.dic` entry can: the corpus spells they'll solid, ·They·Eight·Low. The transliterator does write one. [`src/qslex/latin2qs.py`](../src/qslex/latin2qs.py) inserts U+2019 before a kept clitic’s letters at either grade, giving the Manual’s ·They·Eight’·Low ([Apostrophes](latin2qs.md#apostrophes)). With this `.aff`, hunspell splits at it, accepts the host word, and flags the clitic ·Low alone. Putting ’ in `WORDCHARS` would be worse. hunspell would then look up the whole token, no entry has an apostrophe, and the default `BREAK` does not break at one, so it would flag the whole word instead of just the clitic. A dictionary generated from the columns cannot accept transliterator output that contains clitics, and this setup at least still accepts the host word.

The Desk page and `editor/server/payload.json` (the language server’s data) use the same word set, `TRY` order and `REP` table. The only addition is the §III contractions that their shared checker adds, which no column contains and so no `.dic` entry can. `qslex.checker_data` re-derives the word set and the `TRY` order from the lexicon JSON and checks them against the `.dic` and `.aff` on every build of the page and of the payload. `tests/test_desk.py` and `tests/test_payload.py` check the `REP` table against the `.aff`. The payload also contains two lookup maps for the server’s hover and completions, derived from the same lexicon JSON rows. `latin_by_spelling` maps each accepted spelling to the Latin word, tag and column of each entry with that spelling. `spellings_by_latin` maps each lowercased Latin word to its entries’ tags, frequencies and three spelling columns.

## Regenerating

```sh
make artifacts     # rewrite lexicon/
make check         # lint, type checks, tests, the validator, and a rebuild compared with every committed artifact
```

The last step of `make check`, `make freshness`, rebuilds every artifact in memory and fails if a file on disk differs, so an out-of-date `lexicon/` does not pass. Together with a clean `git diff` after `make artifacts`, that is the regeneration check: the same checkout produces the same bytes every time.

To update the corpus, replace `data/readlex/readlex.json`. Update the commit, digest, headword count and entry count in [`data/readlex/README.md`](../data/readlex/README.md) and in `src/qslex/readlex.py` (`CORPUS_COMMIT`, `CORPUS_SHA256`, `CORPUS_HEADWORDS`, `CORPUS_ROWS`). Then run `make check` and fix every check that fails. Several will. The loader checks the file’s SHA-256, so replacing the file fails the build until the recorded SHA-256 is updated to match.

Most of the checks that fail report the value they expected: the headword and row counts in `src/qslex/readlex.py`, the expected counts in `src/qslex/validate.py`, the row counts in `src/qslex/data/var-tags.tsv`, and the artifacts themselves. Prose has no such check. That is why this file, the [README](../README.md) and [`lexicon/README.md`](../lexicon/README.md) give no counts for the lexicon. See [Artifacts](#artifacts) for where each count is checked instead. Two kinds of count are still written by hand. The provenance table in [`data/readlex/README.md`](../data/readlex/README.md) describes the pinned snapshot, so it changes only when the pin does. The other specs also give some counts over the corpus.

## Upstream files not built

**`readlex.dict` and `addendum.dict`.** Upstream ships these for [Dave Coffin’s Dechifro scripts](https://www.dechifro.org/shavian/), which render Shavian. Not built: nothing in the Quikscript ecosystem reads this format, and its `^prefix`/`$suffix` affix rules encode Shavian’s affixes, not Read’s. If a Quikscript tool ever needs it, it can be derived from the JSON like the other artifacts.

**`readlex_search.json`.** A 29 MB file used by [readlex.pythonanywhere.com](https://readlex.pythonanywhere.com/). Not built; it would be needed only by a Quikscript search site.
