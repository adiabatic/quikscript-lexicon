# Word signs, abbreviations, and special words

ReadLex abbreviates five words in its IPA column with capitals: the=`Ð`, to=`T`, and=`N`, of=`V`, for=`F`. [`docs/ipa-to-qs.md`](ipa-to-qs.md) maps each capital to the matching Quikscript letter. Quikscript has more word signs than these five, and the Manual gives them in three lists. This document specifies the layer that handles them: lexical overrides applied after [Read’s orthographic rules](orthographic-rules.md) to produce the finished spelling.

Authority links go to the [AMS Manual transcription][manual]. Every letter-name spelling quoted below was copied codepoint by codepoint from its PUA text, with the ZWNJs (which are there only for presentation) removed. Page numbers are the Manual’s own.

## Artifacts

- `src/qslex/data/word-signs.tsv`: the 105 rows that are written into a spelling column. They are the core eight, the three abbreviations and the Manual’s standard word-outlines, plus two rows that repeat one of those outlines so that it applies inside a contraction ([Tier 3](#tier-3-the-standard-word-outlines)). Columns: `word`, `pos`, `tier`, `senior`, `junior`, `full`, `authority`, `note`.
- `src/qslex/data/contractions.tsv`: the [§III contraction list][senior], which is written into no column. Its ≈50 printed entries make 78 rows. Several entries cover an inflected set (`be/ing/en`, `come/s/ing`, `make/ing, made`), and two rows are the clitics generalized [below](#contractions-possessives-and-the-apostrophe). Two more rows come from other parts of the Manual:
  - doing ·Day·-ing comes from the [terminal -ing][ing] section, which prints it among its Root Contractions plus Affix. The §III list itself stops at do, did, don't and didn't.
  - done ·Day·No comes from the [No-how][no-how] passage, which writes it at the word’s second occurrence after spelling it out at the first. This source is running text, not a rule, so the checker accepts the form and the transliterator does not write it.

  The `authority` column names each row’s source. Columns: `word`, `pos`, `kind`, `contraction`, `authority`, `note`.
- `src/qslex/words.py`: the loaders and the substitution. The loaders reject, among other things, an unknown tier, an `authority` that is not one of this table’s Manual anchors, a Junior spelling identical to the Senior one, a part-of-speech row for a word that already has a row for every part of speech, and a missing core sign.
- `src/qslex/letters.py`: the letter-name parsing and rendering functions, shared with the rules.
- `src/qslex/elements.py`: pairs an entry’s words and separators with the runs of its spelling. The rules use the same function, so the two layers always agree on where a boundary is.

## The three tiers

|     | Manual                         | What it is                             | Where it is used                                       |
| --- | ------------------------------ | -------------------------------------- | ------------------------------------------------------ |
| 1   | [§ Contractions, p.12][junior] | the eight single-letter word signs     | both columns                                           |
| 2   | [§ Contractions, p.17][senior] | ≈50 Senior contractions                | no column; the transliterator and the spell checker    |
| 3   | [§ Common words, p.16][common] | 69 headwords of standard word-outlines | the senior column, with a junior form where it differs |

Tier 2 is written into no column. The §III contractions are an optional Senior facility. They are not the standard spelling of the words they contract. [`docs/orthographic-rules.md`](orthographic-rules.md) keeps often at ·Ox·Fee·Utter·No instead of the listed ·Ox·Fee·No for the same reason. So the senior column has people = ·Pea·Eat·Pea·Low where the list has ·Pea·Pea·Low, and think = ·Thaw·It·-ing·Key where the list has ·Thaw. The transliterator applies the list as an optional layer ([`docs/latin2qs.md`](latin2qs.md#the-grade-and-the-two-facilities-it-defaults)). The spell checker that the Desk and the language server share accepts the contractions as correct Senior writing, but no column contains them.

## Tier 1: the core eight

“Here are eight words of two or three letters which even writers of Junior Quickscript should soon contract to single letters” ([p.12][junior]). The signs are therefore these words’ standard spellings in *both* columns. ReadLex does the same for five of them with `Ð T N V F`.

| Word | Sign  | Uncontracted, as the Manual writes it | Where      |
| ---- | ----- | ------------------------------------- | ---------- |
| the  | ·They | ·They·Utter                           | p.11, p.24 |
| of   | ·Vie  | ·Ox·Vie                               | p.11, p.24 |
| and  | ·No   | ·At·No·Day                            | p.11, p.24 |
| to   | ·Tea  | ·Tea·Foot                             | p.11, p.24 |
| it   | ·It   | ·It·Tea                               | p.11, p.24 |
| is   | ·Zoo  | ·It·Zoo                               | p.11, p.24 |
| for  | ·Fee  | ·Fee·Awe·Roe                          | p.11, p.24 |
| be   | ·Bay  | ·Bay·Eat                              | p.24       |

For five of the eight, ReadLex writes the capital and the segment mapping turns it into the sign. The other three, it `ɪt`, is `ɪz` and be `biː`, have ordinary IPA, so this layer supplies the sign.

The uncontracted forms are recorded in the `full` column, which no artifact uses. The Manual does write them:

- The alphabet pangram on [p.11][tips], one page *before* the Contractions section, spells out seven of the eight (all but be).
- The Junior half of the p.24 comparison spells out all eight.
- The Economy table lists “Classes 2, 3, 4” at 15 % and “or with Contractions of ‘the, of, and, to, for, it, is, be’” at 20 %.

So Read himself has a register that does without the signs. But the Manual tells Junior writers to use them, [#8][plan] decided to follow that instruction, and the p.26 Junior examples use them (and = ·No in Bo-peep). The `full` column exists because these forms cannot be recovered any other way. For five of the eight, ReadLex’s IPA is already the capital, so nothing in the corpus gives ·Ox·Vie back.

For the, the `full` column records the specimens’ ·They·Utter, and there is no fuller spelling to record. Those specimens contradict the Manual’s own instruction: “as soon as words are not to vary in their spelling, how should we spell ‘the’? … the solution which, from experience, satisfies all writers and all occasions, is to omit the variable vowel entirely” (p.7, in [§ Spelling][spelling]).

## Tier 3: the standard word-outlines

[§ Common words][common] prints 69 headwords. Several cover an inflected pair (`day/s`, `know/n`, `use/d (v.)`), so the headwords make 84 words, and 92 rows once the parts of speech are split out. For 79 of the 84, ReadLex’s IPA and the orthographic rules already produce the Manual’s outline. (at is one of the 79, but it is rewritten inside four phrase entries; see [Phrase entries](#phrase-entries).) The 79 are listed anyway, for the same reason as the eleven orthographic rules that rewrite nothing: if a corpus row ever contradicts the Manual, the substitution corrects it instead of passing it through. The validator fails if the number of rows a word rewrites changes, including to or from zero.

Two more rows belong to this tier but are not among the 84: wasn't and 'twas. An outline is substituted only at the boundaries that [`src/qslex/elements.py`](../src/qslex/elements.py) finds, and neither clitic leaves a boundary. `n't` attaches solid, and the aphetic `'t` is written straight onto the word. So each entry is one Latin part against one spelled run, with no boundary inside it where was could be matched. The outline applies to these two words only through rows of their own.

The two are listed individually instead of generalized into a rule. A rule that substituted outlines inside contractions would change eight corpus rows over six other words:

- isn't and 'tis would take the core sign for is: ·Zoo·No·Tea and ·Tea·Zoo.
- it's, it'd and it'll would take the core sign for it: ·It·See, ·It·Utter·Day and ·It·Utter·Low.
- mustn't would become ·May·Utter·See·Tea·No·Tea, inserting a ·Tea that neither ReadLex’s `ˈmʌsənt` nor the Manual has.

The Manual writes none of these six words. The it family shows the downside. ·It·See is letter for letter the [§III][senior] contraction that `contractions.tsv` lists for it's. So the rule would put a Senior contraction into the senior column, which the Tier 2 policy that keeps people at ·Pea·Eat·Pea·Low forbids.

was is different because the Manual writes its outline inside both contractions itself. The Senior form is in the gown-shop passage’s wasn't, and the Junior form is in Mary’s Lamb’s 'twas. The `was` row’s own Senior/Junior split then supplies the other column of each. The Manual writes an outline inside only two other contractions: doesn't (·Day·Utter·Zoo·Utter·No·Tea in the Junior rhyme) and they'll (·They·Eight’·Low). The rules already give the does and they outlines there, so neither word needs a row.

Seven words in this tier rewrite their own entries (at rewrites only inside phrase entries). Five of the seven are word-level standardizations. wasn't combines its outline with the vowel that [`terminal-nt`](orthographic-rules.md#decisions) elides in the senior column only:

| Word                     | Senior                      | Junior                   | Why                                                                                       |
| ------------------------ | --------------------------- | ------------------------ | ----------------------------------------------------------------------------------------- |
| always                   | ·Awe·Low·Way·Utter·Zoo      | ·Awe·Low·Way·Eight·Zoo   | the standard outline reduces -ways; ReadLex has `ˈɔːlweɪz`                                |
| was                      | ·Way·Utter·Zoo              | ·Way·Ox·Zoo              | the standard outline takes the weak vowel; ReadLex has `wɒz`                              |
| wasn't                   | ·Way·Utter·Zoo·No·Tea       | ·Way·Ox·Zoo·Utter·No·Tea | the same outline inside the contraction, senior eliding; ReadLex has `ˈwɒzənt`            |
| 'twas                    | ·Tea·Way·Utter·Zoo          | ·Tea·Way·Ox·Zoo          | the same again, after the aphetic 't; ReadLex has `twɒz`                                  |
| that (not demonstrative) | ·They·Tea                   | ·They·At·Tea             | the Common words footnote: “spelt in full only when demonstrative; otherwise — ·They·Tea” |

The word-signs issue ([#3][ticket]) did not predict that `was` would need a junior form. The Manual’s specimens confirm the split in the word itself. The Senior gown-shop passage on p.23 writes wasn't ·Way·**Utter**·Zoo·No·Tea. The Junior Mary’s Lamb on p.26 writes was twice as ·Way·**Ox**·Zoo (“its fleece was white as snow” and “her lamb was sure to go”) and 'twas as ’·Tea·Way·**Ox**·Zoo.

The gown-shop wasn't also elides the vowel between the outline and the `n't`, and the senior column does the same. [`terminal-nt`](orthographic-rules.md#decisions) generalizes the bare ·No·Tea that every `n't` entry in the [§III][senior] list writes: can't ·Key·No·Tea, couldn't ·Key·Day·No·Tea, haven't ·He·Vie·No·Tea. So senior wasn't is letter for letter the gown-shop form. The Junior doesn't ·Day·Utter·Zoo·Utter·No·Tea on p.26 keeps the vowel, and the junior column follows *that*: every row the rule rewrites has a `qs_junior` with the vowel kept. Each specimen is therefore reproduced by its own grade’s column.

after and last rewrite for a different reason: they take ·At. The Manual writes after = ·At·Fee·Tea·Utter·Roe and last = ·Low·At·See·Tea. That agrees with ReadLex’s `Æ` rows and overrules its `Ɑː` ones. This is not an accident of Read’s own accent. It is the purpose of the section: “The choice of standard spellings is convenient for writing and reading. It implies no preference in pronunciation” ([p.22][note]). So these two words are spelled with ·At for the BATH vowel. ReadLex’s `Æ` rows for them are TrapBath variants, which the [row policy](pipeline.md#row-policy-the-rrp-family-only) drops, so the rows rewritten are the RRP rows with `Ɑː`.

### What the part-of-speech tag is for

A tier-3 row has a POS tag only where a ReadLex tag would otherwise apply the outline to the wrong entry, or where the Manual labels the part of speech itself:

- **a** AT0: the ZZ0 row is the letter A, ·Eight.
- **am** VBB: the AV0 row is a.m., ·Eight·Et·May.
- **does** VDZ: the NN2 row is the plural of doe, ·Day·Owe·Zoo.
- **who** PNQ: the NP0 row is W.H.O. spelled out.
- **use** NN1 ·Ye·Ooze·See against VVB/VVI ·Ye·Ooze·Zoo, and **used** VM0 ·Ye·Ooze·See·Tea against AJ0/VVD/VVN ·Ye·Ooze·Zoo·Day. This is the Manual’s own `use (n.)` / `use/d (v.)` split, which ReadLex’s `juːs`/`juːz` already makes.
- **that** DT0 ·They·At·Tea against AJ0/AV0/CJT ·They·Tea.

Every other row has an empty `pos` and applies to every tag ReadLex gives the word. The validator fails on any row, tagged or not, that the substitution never consults.

## Abbreviations

The Manual writes these “without a break between letters” and with a name-dot ([p.12][junior]). ReadLex’s IPA spells them out in full, so all three rewrite:

|     | Quikscript     | Manual’s letter numbers | ReadLex IPA        |
| --- | -------------- | ----------------------- | ------------------ |
| Mr  | ·May·Roe       | 22/25                   | `ˈmɪstəR`          |
| Mrs | ·May·Zoo       | 22/12                   | `ˈmɪsəz`, `ˈmɪsɪz` |
| Dr  | ·Day·Utter·Roe | 4/36/25                 | `ˈdɒktəR`          |

The column does not contain the name-dot, because the dot is a rendering decision. `manual-spellings.tsv` leaves the dot off England for the same reason. The transliterator adds it ([`docs/latin2qs.md`](latin2qs.md#the-namer-dot)). The Manual’s own specimen is ··May·Roe ·He·At·Roe·Utter·Low·Day ·Jay·Owe·No·Zoo for “Mr Harold Jones”, with the dot on Mr only.

The Manual names MS, M.C., etc, i.e. and e.g. as standard contractions in everyday use but gives no Quikscript spelling for them, so they have no row. `etc` needs none: the Manual replaces it with ·No·No·No, “and-and-and” ([§ Other conventions][other]), and ReadLex already writes that as `NNN`.

## Phrase entries

A multi-word or hyphenated entry is matched word by word, at every space and hyphen. ReadLex does the same with its capitals: air-to-air is `ˌeəR-T-ˈeəR`, and dyed-in-the-wool is `ˌdaɪd-ɪn-Ð-ˈwʊl`. Matching the same way keeps this layer consistent with ReadLex’s capitals. [Read’s orthographic rules](orthographic-rules.md#one-entry-several-words) cut an entry up at the same boundaries, with the same code.

Two checks apply:

- Inside a phrase, a row is applied only if it has an empty `pos` and so applies to every part of speech. The entry’s tag belongs to the phrase, not to any word inside it. For example, that is has an AV0 tag, but its that is not the degree adverb. So that is keeps ·They·At·Tea, while the standalone AV0 that contracts to ·They·Tea.
- Nothing in an entry is substituted unless its Latin parts and its spelling’s runs line up one for one. to-day (`təˈdeɪ`) has one spelled run against three Latin parts. dhs has one Latin part against seven runs, because its IPA spells out the department’s name. Both are left as they are. Equal counts are not enough: the check also rejects a Latin hyphen facing a spelled space, so a substitution never crosses a boundary other than the one it matched.

`EXPECTED_SIGN_CHANGES` in [`src/qslex/validate.py`](../src/qslex/validate.py) records the expected number of rows each word rewrites, and it is the only place those counts are written down. `make validate` prints them word by word. These are the words it lists, in its order:

| Word   | Result                                                                                  |
| ------ | --------------------------------------------------------------------------------------- |
| 'twas  | → ·Tea·Way·Utter·Zoo                                                                    |
| after  | the `Ɑː` rows, and the `Ɑː` half of the PRE entry after- → ·At·Fee·Tea·Utter·Roe        |
| always | → ·Awe·Low·Way·Utter·Zoo                                                                |
| at     | at-home, at-homes, gentleman-at-arms, gentlemen-at-arms: ReadLex’s weak `ət` → ·At·Tea  |
| be     | be VBB, be VBI, would-be → ·Bay                                                         |
| dr     | → ·Day·Utter·Roe                                                                        |
| is     | is VBZ, that is → ·Zoo                                                                  |
| it     | it PNP, as it were → ·It                                                                |
| last   | last ×3, at last, last-ditch → ·Low·At·See·Tea                                          |
| mr     | both rows → ·May·Roe                                                                    |
| mrs    | `ˈmɪsəz` and `ˈmɪsɪz` → ·May·Zoo                                                        |
| that   | that AJ0, AV0, CJT → ·They·Tea                                                          |
| to     | lean-to ×2, set-to → ·Tea                                                               |
| was    | → ·Way·Utter·Zoo                                                                        |
| wasn't | both rows → ·Way·Utter·Zoo·No·Tea                                                       |

In lean-to and set-to, the to is a lexicalized particle, not the preposition. The substitution still applies, because ReadLex writes the same particle with its own word sign in stand-to `stænd-ˈT`, talking-to `ˈtɔːkɪŋ-T` and to-do `T-ˈduː`. Substituting in lean-to and set-to makes upstream’s treatment of the particle consistent.

## The junior column

Per [#8][plan], the senior column is the default, and the junior column has a value only where the Junior spelling differs. That is 27 rows:

- six word-level rows: that ×3, always, was and 'twas;
- the 21 rows that [`terminal-nt`](orthographic-rules.md#decisions) rewrites, whose linking vowel the junior grade keeps. The two wasn't rows are among them, and their junior form has both the ·Way·Ox outline and the kept vowel.

No other rows differ. The Manual’s terminal, affix and prefix conventions apply to both grades ([#2][rules]). The Manual sanctions the core eight for Junior writing, and it gives the abbreviations in the Junior section.

The validator checks one invariant on this column: **a Junior spelling must equal the spelling produced without the sign substitution and without `terminal-nt`.** So every junior form in `word-signs.tsv` is what the rules alone produce for that grade. If a word ever needs a Junior spelling that the rules do not produce, `make validate` fails, and the column model has to be reconsidered.

## Contractions, possessives, and the apostrophe

The Manual says almost nothing about apostrophes, but its examples show a consistent practice. Every instance in the text:

| Class              | Apostrophe? | Evidence                                                                                                                                                                                                                                                                                                                                          |
| ------------------ | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| possessive         | **no**      | “Possessive apostrophes are usually omitted without loss of meaning” ([§ Punctuation etc][punct], p.8); “··May·Roe ·Jay·Owe·No·Zoo·Zoo clearly means ‘Mr Jones's’: with one name-dot, no apostrophe” ([§ Terminal -es, -ed][es-ed], p.18); anybody's = ·Et·No·It·Bay·Ox·Day·It·Zoo (p.24); world/'s = ·Way·Utter·Roe·Low·Day·Zoo ([p.16][common]) |
| `n't`              | **no**      | all nine instances: can't, couldn't, don't, didn't, haven't, wouldn't in the §III list, plus running-text wasn't ·Way·Utter·Zoo·No·Tea, doesn't ·Day·Utter·Zoo·Utter·No·Tea and wouldn't ·Way·Day·No·Tea                                                                                                                                          |
| verbal `'s`        | **no**      | She's = ·She·Zoo (p.23); the list gives its and it's one spelling, ·It·See                                                                                                                                                                                                                                                                        |
| `'d`               | **yes**     | He'd = ·He’·Day (p.24)                                                                                                                                                                                                                                                                                                                            |
| `'ll`              | **yes**     | they'll = ·They·Eight’·Low (p.26), the ·Low being the listed will/'ll contraction                                                                                                                                                                                                                                                                 |
| aphetic `'t`       | **yes**     | 'Twas = ’·Tea·Way·Ox·Zoo (p.26)                                                                                                                                                                                                                                                                                                                   |
| `'ve`, `'m`, `'re` | unattested  | the Manual never writes one                                                                                                                                                                                                                                                                                                                       |

The clearest evidence is one six-line rhyme on p.26, which writes doesn't without an apostrophe and they'll with one, two lines apart.

What decides the apostrophe is whether the clitic’s letters could be read as a continuation of the word. Phonology and letter class do not decide it. `n't` and `'s` add letters that are already ordinary word-final spellings, so they attach solid. `'d`, `'ll` and aphetic `'t` would be misread, so the apostrophe stays. For the three unattested clitics, this project follows `'d` and `'ll` and keeps the apostrophe: I'm = ·I’·May, you've = ·Ye·Ooze’·Vie, we're = ·Way·Eat’·Utter·Roe. `contractions.tsv` has two `clitic` rows, `'ll` = ’·Low and `n't` = ·No·Tea, and each row’s note says what it was generalized from.

Attaching solid is separate from eliding the vowel before the clitic. The table above decides only the apostrophe, and wasn't and doesn't attach the clitic in the same way. Whether the vowel before it is written is decided by [`terminal-nt`](orthographic-rules.md#decisions), by grade. The senior column elides it, as the Senior specimen writes wasn't and as §III prints can't and couldn't. The junior column keeps it, as the Junior rhyme writes doesn't.

The apostrophe is also independent of the outline. p.26’s 'Twas shows where the apostrophe goes, but it is Junior text, so it says nothing about the Senior vowel. The senior column has ·Tea·Way·**Utter**·Zoo ([Tier 3](#tier-3-the-standard-word-outlines)), and the transliterator writes it with the same leading ’. So some spellings the table cites are not the ones the columns contain. The columns contain no apostrophes. The transliterator reinserts them ([`docs/latin2qs.md`](latin2qs.md#apostrophes)).

**Where the possessive meets the -es rule.** [`terminal-es-ed`][es-ed] already omits the separating vowel between the seven pairs the Manual names (SZ, ShZ, ChZ, JZ, ZZ, DD, TD). So a possessive after a sibilant is a bare ·Zoo with nothing before it, and Jones's comes out ·Jay·Owe·No·Zoo·Zoo. A plural or possessive -Z becomes -S after a voiceless consonant (cups = ·Key·Utter·Pea·See against cubs = ·Key·Utter·Bay·Zoo). That needs no rule, because ReadLex’s IPA already writes /s/ there.

**The namer dot.** A standalone sign letter that is meant as a *letter* needs the namer dot, which cancels the word-sign reading ([quikscript.net/namer-dot-usage](https://www.quikscript.net/namer-dot-usage/)). The Manual also lets a dotted title cover the name that follows it. Both are rendering decisions, and the transliterator implements them ([`docs/latin2qs.md`](latin2qs.md#the-namer-dot)). This layer ensures only that the column contains the sign.

## What the validator checks

The word-sign section of [`src/qslex/validate.py`](../src/qslex/validate.py) fails unless:

- the substitution consults every row in `word-signs.tsv` for at least one corpus row. A corpus word that matches a row’s word does not count unless the row is consulted. So the validator fails on any row that no longer matches anything.
- every word that rewrites rows rewrites exactly the number `EXPECTED_SIGN_CHANGES` gives for it, and every word that rewrites rows has an entry there.
- **every word that rewrites rows also has a `manual-spellings.tsv` row, with `rule` set to `junior-contractions` or `common-words`, that checks its spelling against the Manual.** A count alone does not check a spelling. If after’s outline were mistyped as, say, ·At·Fee·Tea·Roe, it would still rewrite the same five rows and match the count. A row that rewrites nothing needs no `manual-spellings.tsv` row, because ReadLex’s own IPA already agrees with it.
- every corpus row for one of the core eight comes out as that word’s sign.
- exactly `EXPECTED_JUNIOR_DIVERGENCES` rows have a Junior spelling, and each equals the spelling produced without the sign substitution and without `terminal-nt`.
- every `word` row in `contractions.tsv` names a word ReadLex has.

[manual]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html
[junior]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#junior-contractions
[senior]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#senior-contractions
[common]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#common-words
[es-ed]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-es-ed
[punct]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#punctuation-etc
[other]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#other-conventions
[spelling]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#spelling
[tips]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#writing-tips
[ing]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-ing
[no-how]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#no-how
[note]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#examples-note
[plan]: https://github.com/adiabatic/quikscript-lexicon/issues/8
[rules]: https://github.com/adiabatic/quikscript-lexicon/issues/2
[ticket]: https://github.com/adiabatic/quikscript-lexicon/issues/3
