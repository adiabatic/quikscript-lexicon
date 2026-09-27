# The canonical IPA → Quikscript segment mapping

This is the spec for [`src/qslex/data/ipa-to-qs.tsv`](../src/qslex/data/ipa-to-qs.tsv). The table maps every symbol that appears in ReadLex’s IPA column to Quikscript letters, encoded as PUA codepoints U+E650–U+E67E per the [quikscript.net CSUR proposal][csur]. It is a total function: every symbol in the column has a mapping.

Authority links go to the [AMS Manual transcription][manual]. Everything below was checked against the PUA text of that document, and spellings quoted as letter names were copied from it codepoint by codepoint.

## Artifacts

- `src/qslex/data/ipa-to-qs.tsv` is the mapping. Its columns are:
  - `ipa`: the token.
  - `condition`: empty, `stressed`/`unstressed`, or `pre-r`/`no-r`.
  - `qs`: the PUA string.
  - `codepoints`: `U+XXXX …`.
  - `letters`: `·Name·Name`.
  - `kind` and `example`.
  - `authority`: an anchor slug in the Manual.
- `src/qslex/data/ipa-quirks.tsv` normalizes upstream data quirks before tokenization. Each quirk is an error in ReadLex that should be fixed upstream. The rules apply from top to bottom. Their scopes are `row` (exact string), `sub` (literal substring) and `regex`. Each rule lists the words it may touch, and the validator checks it against that list.
- `src/qslex/data/ipa-overrides.tsv` holds per-word stress overrides for the words where the mechanical ɪə rule contradicts the evidence. See [Where the mechanical rule breaks](#where-the-mechanical-rule-breaks-and-the-override-file).
- `src/qslex/data/shavian-divergences.tsv` lists the words where the mapping’s ɪə result contradicts ReadLex’s Shavian column. Every row names its authority, and the loader rejects a row without one.
- `src/qslex/` contains the mapping loader, the tokenizer and the validator. The loader checks that each row’s letter names, codepoints and PUA string agree with each other and with the CSUR table.
- `data/readlex/` is the ReadLex corpus, vendored at a pinned commit with its MIT license and SHA-256 ([provenance](../data/readlex/README.md)). The mapping tables are inside the package so that an installed wheel can load them. The corpus is outside it, because code that transcribes IPA does not need megabytes of ReadLex.

Run the checks:

```
make check
```

The validator tokenizes every IPA string in the corpus. It fails if any of these is true:

- Some IPA matches no mapping token (the `unmapped IPA` count is not zero).
- A mapping row is never used.
- A quirk rule matches nothing, touches a word it does not list, or lists a word it no longer touches.
- A stress override is never used, touches a word it does not list, or changes nothing.
- A row’s stressed EAR count differs from the Shavian column’s 𐑽 count, and the row has no entry in `shavian-divergences.tsv`.
- The number of `əʊ` in the normalized text differs from the number of ·Owe tokens.
- A token count differs from its expected value in `EXPECTED_TOKEN_COUNTS`. The counted tokens include `R`, `Ə`, `I`, `Æ`, `Ɑː`, `ʍ`, the word signs, weak `u` and the affricates.
- The raw corpus contains a schwa-less `ɪR`, `aɪR` or `aʊR` (`FORBIDDEN_RAW_PATTERNS`).

The expected values are in [`src/qslex/validate.py`](../src/qslex/validate.py) and nowhere else. `load_rows` in [`src/qslex/readlex.py`](../src/qslex/readlex.py) checks the corpus SHA-256 before the build or the validator reads a row, so these counts change only when someone updates the corpus or edits the mapping tables.

## Tokenizer contract

Tokens are matched greedily, longest first, over the quirk-normalized string. Three rules apply, and all are required:

- **A stress mark ends a vowel token.** coyote `kaɪˈəʊti` must parse as `aɪ·ˈ·əʊ`, never as an `aɪə` triphthong across the mark. This follows from matching contiguous characters, since no vowel token contains a stress mark.
- **A stress mark does not break vowel+r adjacency.** thereafter `ðeəˈrÆftəR` still counts its `eə` as pre-r (·Eight). The `pre-r`/`no-r` lookahead skips stress marks before it tests for `r` or `R`.
- **A token that ends in a schwa does not match when `ʊ` follows.** In bio `ˈbaɪəʊ`, diode, flyover and heliograph, the `ə` belongs to a following GOAT vowel `əʊ`. So `aɪə` and `ɪə` decline to match, and the split is `aɪ`+`əʊ` → ·I·Owe. The Shavian column agrees: 𐑲𐑴. The validator’s əʊ-conservation check tests this: every `əʊ` in the normalized text must come out as an ·Owe token. The corpus has no `eəʊ`, `ʊəʊ` or `aʊəʊ`, so this rule applies only to words like bio.

Chunks are the spans of an entry separated by `-`, space or `+`. Stress conditioning never crosses a chunk boundary. It does read which separator began the chunk. See the rider on rule 3 below. Token matching cannot cross a separator either, so a hiatus sequence such as angrier `ˈæŋɡrɪ+əR` does not fuse into a false `ɪə`. Stress marks map to no letters.

The `-` and space separators are orthographic and pass through as themselves. `+` is ReadLex’s marker for hiatus and has no orthographic meaning. Its row has `kind=hiatus` and produces nothing, so angrier is ·At·-ing·Gay·Roe·It·Utter·Roe, with no `+`. The mapping loader rejects a hiatus row that names any letter, and `tests/test_build.py` rejects a `+` in any Quikscript column the build writes.

## Consonants and simple vowels

Every consonant maps to one letter: p→·Pea b→·Bay t→·Tea d→·Day k→·Key ɡ→·Gay θ→·Thaw ð→·They f→·Fee v→·Vie s→·See z→·Zoo ʃ→·She ʒ→·J’ai tʃ→·Cheer dʒ→·Jay j→·Ye w→·Way h→·He m→·May n→·No ŋ→·-ing l→·Low r→·Roe. There are also ʍ→·Why, x→·Loch (koch) and ɬ→·Llan (llanfair, after a quirk rule normalizes upstream `L`). ReadLex’s IPA column keeps the wh distinction that ʍ encodes, and that is why this project spells from that column.

Simple vowels: ɪ→·It iː→·Eat e→·Et eɪ→·Eight æ→·At aɪ→·I ɑː→·Ah ɒ→·Ox ɔː→·Awe ɔɪ→·Oy aʊ→·Out əʊ→·Owe ʊ→·Foot uː→·Ooze. ə, ʌ and ɜː all map to ·Utter. [§ Vowels + R][vr] says letter 36 “serves both for Hut and for Hurt, for Us, Upon and Urge”, and the Manual spells hut ·He·Utter·Tea and hurt ·He·Utter·Roe·Tea.

## Non-obvious rows, with one example each

| Row                                 | Example           | Result                       | Authority                                                                              |
| ----------------------------------- | ----------------- | ---------------------------- | -------------------------------------------------------------------------------------- |
| `R` → ·Roe, always                  | baker `ˈbeɪkəR`   | ·Bay·Eight·Key·Utter·Roe     | [§ Spell all R's][rs]; [§ Vowels + R][vr] (-er = ·Utter·Roe)                           |
| happY `i` → ·It                     | money, coffee     | final ·It                    | [§ Terminal -y][y]                                                                     |
| weak `u` → ·Ooze                    | visual `ˈvɪʒuəl`  | ·Vie·It·J’ai·Ooze·Utter·Low  | [§ -al, -el, -le, -il][al]; the decision below explains the ·J’ai                      |
| `juː` → ·Ye + ·Ooze (compositional) | few `fjuː`        | ·Fee·Ye·Ooze                 | [alphabet chart][chart] (“Ewe, Use, Few”)                                              |
| `eə` pre-r → ·Eight                 | there `ðeəR`      | ·They·Eight·Roe              | [alphabet chart][chart] (“Pair, Dare, There”); common-words there = ·They·Eight·Roe    |
| `eə` no-r → ·Et·Utter               | yeah `ˈjeə`       | ·Ye·Et·Utter                 | occurs only in yeah and elo; follows yeah’s Shavian 𐑘𐑧𐑩 (see the note below)           |
| `ʊə` → ·Ooze·Utter                  | moor `mʊəR`       | ·May·Ooze·Utter·Roe          | [§II][sec2] join table: moor                                                           |
| `ɪə` stressed → ·Eat·Utter          | career `kəˈrɪəR`  | ·Key·Utter·Roe·Eat·Utter·Roe | [§ Terminal -ier, -ior][ier]; [§ -ia, -ea][ia] (Korea, idea); §II (dear, mere, fear)   |
| `ɪə` unstressed → ·It·Utter         | carrier `ˈkærɪəR` | ·Key·At·Roe·It·Utter·Roe     | [§ Terminal -ier, -ior][ier] (happier, senior, junior); [§ -ia, -ea][ia] (India, area) |
| `aɪə` pre-r → ·I (schwa absorbed)   | mire `ˈmaɪəR`     | ·May·I·Roe                   | [§II][sec2]: mire = ·May·I·Roe                                                         |
| `aʊə` pre-r → ·Out (schwa absorbed) | our `ˈaʊəR`       | ·Out·Roe                     | [§II][sec2] (sour); [§ Common words][common]: our = ·Out·Roe                           |
| `aɪə` no-r → ·I·Utter               | science `ˈsaɪəns` | ·See·I·Utter·No·See          | decision below                                                                         |
| `aʊə` no-r → ·Out·Utter             | bowel `ˈbaʊəl`    | ·Bay·Out·Utter·Low           | decision below                                                                         |

The pre-r rows are conditioned on r, not only on capital `R`. An intervocalic lowercase r (firing, dowry) triggers the same absorption, so the token-level pre-r counts are higher than the number of capital-R rows.

ReadLex writes some -ia words with happY `i` + `ə` (Austria `ˈɒstriə`) and others with `ɪə` (India `ˈɪndɪə`), as it writes happier. Both produce ·It·Utter, which matches the Manual’s -ia rule.

The `eə` no-r row occurs only in yeah and elo. yeah’s Shavian 𐑘𐑧𐑩 supports ·Et·Utter. elo’s Shavian is 𐑺𐑤𐑴 (AIR), which contradicts its own row’s IPA, so it is no evidence for the mapping. The row therefore rests on yeah alone. elo is an upstream data defect that should be fixed at source. The validator has an expected count for this row, so an upstream fix will make it fail.

## The stress rule for ɪə

The rule is mechanical. It works within one chunk and scans left from the `ɪə`:

1. If it reaches a stress mark (ˈ or ˌ) before any vowel, the ɪə is **stressed**. Only consonants lie between the mark and the ɪə syllable: appear `əˈpɪəR`, career `kəˈrɪəR`.
2. If it reaches a vowel first, the ɪə is **unstressed**: happier `ˈhæpɪəR`, senior, the second ɪə of period.
3. If it reaches the start of the chunk, the ɪə is **stressed** when the chunk has no stress mark at all, and unstressed otherwise. This covers the monosyllables the Manual cites (dear `dɪəR`, here, year), because ReadLex writes no ˈ on monosyllables. It covers compound elements without a mark in the same way: anti-hero `ˈænti-hɪərəʊ`, world-weary and operating-theatre keep the ·Eat·Utter of their standalone forms. The Shavian column agrees for two of those three, hero 𐑣𐑽 and weary 𐑢𐑽, but **not** for theatre, which is 𐑔𐑾. Shavian writes 𐑾 for every non-rhotic ɪə whatever its stress, so for a non-rhotic ɪə it is no evidence either way.

Rule 3 assumes that the chunk is a word in its own right, which is why a chunk without a mark may keep its standalone stress. A `+` marks hiatus, not a word boundary. So the chunk after a `+` is treated as stressed only if it contains a stressable vowel. A chunk whose only vowel is a schwa takes the unstressed branch, because a schwa is never a stressed nucleus. This rider on rule 3 tests phonology, not morphology: `STRESSABLE_VOWELS` in [`src/qslex/tokenizer.py`](../src/qslex/tokenizer.py) is the vowel set minus the schwas. Even so, nearly every chunk it demotes is a suffix: keenness `ˈkiːn+nəs`, goalless `ˈɡəʊl+ləs`, freest `ˈfriː+əst`, angrier `ˈæŋɡrɪ+əR`.

The corpus has minimal pairs for this. happiest `ˈhæpiəst` and driest have no `+`, so their schwa was always treated as unstressed. beefiest `ˈbiːfi+əst` and freest differ from them only by an upstream `+`.

The rider also demotes some schwa-only chunks that are not suffixes, for the same reason:

- jukka `ˈjʊk+kə`, a given name with a `+` at its doubled consonant.
- you're `juː+əR`, whose second chunk is a clitic.
- The -shire place names. cambridgeshire `ˈkeɪmbrɪdʒ+ʃəR` and dorsetshire have the `+` upstream. wiltshire `ˈwɪlt+ʃəR` and somersetshire get it from `ipa-quirks.tsv`, which inserts it and describes it as a compound boundary.

None of their spellings changes, because `ə` is written ·Utter under either condition.

Every other chunk after a `+` is left alone. Many have their own stress mark and never reach rule 3’s fallback (`ˌriː+əˈdʒʌst` and the re- and pre- words). Of those that do reach it, the important case is a `+` that joins two words, where the second element has a vowel that can take stress: bookkeeping `ˈbʊk+kiːpɪŋ`, clipboard, courtship `ˈkɔːRt+ʃɪp`, sweatshirt `ˈswet+ʃɜːRt`. Not all of them are compounds. coolly `ˈkuːl+li`, agreeably `əˈɡriː+əbli`, soullessly `ˈsəʊl+ləsli` and outlawry `ˈaʊtlɔː+ri` have suffix chunks that the rider keeps stressed. This changes no spelling. Their `i` is written ·It under either condition, and `terminal-ess-est` matches only at the end of a word, so it never applies to the -less inside soullessly.

Stress conditioning still does not cross a chunk boundary. The rider reads the separator character and the chunk’s own vowels, and nothing before the `+`. The rules layer then rewrites the vowel that the rider demotes. See [`docs/orthographic-rules.md`](orthographic-rules.md), which spells the -ess, -est, -less and -ness terminals with ·Et.

The rule as first stated did not cover two cases. They were decided as follows:

- **ˌ counts as stress.** The first statement named only ˈ. But bacteriology `bækˌtɪəriˈɒlədʒi` and similar words put ˌ directly before the ɪə syllable. Treating them as stressed keeps word families together: bacteria and bacteriology both have ·Eat·Utter.
- **Rule 3 generalizes “monosyllable.”** A literal monosyllable test would change the hero, weary and theatre compounds to ·It·Utter, which would split them from their standalone forms.

### Where the mechanical rule breaks, and the override file

The rule reads ReadLex’s stress marks, and ReadLex does not mark stress inside compounds. So rule 2 demotes the second element of any **unhyphenated** compound, because the first element’s vowel is in the same chunk. The hyphenated form comes out right, because the hyphen starts a new chunk:

|             | mechanical               | standalone form                  |
| ----------- | ------------------------ | -------------------------------- |
| `musk-deer` | ·Day·**Eat**·Utter·Roe ✓ | deer `dɪəR` → ·Day·Eat·Utter·Roe |
| `reindeer`  | ·Day·**It**·Utter·Roe ✗  | same morpheme, no hyphen         |

The same fault affected -sphere (atmosphere, biosphere, stratosphere…), the -mere place names, headgear, greybeard, compeer and godfearing. Through the unstressed branch of rule 3, it also affected hereafter, hereby, hereof and hereto. Those came out differently from herein and herewith only because ReadLex happened to write a `ˌ` at the start of herein and herewith. No signal in the IPA separates reindeer from happier: both have a stress mark, a full vowel and Cɪə(R) at the end of the chunk. Relaxing rule 2 would give the wrong result for the much larger set of non-rhotic occurrences that the Manual explicitly makes unstressed (Austria, India, Virginia, area).

So the rule stays, and the exceptions are **data** in `src/qslex/data/ipa-overrides.tsv`. Each row is keyed on the exact normalized IPA string and lists the words it covers, the condition to force and the evidence. The validator fails if an override is never used, touches a word it does not list, or changes nothing.

The same problem affects a word-final `iː`. To the rule, honeybee `ˈhʌnɪbiː` looks the same as jubilee `ˈdʒuːbɪliː`, but only honeybee should keep the ·Eat of bee. The override file cannot hold these words. `iː` has one unconditional mapping row, so an override has no condition to select, and the rules layer reads `is_stressed` directly instead of a token’s condition. These words are listed in `src/qslex/data/rule-words.tsv` instead, under [`terminal-y`](orthographic-rules.md#5-whether-a-terminal--y-that-readlex-writes-in-full-is-stressed).

### Cross-checking against the Shavian column

ReadLex’s Shavian column is independent evidence. It writes 𐑽 (EAR) for stressed rhotic ɪə and 𐑦𐑼 for unstressed. For every row in the corpus, the validator checks that the number of 𐑽 in the Shavian column equals the number of ɪə tokens that the mapping resolves as stressed and rhotic.

The check compares counts per row instead of aligning segments. Aligning IPA with Shavian segment by segment would itself need a heuristic, and a wrong alignment would report false failures. The downside is that two compensating errors in one row cancel out. That case is rare. Few rows have more than one ɪə token. Fewer still have two *rhotic* ɪə that differ in stress, which is the only case where swapped conditions would go unnoticed, and nearly all of those rows are already recorded divergences.

A mismatch fails the build unless `src/qslex/data/shavian-divergences.tsv` lists the row **with an authority**. The rows fall into three groups:

- **The -ier/-ior families** (-ier, -ior, -iary, -iorate, -erior, -iorism: barrier, courier, senior, junior, warrior, apiary, ameliorate, exterior, incendiarism) make up most of the file. [§ Terminal -ier, -ior][ier] says “If unstressed, -·It·Utter·Roe : if stressed, -·Eat·Utter·Roe” and lists happier, carrier, furrier, senior and junior as unstressed. ReadLex is inconsistent here. It writes carrier 𐑒𐑨𐑮𐑦𐑼 but barrier 𐑚𐑨𐑮𐑽, with the same rhyme, and spells the two senses of the homograph furrier differently. The Manual takes precedence.
- **The meteor- stems and the unresolved stems** (meteorite, meteorology, meteoroid, panjshir, protocadherin, tyrconnel) have the authority `no-promotion-evidence`. Shavian writes 𐑽, but no row in ReadLex has a stressed EAR for the stem. `meteor` itself is `ˈmiːtɪɔːR` → 𐑥𐑰𐑑𐑦𐑹, with no EAR at all. The Manual’s *terminal* rule does not cover a word-medial -eor-. So these rows keep the mapping’s result instead of guessing a stress.
- **`we're`**: Shavian spells the contraction by its parts (𐑢𐑰𐑼 = we + ’re), not by its sounds.

A few rows have `condition=none`. These words are still written with happY `i`, so they produce no ɪə token, and only the Shavian column has an EAR. The loader accepts only `stressed`, `unstressed` and `none` in that column. The validator checks each row’s recorded Shavian string against the corpus, and fails on any row that no longer matches anything.

Result over the corpus: every row agrees with the Shavian column, diverges with a recorded authority, or has a non-rhotic ɪə, for which Shavian writes 𐑾 regardless of stress and so gives no evidence. No row diverges unexpectedly. The validator prints the tally and fails if any row does.

## Decision: weak u = ·Ooze (not ·Foot)

The Manual spells visual ·Vie·It·Zoo·Ye·Ooze·Utter·Low ([§ -al, -el, -le, -il][al]). Checked codepoint by codepoint, the fifth letter is U+E67E ·Ooze, not U+E67D ·Foot. So the primary source writes the weak-u vowel as **·Ooze**, and in this project the Manual takes precedence. ·Foot is arguably closer to the modern lax [u] of coalesced /ˈvɪʒuəl/ and /əkˈsentʃueɪt/. It is rejected because the Manual writes ·Ooze.

Two qualifications apply. First, ReadLex’s own Shavian column writes visual with 𐑫 (WOOL, the FOOT vowel). On this row the Shavian column **disagrees, and the Manual overrules it**. Elsewhere in this spec the Shavian column is used as supporting evidence. Second, the Manual’s ·Ooze is the second element of Read’s /zj/. So the evidence is direct for `u` after `j` and the postalveolars, and it is extended to `u` after other consonants (affluence, influence).

The consonant differs from the Manual on purpose. The Manual’s 1966 pronunciation had /zj/ (·Zoo·Ye). ReadLex has ʒ, and the senior column follows the IPA, so the lexicon writes ·Vie·It·J’ai·Ooze·Utter·Low.

The row covers every `u` without a length mark: after `j`, `tʃ`, `dʒ`, `ʃ` and `ʒ`, and after other consonants, mostly before another vowel. The validator has an expected count for it.

## Decision: non-rhotic aɪə/aʊə keep the schwa

The original question was whether the few non-rhotic aɪə and aʊə, if there were any, should absorb the schwa as the pre-r ones do. Checking the corpus showed that the premise was wrong. Non-rhotic aɪə and aʊə are common: science, client, quiet, diet, giant, lion, diary, trial, dial, bowel, towel, vowel, avowal, allowance. (Raw `aɪəʊ` matches are words like bio, where the `ə` belongs to a following GOAT vowel. The tokenizer splits those as `aɪ`+`əʊ`, as the tokenizer contract above describes.) The mapping absorbs the schwa **only before r/R** and writes ·I·Utter and ·Out·Utter otherwise, for three reasons:

- Every absorption example in the Manual is a vowel+R join (mire, sour, our, desire, hours, the §II join tables), and the sequences ·I·Utter and ·Out·Utter appear nowhere in the document. The Manual spells almost none of the candidate words: dial, lion, diary, towel, quiet, riot, fire and power are absent, and trial, vowel, violence and liable occur only in its Latin-script prose. The one exception supports the mapping. **highest** is spelled in [§ Terminals -ess, -est][ess], and it does **not** absorb the schwa: it writes a vowel letter, `-·Et·See·Tea`. That letter is ·Et, not ·Utter, because of a suffix convention that this segment mapping cannot express; see [What a segment mapping cannot do](#what-a-segment-mapping-cannot-do).
- The Manual’s loyal = ·Low·Oy·Utter·Low ([§ -al, -el, -le, -il][al]) keeps the schwa in the same non-rhotic diphthong+ə position.
- Absorption would merge minimal pairs: quiet/quite, lion/line, vial/vile, science/signs.

## Tagged pass-throughs (handled by later layers)

| Token       | Naive value              | Tag semantics                                                                     | Handled by                                                     |
| ----------- | ------------------------ | --------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| `Ə`         | ·Utter                   | Shavian epenthetic-vowel site in -es/-ed (kisses `ˈkɪsƏz`); QS convention differs | rules layer                                                    |
| `I`         | ·It                      | unstressed-ɪ site where Shavian writes schwa (banquet `ˈbæŋkwIt`)                 | rules layer, where a terminal rewrites it; otherwise ·It stays |
| `Ɑː`/`Æ`    | ·Ah / ·At                | TRAP-BATH dual variant rows (bath `bⱭːθ`/`bÆθ`)                                   | row policy                                                     |
| `Ð T N V F` | ·They ·Tea ·No ·Vie ·Fee | word signs the/to/and/of/for                                                      | canonical word-sign spellings                                  |

## What a segment mapping cannot do

A total function from IPA segments to letters cannot see which suffix a word has, so it cannot express several of the Manual’s prescriptions. They are listed here so that nobody takes their absence from this table to mean the Manual has no such rule. The rules layer implements all of them; see [`docs/orthographic-rules.md`](orthographic-rules.md).

| Manual rule                                                                                                         | Manual spelling                                                                             | This mapping                                                               | Notes                                                                                                                                                 |
| ------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| [§ Terminals -ess, -est, -less, -ness][ess]: “Distinguished from the -us, ous terminal by writing vowel No. 28 ·Et” | hostess `-·Et·See`, highest `-·Et·See·Tea`, hopeless `-·Low·Et·See`, goodness `-·No·Et·See` | ·Utter, because ReadLex writes plain `ə` in both families                  | a large family; the contrasting [-us/-ous][us] family is correctly ·Utter                                                                             |
| [§ Terminal -al, -el, -le, -il][al]: “omit any unstressed vowel sound between L and the preceding consonant”        | final, rifle, couple, easel, devil lose the vowel; Spaniel = ·See·Pea·At·No·Ye·Low          | keeps it: final = ·Fee·I·No·Utter·Low                                      | the same section that supports weak u = ·Ooze                                                                                                         |
| [§ Terminal -ing][ing]: affix -ing omits the vowel                                                                  | calling = ·Key·Awe·Low·-ing (but root wing keeps ·It)                                       | ·It always                                                                 | the affix/root distinction is morphological                                                                                                           |
| [§ Terminal -tion][tion], [§ -land, -ment][land]                                                                    | action `-·She·No`                                                                           | ·At·Key·She·Utter·No                                                       |                                                                                                                                                       |
| [§ Terminal -age][age]                                                                                              | manage = `-·Utter·Jay`, marriage = `-·It·Jay` after a -y root                               | ·It, since ReadLex writes plain `ɪ`, so the `I` tag does not catch it      |                                                                                                                                                       |
| [§ Terminal -y][y]                                                                                                  | coffee `-·It`; legatee, lessee, payee keep ·Eat “where the terminal is stressed”            | ·Eat wherever ReadLex writes a full `iː`, because its row is unconditional | the happY `i` row above already has `terminal-y` as its authority; whether a full `iː` at that terminal is stressed is a question for the rules layer |

Quikscript’s terminal conventions are keyed to the *spelling* of the suffix, and the IPA column does not record that information. The rules layer implements them. This mapping writes each segment as it is, and that layer rewrites the result. Two rows of the tagged pass-through table are also resolved there. Following [§ Terminal -es, -ed][esed], the rules layer drops `Ə` outright. `I` keeps its ·It unless a terminal rule rewrites that vowel, and in most rows with `I`, such as banquet and basketry, no rule does.

## Quirk normalizations (to be fixed upstream)

`src/qslex/data/ipa-quirks.tsv` fixes these upstream irregularities before tokenization:

- stray Shavian letters (𐑴 in hyperfocus, 𐑑 in oakshott)
- ASCII `g` for `ɡ`
- Latin spelling in the IPA: `ai` is eɪ in brainpan and brainstem but aɪ in lobotomise, per the Shavian column
- bare `a`, `ɑ` and `ɔ` that lack their length or laxness marks
- a spurious length mark (goulburn `əː`), found by the unmapped-IPA check, not by any upstream report
- misplaced marks (nauvoo `nɔˈː`, ursae majoris `dˈʒ`)
- missing hiatus markers that let `t`+`ʃ` fuse (sweatshirt, wiltshire), and a stray one that split `eə` (whate'er)
- `dz` for `dʒ` (jonnie)
- a missing `ə` in SQUARE (sierra leone)
- stray `.`, `'` and U+0329

The largest single class is **happY `i` written for EAR `ɪ`**. ReadLex spells shakespeare `ˈʃeɪkspiəR`, lightyear `ˈlaɪtjiəR`, pierce `piəRs` and others with `iə`. That tokenizes to ·It·Utter, the unstressed spelling, while the same rows’ Shavian column has 𐑽. Upstream contradicts itself here. It writes god-fearing `ˈɡɒd-ˌfiərɪŋ` but godfearing `ˈɡɒdfɪərɪŋ`, and magnetosphere with `iə` but atmosphere with `ɪə`. Each fix is supported by an independently attested standalone form (year, sphere, mere, near, sheer, zero, series, period). Three of them, lear, pierce and vere, also fit a pattern in the corpus. Every mark-less monosyllable row with `ɪəR` in ReadLex has 𐑽 in its Shavian. lear, pierce and vere are the only mark-less monosyllables written with `iəR` instead, and their Shavian has 𐑽 too. Some words in this class also need a stress override, because the mechanical rule still demotes them after the fix.

Every rule lists the words it affects, and the validator **enforces** that list. A rule that touches a word it does not list fails the build, and so does a rule that lists a word it no longer touches. Two caveats on the evidence:

- Most rules were cross-checked against the row’s Shavian column, but not all could be. `L`→`ɬ` is a **judgment call without Shavian support**. llanfair’s Shavian is 𐑤𐑨𐑯𐑓𐑺, with a plain /l/, because Shavian has no letter for /ɬ/ and upstream could not have written one. Quikscript does have ·Llan, and the capital `L` is clearly an intentional upstream marker, so the rule stays, on judgment. Likewise drm’s Shavian is an initialism with no vowel letters, so it cannot support `ɑ`→`ɑː`. The other words under that rule have 𐑸 in their Shavian.
- goulburn’s fix drops the spurious length mark (`əː`→`ə`) instead of reading it as NURSE (`əː`→`ɜː`). Its Shavian 𐑼 rules out NURSE: 𐑼 is schwa+r (auburn, melbourne), while NURSE is 𐑻 (burn). The output is the same either way, because ə and ɜː both give ·Utter. But this way the normalized corpus does not pass a wrong vowel on to the rules and row-policy layers.

The validator fails if any rule stops matching, so the file is also a list of fixes to make upstream. The corpus is vendored at a pinned commit, so a rule can stop matching only when someone updates the corpus or edits this file.

## Counted invariants

The expected corpus counts are in [`src/qslex/validate.py`](../src/qslex/validate.py). Most are bookkeeping. Three of them check claims about the corpus and the tokenizer:

- **EAR is always `ɪəR`, never `ɪR`.** The validator fails if the raw corpus contains any schwa-less `ɪR`, `aɪR` or `aʊR`.
- **GOAT is conserved.** Every `əʊ` in the normalized text is tokenized as ·Owe. None is taken into a neighboring triphthong token.
- **The affricate counts are accounted for by Shavian.** The `tʃ` and `dʒ` token counts are slightly higher than the counts of Shavian 𐑗 and 𐑡. The difference is exactly the initialisms whose Shavian column spells letter names instead of sounds (adhd, nlg, who; dm, gmt, gnp, gop, lgbt and its variants). The validator has expected values for the two token counts. It does not count the Shavian letters. The token counts check the quirk rules that insert a `+` at a compound boundary: if `t`+`ʃ` fused again in sweatshirt or wiltshire, the `tʃ` count would change.

## Out of scope

·Excite (U+E66B) and ·Exam (U+E66C) are in the CSUR table but in no mapping row. This is intentional. The Manual limits them to “a Tall ·Excite for ·Key·See sounds : a Deep ·Exam for ·Gay·Zoo sounds — **but only where Orthodox spells these sounds with X**”, and writes ·Excite in tax, fix and ox but ·Key·See in tacks, licks and locks. Tax and tacks are homophones, so IPA alone cannot decide which to write, and a segment mapping cannot make that choice. The lexicon stores the X-letter form in a `qs_x` column derived from the senior column. The rules layer specifies where an X-letter goes ([`docs/orthographic-rules.md`](orthographic-rules.md)), and [`docs/pipeline.md`](pipeline.md#artifact-formats) describes the column.

[csur]: https://www.quikscript.net/csur/
[manual]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html
[chart]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#alphabet-chart
[vr]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#vowels-plus-r
[rs]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#spell-all-rs
[ier]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-ier-ior
[ia]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-ia-ea
[y]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-y
[al]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-al-el-le-il
[sec2]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#section-2
[common]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#common-words
[ess]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-ess-est
[us]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-us-ous
[ing]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-ing
[tion]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-tion
[land]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-land-ment
[age]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-age
[esed]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-es-ed
