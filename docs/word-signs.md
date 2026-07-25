# Word signs, abbreviations, and special words

ReadLex abbreviates five words in its IPA column with capitals — the=`Ð`, to=`T`, and=`N`, of=`V`, for=`F` — and [`docs/ipa-to-qs.md`](ipa-to-qs.md) already sends each to the matching Quikscript letter. Quikscript's inventory is larger, and it is not one list but three. This is the layer that owns them: the lexical overrides that sit after [Read's orthographic rules](orthographic-rules.md) and before the finished spelling.

Authority links go to the [AMS Manual transcription][manual]; every letter-name spelling quoted below was extracted codepoint-for-codepoint from its PUA text, with the presentation-only ZWNJs stripped. Page numbers are the Manual's own.

## Artifacts

- `src/qslex/data/word-signs.tsv` — the 103 rows that reach a column: the core eight, the three abbreviations, and the Manual's standard word-outlines. Columns: `word`, `pos`, `tier`, `senior`, `junior`, `full`, `authority`, `note`.
- `src/qslex/data/contractions.tsv` — the 78 rows of the [§III contraction list][senior], which reach **no** column. Columns: `word`, `pos`, `kind`, `contraction`, `authority`, `note`.
- `src/qslex/words.py` — the loaders and the substitution, which rejects an unknown tier, a Manual anchor that does not belong to this table, a Junior spelling that merely repeats the Senior one, a part-of-speech row that a general row already shadows, and a missing core sign.
- `src/qslex/letters.py` — the letter-name primitives this layer shares with the rules.
- `src/qslex/elements.py` — the split into elements it shares with them too, so that neither layer can disagree with the other about where a boundary is.

## The three tiers

| | Manual | What it is | Where it lands |
|---|---|---|---|
| 1 | [§ Contractions, p.12][junior] | the eight single-letter word signs | both columns |
| 2 | [§ Contractions, p.17][senior] | ~50 Senior contractions | no column — the converter's table |
| 3 | [§ Common words, p.16][common] | 69 headwords of standard word-outlines | the senior column, with a junior form where it diverges |

Tier 2 is the odd one out and stays that way, for the same reason [`docs/orthographic-rules.md`](orthographic-rules.md) keeps often at ·Ox·Fee·Utter·No rather than the listed ·Ox·Fee·No: it is an optional Senior facility, not how the word is spelt. So the senior column has people = ·Pea·Eat·Pea·Low against the list's ·Pea·Pea·Low, and think = ·Thaw·It·Oolong·Key against ·Thaw. The list is shipped for [#6][converter] to apply as a mode.

## Tier 1: the core eight

"Here are eight words of two or three letters which even writers of Junior Quickscript should soon contract to single letters" ([p.12][junior]). They are therefore these words' standard spellings in *both* columns, mirroring what ReadLex already does with `Ð T N V F`.

| Word | Sign | Uncontracted, as the Manual writes it | Where |
|---|---|---|---|
| the | ·They | ·They·Utter | p.11, p.24 |
| of | ·Vie | ·Ox·Vie | p.11, p.24 |
| and | ·No | ·At·No·Day | p.11, p.24 |
| to | ·Tea | ·Tea·Foot | p.11, p.24 |
| it | ·It | ·It·Tea | p.11, p.24 |
| is | ·Zoo | ·It·Zoo | p.11, p.24 |
| for | ·Fee | ·Fee·Awe·Roe | p.11, p.24 |
| be | ·Bay | ·Bay·Eat | p.24 |

Five of the eight need no work: ReadLex writes the capital, the segment mapping writes the sign. The other three — it `ɪt`, is `ɪz`, be `biː` — carry ordinary IPA, so the sign is supplied here.

**The uncontracted forms are recorded but are not a column.** They are attested: the alphabet pangram on [p.11][tips] sits one page *before* the Contractions section and spells seven of the eight out — all but be — the Junior half of the p.24 comparison spells out all eight, and the Economy table prices "Classes 2, 3, 4" at 15 % against "or with Contractions of 'the, of, and, to, for, it, is, be'" at 20 % — so Read himself has a register that does without them. But the Manual's instruction is that Junior writers should use the signs, [#8][plan] ruled on that, and the p.26 Junior examples do use them (and = ·No in Bo-peep). The `full` column exists because these forms are otherwise *unrecoverable*: for five of the eight, ReadLex's IPA is already the capital, so no amount of work on the corpus gets ·Ox·Vie back.

For the there is no fuller spelling to record beyond the specimens' ·They·Utter, and those specimens contradict the Manual's own ruling: "as soon as words are not to vary in their spelling, how should we spell 'the'? … the solution which, from experience, satisfies all writers and all occasions, is to omit the variable vowel entirely" (p.7, in [§ Spelling][spelling]).

## Tier 3: the standard word-outlines

[§ Common words][common] prints 69 headwords, several of them covering an inflected pair (`day/s`, `know/n`, `use/d (v.)`), for 84 words in 92 rows once the parts of speech are split out. **Seventy-nine of the 84 are already exactly what ReadLex's IPA gives** once the orthographic rules have run. They ship anyway, for the reason the sixteen no-op rules do: a corpus row that ever contradicts the Manual gets corrected rather than passed through, and the validator pins the count so a word that starts mattering is visible.

Three of the five that do rewrite are word-level standardisations:

| Word | Senior | Junior | Why |
|---|---|---|---|
| always | ·Awe·Low·Way·Utter·Zoo | ·Awe·Low·Way·Eight·Zoo | the standard outline reduces -ways; ReadLex has `ˈɔːlweɪz` |
| was | ·Way·Utter·Zoo | ·Way·Ox·Zoo | the standard outline takes the weak vowel; ReadLex has `wɒz` |
| that (not demonstrative) | ·They·Tea | ·They·At·Tea | the Common words footnote: "spelt in full only when demonstrative; otherwise — ·They·Tea" |

`was` is the one the ticket did not predict, and the Manual's specimens confirm the split independently, in the same word: the Senior gown-shop passage on p.23 writes wasn't ·Way·**Utter**·Zoo·No·Tea, while the Junior Mary's Lamb on p.26 writes was twice as ·Way·**Ox**·Zoo — "its fleece was white as snow" and "her lamb was sure to go" — and 'twas as ’·Tea·Way·**Ox**·Zoo.

The other two rewrite for a different reason. **after and last take ·At.** The Manual writes after = ·At·Fee·Tea·Utter·Roe and last = ·Low·At·See·Tea, which agrees with ReadLex's `Æ` rows and overrules its `Ɑː` ones. That is not an accident of Read's own accent — it is the point of the section: "The choice of standard spellings is convenient for writing and reading. It implies no preference in pronunciation" ([p.22][note]). So the BATH set is standardised on ·At and the variant rows collapse for these two words, whichever way [#8][plan]'s rhotic-RP-only decision finally falls in [#4][pipeline].

### What the part-of-speech tag is for

A tier-3 row carries a POS tag only where a ReadLex tag would otherwise take the outline to the wrong entry, or where the Manual labels the part of speech itself:

- **a** AT0 — the ZZ0 row is the letter A, ·Eight.
- **am** VBB — the AV0 row is a.m., ·Eight·Et·May.
- **does** VDZ — the NN2 row is the plural of doe, ·Day·Owe·Zoo.
- **who** PNQ — the NP0 row is W.H.O. spelt out.
- **use** NN1 ·Ye·Ooze·See against VVB/VVI ·Ye·Ooze·Zoo, and **used** VM0 ·Ye·Ooze·See·Tea against AJ0/VVD/VVN ·Ye·Ooze·Zoo·Day — the Manual's own `use (n.)` / `use/d (v.)` split, which ReadLex's `juːs`/`juːz` already honours.
- **that** DT0 ·They·At·Tea against AJ0/AV0/CJT ·They·Tea.

Everything else holds for every tag ReadLex gives the word, which the validator proves by requiring each row to be reached.

## Abbreviations

Written "without a break between letters" and name-dotted ([p.12][junior]). ReadLex expands them in the IPA column, so all three rewrite:

| | Quikscript | Manual's letter numbers | ReadLex IPA |
|---|---|---|---|
| Mr | ·May·Roe | 22/25 | `ˈmɪstəR` |
| Mrs | ·May·Zoo | 22/12 | `ˈmɪsəz`, `ˈmɪsɪz` |
| Dr | ·Day·Utter·Roe | 4/36/25 | `ˈdɒktəR` |

The name-dot itself is not in the column — the same convention `manual-spellings.tsv` already uses for England — because it is a rendering decision that belongs to [#6][converter]. The Manual's own specimen is ··May·Roe ·He·At·Roe·Utter·Low·Day ·Jay·Owe·No·Zoo for "Mr Harold Jones", with the dot on Mr only.

The Manual names MS, M.C., etc, i.e. and e.g. as standard contractions in everyday use but gives no Quikscript spelling for them, so they get no row. `etc` needs none: the Manual replaces it with ·No·No·No, "and-and-and" ([§ Other conventions][other]), and ReadLex writes that already as `NNN`.

## Phrase entries

A multi-word or hyphenated entry is matched word by word at every boundary, space and hyphen alike. That is what ReadLex itself does with its capitals — air-to-air is `ˌeəR-T-ˈeəR`, dyed-in-the-wool is `ˌdaɪd-ɪn-Ð-ˈwʊl` — so following it keeps the two halves of the same convention consistent. [Read's orthographic rules](orthographic-rules.md#one-entry-several-words) now cut an entry up the same way, at the same boundaries, in the same code.

Two guards keep it honest. A row is only applied inside a phrase if it holds for **every** part of speech, because the entry's tag belongs to the phrase and not to any word inside it: that is has an AV0 tag, but the that inside it is not the degree adverb, so it keeps the demonstrative ·They·At·Tea while the standalone AV0 that contracts. And nothing is substituted unless the Latin words and the spelling's runs are the same shape, which is what stops to-day (`təˈdeɪ`, one run against three Latin parts) and dhs (one Latin part against seven runs, its IPA being the department's name spelt out) from being mangled. Equal counts are not enough on their own: the shape check also refuses a Latin hyphen facing a spelt space, so a substitution can never cross a boundary other than the one it matched.

All 34 rows the layer rewrites, in full:

| Rows | Word | Result |
|---:|---|---|
| 5 | after | the `Ɑː` rows, and the `Ɑː` half of the PRE entry after- → ·At·Fee·Tea·Utter·Roe |
| 5 | last | last ×3, at last, last-ditch → ·Low·At·See·Tea |
| 4 | at | at-home, at-homes, gentleman-at-arms, gentlemen-at-arms — ReadLex's weak `ət` → ·At·Tea |
| 3 | be | be VBB, be VBI, would-be → ·Bay |
| 3 | to | lean-to ×2, set-to → ·Tea |
| 3 | that | that AJ0, AV0, CJT → ·They·Tea |
| 2 | it | it PNP, as it were → ·It |
| 2 | is | is VBZ, that is → ·Zoo |
| 2 | mr | both rows → ·May·Roe |
| 2 | mrs | `ˈmɪsəz` and `ˈmɪsɪz` → ·May·Zoo |
| 1 | dr | → ·Day·Utter·Roe |
| 1 | always | → ·Awe·Low·Way·Utter·Zoo |
| 1 | was | → ·Way·Utter·Zoo |

lean-to and set-to are worth a second look, since the to in each is a lexicalised particle rather than the preposition. They stay, because ReadLex writes exactly the same particle with its own word sign in stand-to `stænd-ˈT`, talking-to `ˈtɔːkɪŋ-T` and to-do `T-ˈduː`; substituting here makes upstream's treatment of the pattern uniform rather than departing from it.

## The junior column

Per [#8][plan] the senior column is the default and junior is populated only where the Junior spelling genuinely differs at word level. After this ticket that is **five rows** — that ×3, always, was — and no others: the Manual's terminal, affix and prefix conventions are universal ([#2][rules]), the core eight are Junior-sanctioned, and the abbreviations are given in the Junior section.

The column obeys one invariant, which the validator checks: **a Junior spelling is exactly the spelling with the override left unapplied.** A junior form is never independently authored; it is what the rules alone produce. If a word ever needs a Junior spelling that is neither the Senior outline nor the plain rules output, the build fails and the model has to be revisited rather than quietly bent.

## Contractions, possessives, and the apostrophe

The Manual states almost nothing about apostrophes and demonstrates a great deal. Every instance in the whole text:

| Class | Apostrophe? | Evidence |
|---|---|---|
| possessive | **no** | "Possessive apostrophes are usually omitted without loss of meaning" ([§ Punctuation etc][punct], p.8); "··May·Roe ·Jay·Owe·No·Zoo·Zoo clearly means 'Mr Jones's': with one name-dot, no apostrophe" ([§ Terminal -es, -ed][es-ed], p.18); anybody's = ·Et·No·It·Bay·Ox·Day·It·Zoo (p.24); world/'s = ·Way·Utter·Roe·Low·Day·Zoo ([p.16][common]) |
| `n't` | **no** | all nine instances: can't, couldn't, don't, didn't, haven't, wouldn't in the §III list, plus running-text wasn't ·Way·Utter·Zoo·No·Tea, doesn't ·Day·Utter·Zoo·Utter·No·Tea and wouldn't ·Way·Day·No·Tea |
| verbal `'s` | **no** | She's = ·She·Zoo (p.23); the list gives its and it's one spelling, ·It·See |
| `'d` | **yes** | He'd = ·He’·Day (p.24) |
| `'ll` | **yes** | they'll = ·They·Eight’·Low (p.26), the ·Low being the listed will/'ll contraction |
| aphetic `'t` | **yes** | 'Twas = ’·Tea·Way·Ox·Zoo (p.26) |
| `'ve`, `'m`, `'re` | unattested | the Manual never writes one |

The sharpest datum is internal to a single six-line rhyme on p.26: **doesn't without an apostrophe and they'll with one, two lines apart.**

So the conditioning is not phonological and not about letter class — it is about whether the clitic's letters could be read as a continuation of the word. `n't` and `'s` add letters that are already ordinary word-final spellings, so they attach solid; `'d`, `'ll` and aphetic `'t` would be misread, so the apostrophe stays. The ruling for the unattested three is to follow `'d` and `'ll` and keep the apostrophe: I'm = ·I’·May, you've = ·Ye·Ooze’·Vie, we're = ·Way·Eat’·Utter·Roe. `contractions.tsv` records `'ll` = ’·Low and `n't` = ·No·Tea as its two `clitic` rows, each carrying the note that says what it was generalised from.

**Where the possessive meets the -es rule.** [`terminal-es-ed`][es-ed] already omits the separating vowel between the seven pairs the Manual names — SZ, ShZ, ChZ, JZ, ZZ, DD, TD — so a possessive after a sibilant is a bare ·Zoo with nothing before it, and Jones's comes out ·Jay·Owe·No·Zoo·Zoo. The -Z of a plural or possessive becoming -S after a voiceless consonant (cups = ·Key·Utter·Pea·See against cubs = ·Key·Utter·Bay·Zoo) needs no rule at all: ReadLex's IPA writes /s/ there already.

**The namer dot.** A standalone sign letter read as a *letter* needs the namer dot to cancel the word-sign reading ([quikscript.net/namer-dot-usage](https://www.quikscript.net/namer-dot-usage/)), and the Manual adds a nuance about a dotted title covering the name that follows. Both are rendering, so [#6][converter] implements them; this layer only guarantees that the sign is what the column contains.

## What the validator checks

The word-sign section of [`src/qslex/validate.py`](../src/qslex/validate.py) fails unless:

- every row in `word-signs.tsv` is reached by at least one corpus row — reached meaning the substitution actually consulted it, not merely that a corpus word matched — so a stale row cannot linger;
- every word that rewrites anything rewrites exactly as many rows as `EXPECTED_SIGN_CHANGES` pins, and no word rewrites rows without a pinned count;
- **every word that rewrites anything also has a `manual-spellings.tsv` row holding its spelling to the Manual.** A count alone does not pin a spelling: after has one `Æ` row and one `Ɑː` row per tag, so mistranscribing its outline as ·Ah·Fee·Tea·Utter·Roe would rewrite the same five rows and pass. A row that never rewrites needs no fixture, because ReadLex's own IPA already corroborates it;
- every corpus row for one of the core eight comes out as that word's sign;
- exactly `EXPECTED_JUNIOR_DIVERGENCES` rows carry a Junior spelling, and each of those is the spelling the rules alone produce;
- every `word` row in `contractions.tsv` names a word ReadLex actually has.

[manual]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html
[junior]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#junior-contractions
[senior]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#senior-contractions
[common]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#common-words
[es-ed]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-es-ed
[punct]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#punctuation-etc
[other]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#other-conventions
[spelling]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#spelling
[tips]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#writing-tips
[note]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#examples-note
[plan]: https://github.com/adiabatic/quikscript-lexicon/issues/8
[rules]: https://github.com/adiabatic/quikscript-lexicon/issues/2
[pipeline]: https://github.com/adiabatic/quikscript-lexicon/issues/4
[converter]: https://github.com/adiabatic/quikscript-lexicon/issues/6
