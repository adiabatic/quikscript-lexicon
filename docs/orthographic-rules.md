# Read’s orthographic rules

Quikscript spelling needs more than a transcription of the sounds. [`docs/ipa-to-qs.md`](ipa-to-qs.md) maps IPA segments to letters and stops there. Its section [What a segment mapping cannot do](ipa-to-qs.md#what-a-segment-mapping-cannot-do) lists the Manual’s terminal and affix conventions that a segment mapping cannot express, because they depend on the *spelling* of a suffix rather than on its sounds. This layer implements them.

Section III of the Manual is the complete list of these conventions: eighteen terminal rules and eight prefix rules. This layer implements them, the §II X-letter substitution, and one rule of this project’s own, `terminal-nt`. That rule generalizes the bare ·No·Tea that §III’s [contraction list][nt] and the gown-shop specimen write directly onto every `n't` stem ([Decisions](#decisions)).

Per [#8][plan], the Manual’s rules apply to every column, Junior as well as Senior: they are how Quikscript is spelled. The exception is `terminal-nt`, which applies only to the senior column. Its evidence is Senior writing, and the junior column keeps the vowel it drops.

Authority links go to the [AMS Manual transcription][manual]. Every letter-name spelling quoted below was extracted codepoint for codepoint from its PUA text, with the presentation-only ZWNJs removed.

## Artifacts

- `src/qslex/rules.py` has the rule engine and the twenty-seven rules. Each rule is a pure function of a `Context`: the Latin spelling, the POS tag, the quirk-normalized IPA, its tokens, and whether the entry ends with this word. Per-word decisions that a row’s own data cannot settle come from tables (`rule-words.tsv`, `x-decisions.tsv`, the word signs). No rule looks anything up in the corpus.
- `src/qslex/elements.py` finds the boundaries inside an entry. The word-sign layer uses the same split, so the two layers always agree on where an entry’s words begin and end ([One entry, several words](#one-entry-several-words)).
- `src/qslex/data/manual-spellings.tsv` is the table of Manual examples: 381 rows covering every rule, 137 of them spellings the Manual writes out itself. Twenty of the rows belong to the word-sign layer rather than to a rule ([`docs/word-signs.md`](word-signs.md)). Columns: `word`, `pos`, `column` (`senior`/`x-letter`), `kind` (`word`/`terminal`/`prefix`), `spelling`, `source`, `rule`, `note`.
- `src/qslex/data/rule-words.tsv` has per-word decisions for the five rules whose trigger the data cannot settle. It has 453 rows. Each is `apply` or `skip`, with an authority and a note.
- `src/qslex/data/x-decisions.tsv` has the ten words where matching each Latin `x` to a letter pair cannot place the X-letter.
- `src/qslex/manual.py` loads the Manual examples table. It rejects an unknown rule anchor, an unknown letter name, and a derived spelling with no note.

Run the checks:

```
make check
```

## What the rules do

Eleven of the twenty-seven rules rewrite no row that the lexicon spells. For every word those rules name, ReadLex’s IPA already gives the Manual’s spelling. The reason is that Read was standardizing a *variable unstressed vowel*, ReadLex writes that vowel as a schwa, and the segment mapping already sends schwa to ·Utter. The eleven rules are kept as normalizers: if a ReadLex row ever contradicts the Manual, the rule corrects it. The validator fails if a rule’s rewrite count changes, including to or from zero.

The expected rewrite count for each rule, counted over the rows the lexicon spells, is in `EXPECTED_RULE_CHANGES` in [`src/qslex/validate.py`](../src/qslex/validate.py). That is the only place the counts are recorded. `make validate` prints them rule by rule. What each rule does:

| Rule                                                                                                                                                                                                                                                                 | What it does                                                                                               |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| [`terminal-ing`][ing]                                                                                                                                                                                                                                                | affix -ing loses vowel-i: calling ·Key·Awe·Low·-ing                                                        |
| [`terminal-es-ed`][es-ed]                                                                                                                                                                                                                                            | the epenthetic vowel goes: kisses ·Key·It·See·Zoo                                                          |
| [`terminal-al-el-le-il`][al]                                                                                                                                                                                                                                         | vowel omitted before a final L: tribal ·Tea·Roe·I·Bay·Low                                                  |
| [`terminal-tion`][tion]                                                                                                                                                                                                                                              | vowel omitted before N: action ·At·Key·She·No                                                              |
| [`terminal-ess-est`][ess]                                                                                                                                                                                                                                            | ·Et, not ·Utter: highest ·He·I·Et·See·Tea                                                                  |
| [`prefix-con-com`][con]                                                                                                                                                                                                                                              | unstressed con-/com- lose the vowel: content (adj) ·Key·No·Tea·Et·No·Tea                                   |
| [`terminal-ally-able`][ally]                                                                                                                                                                                                                                         | -·Utter·Low·It, -·Utter·Bay·Low, -·Utter·Bay·Low·It                                                        |
| [`terminal-land-ment`][land]                                                                                                                                                                                                                                         | vowel omitted: England ·It·-ing·Gay·Low·No·Day                                                             |
| [`terminal-age`][age]                                                                                                                                                                                                                                                | -·Utter·Jay, but -·It·Jay after a -y root                                                                  |
| [`terminal-ward`][ward]                                                                                                                                                                                                                                              | contracted: eastward ·Eat·See·Tea·Way·Day                                                                  |
| [`terminal-en-on`][en-on]                                                                                                                                                                                                                                            | invariably -·Utter·No: chicken ·Cheer·It·Key·Utter·No                                                      |
| [`terminal-ain`][ain]                                                                                                                                                                                                                                                | unstressed -·Utter·No: captain ·Key·At·Pea·Tea·Utter·No                                                    |
| [`terminal-nt`][nt]                                                                                                                                                                                                                                                  | vowel omitted before -n't, in senior alone: doesn't ·Day·Utter·Zoo·No·Tea                                  |
| [`terminal-y`][yy]                                                                                                                                                                                                                                                   | the unstressed terminal vowel is ·It, a full ·Eat included: tilde ·Tea·It·Low·Day·It, algae ·At·Low·Gay·It |
| [`terminal-ia-ea`][ia]                                                                                                                                                                                                                                               | stressed -·Eat·Utter: European ·Ye·Ooze·Utter·Roe·Utter·Pea·Eat·Utter·No                                   |
| [`terminal-us-ous`][ous]                                                                                                                                                                                                                                             | invariably -·Utter·See: hippolytus                                                                         |
| [`terminal-ent-ance`][ent], [`terminal-er`][er], [`terminal-ier-ior`][ier], [`terminal-ful`][ful], [`prefix-un`][un], [`prefix-an-al-ar`][an], [`prefix-ob-of`][ob], [`prefix-be-de-re`][be], [`prefix-pre-pro`][pre], [`prefix-per-pur`][per], [`prefix-in-en`][in] | no-ops on this corpus; see below                                                                           |

Why the zero-count rules need no rewrites:

- `per-/pur-`: ɜː and ə both map to ·Utter, so the Manual’s “stressed or not” needs no rule.
- `in-/en-`: ReadLex writes en- words with ɪn (enquiry `ɪnˈkwaɪəri`), which matches the Manual’s “alike unless stressed”.
- `un-`: the mapping already gives the Manual’s form, including the doubled N of unknown `ˌʌnˈnəʊn`.
- `-ier/-ior`, and most of `-ia/-ea`: #1’s stressed/unstressed ɪə conditioning already handles them.
- `-ful`: ReadLex itself splits the adjective and adverb (`fəl`) from the noun (`fʊl`), as the Manual does. The four rows that cross that line are covered below.

## The six things the IPA cannot tell you

### 1. Which Latin suffix this is

The Manual’s own minimal pair settles this: **fashion is -·She·No but ashen is -·She·Utter·No**. Both end in /ʃən/, but the Manual spells the endings differently. So the Latin column is a required input to the pipeline, and the terminal rules are selected by matching the Latin spelling.

**At most one terminal rule applies to a word.** `terminal_for` returns the first rule in `TERMINAL_RULES` whose pattern matches. The order puts more specific endings first, and that order settles the interactions the issue asked about:

- `-ment` before `-ent` (settlement)
- `-tion` before `-en/-on` (fashion)
- `-age` before `-e` (manage)
- `-le` before `-e` (eagle)
- `-ier` before `-er` (carrier)

Every terminal pattern except `n't$` allows an optional trailing inflection, so the rule matches the ending before it without a separate pass: finals, villages, onwards. Nothing inflects an `n't`, so that pattern has no such group. The -ing rule accepts -ings, -ingly and -ingness in the same way (writings).

Two rules run outside that ordering, because they act further inside the word. `terminal-es-ed` can drop its vowel at any position. `terminal-ing` finds the rightmost ·It + ·-ing, so it can apply alongside a terminal: willingness = ·Way·It·Low·-ing·No·Et·See applies both -ing and -ness.

### 2. Whether -ing is an affix or a root

“Provided it is an affix and not a root, omit vowel-i.” No root -ing word is ever a present participle. So any form that **is, or ends in, something ReadLex tags `VVG`** is an affix. That test decides over 6,500 words mechanically, including compounds (bookkeeping ends in keeping). Roots ending in -y are exempt by the Manual’s own rule (carrying = ·Key·At·Roe·It·It·-ing).

The 251 words that the test cannot decide each have a per-word decision in `rule-words.tsv`, with an authority that gives the reason:

- `root`: an unanalyzable stem (bring, ceiling, farthing).
- `ling-suffix`: the diminutive -ling, whose /l/ belongs to the suffix (duckling, seedling, hireling).
- `compound`: the decision comes from a root-final element (bullring, anything, shoestring).
- `placename`: Ealing, Dorking, Nanning.
- `stem`: a real stem plus -ing (being, coloring, caravanning).
- `manual`: the three words the Manual writes itself.

The validator fails on any -ing word that neither the `VVG` test nor a `rule-words.tsv` row decides.

### 3. Whether the Latin -est/-ess is really the terminal

The Manual distinguishes this family from -us/-ous by writing vowel No. 28, ·Et. **The POS tag cannot be used as the condition.** ReadLex tags the Manual’s own example word `highest` AV0 as well as AJS. closest, earliest, fastest, lowest, nearest, fewest and several others also have AV0, PRP or DT0 rows beside their AJS rows, and nighest and soonest have no AJS row at all. So the rule applies on the Latin spelling, and the exceptions are listed in `rule-words.tsv`:

- 19 `skip` rows, all words where the -est/-ess is part of the root, not the suffix: the forest family, harvest, tempest, honest, modest, earnest, interest, Guinness, Furness.
- 4 `apply` rows: nighest and soonest, the two superlatives ReadLex never tags AJS, and burgess and mattress, which have no -ess morpheme at all.

The validator’s check for undecided words is based on the vowel. Read is standardizing a *variable* unstressed vowel, which ReadLex writes as schwa. If the vowel the rule would rewrite is ·It instead, that is evidence that the Latin -est/-ess is part of the root. The validator fails on such a word until `rule-words.tsv` decides it.

`-ess` also applies to words with no -ess morpheme (buttress, cypress, fortress, mattress, burgess). This is intended. Read’s rule is keyed to the Orthodox spelling (“Distinguished from the -us, ous terminal by writing vowel No. 28”), and phonology cannot separate these words from the rest.

Whether the vowel is unstressed in the first place is a separate question. The doubled-consonant `+` markers in keenness and goalless once gave the wrong answer to it: see **A `+` marker does not hide the word’s stress mark** below.

### 4. Whether be-, de- and re- are prefixes at all

The Manual gives unstressed be-/de-/re- as ·Bay·It-, ·Day·It-, ·Roe·It-. ReadLex already writes ɪ for every word the Manual names (begin `bɪˈɡɪn`, decide `dɪˈsaɪd`, receive `rɪˈsiːv`). But nothing in the data separates those words from Berlin, Bermuda, Denise, Rebecca and berserk, which only start with the same letters and whose schwa is correct.

So the rule applies on the Latin string, and every word it would rewrite has a decision in `rule-words.tsv`. All eighteen are placenames, given names or loanwords with no prefix, and each has a `not-the-prefix` skip. So the rule’s rewrite count of 0 means that ReadLex never contradicts the Manual on a real be-/de-/re- prefix. It does not mean the rule could not apply. A nineteenth word fails the validator until it has a decision.

### 5. Whether a terminal -y that ReadLex writes in full is stressed

Read decides this terminal by stress: “the dictionary suggests letter-·It No. 26, and leaves ·Eat No. 27 for distinction where the terminal is stressed”. ReadLex marks no stress inside an **unhyphenated** compound. [`docs/ipa-to-qs.md`](ipa-to-qs.md#where-the-mechanical-rule-breaks-and-the-override-file) already lists the same fault for reindeer against musk-deer. So honeybee `ˈhʌnɪbiː` and jubilee `ˈdʒuːbɪliː` match segment for segment. honeybee should keep the ·Eat of bee, and jubilee should take ·It.

Nothing else in the data separates them. Hyphenated compounds come out right without help: a hyphen starts a new chunk, and [rule 3’s fallback](ipa-to-qs.md#the-stress-rule-for-ɪə) treats a chunk with no stress mark as stressed (ash-key `ˈæʃ-kiː`, christmas-tree). The monosyllables bee, free, key and lee also come out right. The Shavian column does not help here: it writes 𐑰 for both carefree and algae. A rule may not look the ending up in the corpus either, because per-word decisions come from tables.

So the 159 element words (169 corpus rows) where an unstressed ·Eat falls on this terminal each have a decision in `rule-words.tsv`, under seven authorities:

- `compound` (21 skips): each note names the word the last element is. bumblebee and honeybee end in bee, carefree and icefree end in free, and the -tree, -key, -quay and -lee names work the same way.
- `readlex-stress-defect` (3 rows):
  - adoptee. Every other agentive -ee in ReadLex, from absentee to refugee, is marked final-stressed, so `əˈdɒptiː` is the outlier and its ·Eat stays.
  - squeegee and its plural. squeegee is the outlier among the -ee verbs, as explained below at the -ed/-ing boundary.
- `latin-plural`: the twenty -ae plurals, algae to vertebrae.
- `loan` (40 rows): twenty-three -ee loanwords, apogee to yippee, and the seventeen plurals of them that the corpus has.
- `orthographic`: aries, facie, rabies, scabies, series, specie, species, subspecies, superficies. These have no -y or -ee morpheme at all. The rule is keyed to the Orthodox spelling, on the same basis as -ess at burgess and mattress.
- `lexicalized`: maybe, wannabe and its plural, whose compound-final -be is reduced in speech.
- `not-the-terminal`: the plurals described in the next paragraph.

The validator fails on any word of that kind with no decision, including new ones that appear when the corpus changes.

A plural `-s` adds a second question. The terminal pattern has to allow an inflection, because Read’s terminal “certainly must be constant in spelling”: apogees cannot end in a letter apogee does not. But `-es` is also how English spells the plural of a word ending in silent `-e`, and how Greek and Latin spell endings of their own. theses is not these plus s, and vortices is not vortice plus s. precises is the s-form of precis, and this terminal never matches precis at all.

- Where the Latin has `-ys` or `-ies`, the spelling settles the question (latchkeys, rabies).
- Where it has `-es`, the vowel is the only evidence left. The vowel an English plural adds there is reduced, and `terminal-es-ed` has usually dropped it before this rule runs. So behind an `-es`, the rule rewrites only a full ·Eat.

Which kind of ·Eat it is still needs a per-word decision. 23 plurals repeat the decision of their singular: apogees as apogee, honeybees as honeybee, wannabes as wannabe, and crosstrees, which ends in the word tree although the corpus has no crosstree. 63 have `not-the-terminal`, because the ending belongs to the word: the classical plurals theses, crises, indices, vertices and oases, and the names hades, pisces and ecclesiastes.

The optional inflection group does not include `-ed` or `-ing`, here or at any other terminal. A terminal is keyed to the end of a word, and `-eed` does not show what precedes it. The corpus’s aniseed, seaweed and nosebleed end in the words seed, weed and bleed. A pattern wide enough to read squeegeed as squeegee plus d would also match those, and each would then need a decision saying its `-d` is not an inflection. So this terminal treats -ed and -ing as the rest of §III does: manage is -·Utter·Jay and managed keeps its ·It, and captain is -·Utter·No and captained keeps its ·It. Two lemmas have both an -ed/-ing form and a row this terminal matches: fricassee and squeegee. Their spellings are kept constant by hand, as Read’s “constant in spelling” requires.

fricassee needs nothing. ReadLex marks the verb final-stressed, so fricasseed and fricasseeing keep the ·Eat of the verb, and only the noun reduces. squeegee would have been spelled two ways. `ˈskwiːdʒiː` is the one -ee verb in ReadLex with a syllable before the terminal and no stress mark on it. agree, decree, disagree, foresee, fricassee, guarantee, oversee, referee and unsee are all final-stressed. Without a decision, the base form would have taken ·It, while squeegeed and squeegeeing, which the terminal does not match, kept ·Eat. Because every other -ee verb is final-stressed, the missing mark is treated as the defect. So squeegee has the `readlex-stress-defect` skip listed above, and every form of the word keeps ·Eat.

### 6. Where Orthodox spells the sounds with x

·Excite substitutes for ·Key·See and ·Exam for ·Gay·Zoo, “**but only where Orthodox spells these sounds with X**”. tax and tacks are homophones, and so are next and necks. The IPA cannot show the choice, so the lexicon stores the X-letter form in a `qs_x` column built from the senior spelling ([#8][plan]).

The substitution is made per **word** of the entry ([One entry, several words](#one-entry-several-words)). Where a word’s Latin has one `x` and its spelling has one ·Key·See or ·Gay·Zoo pair, the X-letter replaces that pair. A word with no such pair gets no X-letter and needs no decision: anxious (/ŋkʃ/), sexual (/kʃu/), luxury, faux, xenon and xylophone are all correctly left alone. `x-decisions.tsv` decides the ten words where this fails. They have either two x’s (xerox, executrix, vaxxed) or one x and several pairs (textbooks, waxworks, alexics).

**·Et applies only to a word-initial unstressed ex-.** The Manual’s rider says “·Et·Excite for Excite, Extreme, Expect with an initial vowel ·Et easier than ·It”. The rider offers ·Et as easier to write, and so concedes that the sound is ·It. The Manual’s own `sixty` = ·See·It·Excite·Tea·It keeps ·It, so the rider is not a general vowel rule. The senior column follows the IPA. ReadLex writes unstressed ex- as /ɪk/- or /ɪɡ/-, giving ·It·Key·See, and has ·Et only for a real DRESS vowel: next, text, texture, expert.

Word-initial means the start of the *word*, not of the entry. So in cross-examine and for example, the ·Et goes on a word that does not begin the entry. Unstressed means that the element’s IPA chunk does not begin with a ReadLex stress mark. The stress the tokenizer assigns is not used. corn-exchange `ˈkɔːRn-ɪkstʃeɪndʒ` has its one mark on corn, so the ex- of exchange is unstressed and takes the ·Et. exquisite `ˈɪkskwɪzɪt` has a mark on the ex- itself and keeps its ·It, as sixty does. [Rule 3’s fallback](ipa-to-qs.md#the-stress-rule-for-ɪə) is not used here. It treats a chunk with no stress mark as stressed, as the word would be on its own. That is right for the monosyllables and compound elements it was written for, and wrong for a polysyllable whose stress is not initial. Examples:

|               | senior                                         | `qs_x`                                        |
| ------------- | ---------------------------------------------- | --------------------------------------------- |
| expect        | ·It·Key·See·Pea·Et·Key·Tea                     | ·Et·Excite·Pea·Et·Key·Tea                     |
| exam          | ·It·Gay·Zoo·At·May                             | ·Et·Exam·At·May                               |
| next          | ·No·Et·Key·See·Tea                             | ·No·Et·Excite·Tea                             |
| sixty         | ·See·It·Key·See·Tea·It                         | ·See·It·Excite·Tea·It                         |
| exquisite     | ·It·Key·See·Key·Way·It·Zoo·It·Tea              | ·It·Excite·Key·Way·It·Zoo·It·Tea              |
| cross-examine | ·Key·Roe·Ox·See-·It·Gay·Zoo·At·May·It·No       | ·Key·Roe·Ox·See-·Et·Exam·At·May·It·No         |
| corn-exchange | ·Key·Awe·Roe·No-·It·Key·See·Cheer·Eight·No·Jay | ·Key·Awe·Roe·No-·Et·Excite·Cheer·Eight·No·Jay |
| tacks         | ·Tea·At·Key·See                                | —                                             |

Outside the §II rule statement, the Manual writes only three X-letter words out in full, all in the prose specimens on pages 24–25: next = ·No·Et·Excite·Tea, sixty-five = ·See·It·Excite·Tea·It-·Fee·I·Vie, and experiment = ·Et·Excite·Pea·Et·Roe·It·May·No·Tea. The lexicon reproduces next and experiment. ReadLex has no sixty-five entry, but the lexicon’s sixty and five together give the Manual’s spelling. experiment also applies `terminal-land-ment`, so it confirms that rule as well as the X-letter substitution.

No extra S-letter is needed for the C in excite or excess. ReadLex writes /ks/ once, so the spelling before substitution already has a single ·See for the X-letter to replace.

## One entry, several words

A terminal is keyed to the end of a word and a prefix to the start of one. 6,556 ReadLex entries contain a space or a hyphen. When the rules matched the whole entry string, a terminal could apply only to the last element and a prefix only to the first. Every element in between kept a vowel the Manual drops: adding-machine came out ·At·Day·**It**·-ing-·May·Utter·She·Eat·No, while adding on its own is ·At·Day·-ing ([#9][compound]). So the entry is now split into its words at every space and hyphen, and the rules run on each word.

The split is the same one the word-sign layer uses ([§ Phrase entries](word-signs.md#phrase-entries)), and it is the same code: [`src/qslex/elements.py`](../src/qslex/elements.py). The two layers therefore cannot disagree about where a boundary is. The alignment check matters here for the same reason it matters there. If the Latin parts and the spelling’s runs do not line up one for one, the whole entry is treated as one element. to-day has one spelled run and three Latin parts, and dhs has one Latin part and seven runs, so both stay whole instead of being spelled part by part. Splitting changes the spelling of 656 entries. 598 of them now spell the same as their elements put together, so `qs_converter_phrases.txt` does not need to list them.

**The vowel before a final L is dropped only at the end of the entry.** The Manual’s rider on that terminal says: “Where another syllable is added, the vowel sound before this L must be clearly pronounced and spelt in most cases: as it must be in — finally, orally, animality, initially, officially, levelling, devilry, caviller, rif(u)leman”. A following element adds a syllable in the same way a suffix does. So able-bodied is ·Eight·Bay·**Utter**·Low-·Bay·Ox·Day·It·Day where able alone is ·Eight·Bay·Low, and cable-car is ·Key·Eight·Bay·**Utter**·Low-·Key·Ah·Roe where cable alone is ·Key·Eight·Bay·Low.

This affects two rules and no others: [`terminal-al-el-le-il`][al], and the -able/-ible half of [`terminal-ally-able`][ally], which omits the same vowel in the same position. The -ally/-ably/-ibly half is not affected, because there the L is not final. The Manual’s own list of restorations (finally, orally, initially) is from that half. 199 compound entries keep a vowel this way that their element drops when it stands alone, so `qs_converter_phrases.txt` still has to list them.

**What the Manual shows, and what it does not.** The Manual writes seven hyphenated compounds out in Quikscript: gold-hunting, she-ass, under-jaw, high-bred and sixty-five in the Senior specimens, and Bo-peep and a-cock in the Junior ones. In every one, the element with a rule is already last, so none of them distinguishes running the rules per element from running them on the whole entry. ReadLex has no entry for any of them either. So the compound rows in `manual-spellings.tsv` are `derived`, one for each affected family, and each is checked against its element standing alone: adding-machine, air-conditioned, combination-lock, cribbage-board, gentleman-at-arms, chicken-house, witness-box, breeches-buoy, mountain ash, haywards heath, vice versa, feeding-bottle, and able-bodied and cable-car for the restored vowel.

**Compounds keep ReadLex’s pronunciation.** Splitting an entry changes which rules apply, not how it is pronounced. ReadLex gives some compounds a pronunciation their parts do not have: a la mode has ɑː where a has eɪ, aide-de-camp ends kɑːm, black-lead is `led` and not `liːd`, and bay-wreaths has a voiceless θs. This layer runs after the IPA and follows it, here as everywhere.

**Per-word decisions are keyed on the element, not on the entry.** When this change was made, 38 rows keyed on a compound were removed, because a row for the element already decided them. gas-ring, napkin-ring and wedding-ring all say what `ring` already says. Two rows were re-keyed onto the element they are about: barrow-in-furness to `furness`, and spring-mattress to `mattress`. Nine words that the split newly exposed were given decisions. One is `revoir` in au revoir. The other eight are -ing words that are not ReadLex entries in their own right, so they have no `VVG` tag (`circuiting` from short-circuiting, `poohing` from pooh-poohing, `ding` from ding-dong, and five more).

`x-decisions.tsv` has since been keyed per element as well ([#11][x-letter]). The X-letter substitution was the last rule still matched against the whole entry. The exercise-books row was removed in that change. Per element, exercise has one x and one pair. books has no x, so the substitution leaves its ·Key·See alone. The mechanical substitution now gives what the row used to record. The ten remaining rows are all single words. Because rows are keyed on the element, a row keyed `xerox` would also apply inside a compound containing xerox. No corpus entry shows this, so `tests/test_rules.py` tests it with a made-up row for the `box` of ballot-box.

## Decisions

**·Et is not a reducible vowel.** Where ReadLex writes ·Et in an unstressed syllable, it is recording a real DRESS vowel. The Manual’s counter-examples are of this kind: seamen -·May·Et·No against seaman -·May·No, and cement, Overland and unman against England, since “stressed vowels will be appropriately written”. Without this decision, content (noun) `ˈkɒntent` and comment `ˈkɒment` would both lose a vowel the Manual keeps. No rule rewrites ·Et.

The decision is about ·Et, No. 28. The code encodes it as `REDUCIBLE`, the set of ·It and ·Utter. That set also leaves out ·Eat, No. 27. ·Eat is a different letter, the FLEECE vowel, and the Manual’s DRESS argument says nothing about it. `Y_REDUCIBLE` in [`src/qslex/rules.py`](../src/qslex/rules.py) is `REDUCIBLE` plus ·Eat, and only `apply_y` uses it. So the vowel-normalizing rules rewrite an unstressed ·It or ·Utter, and terminal -y also rewrites an unstressed ·Eat. Behind an `-es` plural, terminal -y rewrites only ·Eat. Three rules instead choose between two vowels: -ia/-ea and -ier/-ior choose between ·It and ·Eat by stress, and -ful chooses between ·Utter and ·Foot by POS tag.

**Where the Manual gives a stressed and an unstressed form, the rules enforce only the unstressed one.** The Manual’s stressed forms describe what the stressed sound already gives. Enforcing them would break again (`əˈɡen`, whose -ain is not the terminal), company (`ˈkʌmpəni`, stressed but with ʌ, not ɒ) and present the verb (`prɪˈzent`, whose -ent is stressed). The exception is `terminal-ia-ea` and `terminal-ier-ior`, which write ·Eat for a stressed vowel and ·It for an unstressed one. Every -ia/-ea rewrite in the corpus is a stressed ·It becoming ·Eat, as in European.

**-ing stays bare after a prefix.** The Manual says to “spell the root fully after a prefix or with somewhat changed meaning: e.g., in — beings, undoing, unthinkingly, willingness, canning”. That forbids the *root contraction* (·Bay·-ing = being, ·Day·-ing = doing, ·Thaw·-ing = thinking). It does not forbid the affix rule, which is stated without conditions. So beings = ·Bay·Eat·-ing·Zoo and unthinkingly = ·Utter·No·Thaw·It·-ing·Key·-ing·Low·It. The root contractions are not in this column at all. Per [#8][plan], the §III contraction list is an optional converter layer. That is also why often stays ·Ox·Fee·Utter·No here instead of the Manual’s listed ·Ox·Fee·No.

The rider’s typography shows which of the two it restores. It underlines what the root contraction drops: the *e* of beings, the *o* of undoing, the *ink* of unthinkingly, the *wi* of willingness, the *ann* of canning. An affix vowel to be omitted is struck through instead, as in calling and writings, and bringing has both marks. The section’s own example table prints writings, a de-verbal noun plural, with the affix vowel struck, so a “changed meaning” does not keep that vowel. The reading that would keep it would also have to exempt canning from the rule stated one paragraph earlier. So the noun being is ·Bay·Eat·-ing, the same as the participle, and the plural is the beings the rider names.

[`docs/validation.md`](validation.md#three-gaps-in-the-rules) gives the whole argument and the one question it leaves open. The converter’s contraction layer has §III’s flat be/ing/en with no part-of-speech condition. The open question is whether it should apply to the noun senses of the six root-contraction-plus-affix rows in that layer, three of which the Manual’s Root Contractions plus Affix names. That layer writes into no column, and the Manual settles none of the six, so the question is left open.

**Lexicalized participles keep the affix rule; fully grammaticalized forms do not.** cunning, fleeting, scathing and excruciating are still participial in form and behavior, so the vowel goes. during has become a preposition with no participial function left, so it keeps the vowel. Each such word is decided by its own row in `rule-words.tsv`, not by a heuristic.

**-ally is written even where no vowel is spoken.** “These terminals should always be written as shown, even if a preceding penlift results.” ReadLex gives basically as `ˈbeɪsɪkli`, with no vowel between /k/ and /l/. The rule inserts one, giving ·Bay·Eight·See·It·Key·Utter·Low·It. This is the only rule that adds a letter.

**The epenthetic vowel is identified by its environment, not only by upstream’s tag.** ReadLex marks most -es/-ed sites with a capital `Ə`. But 86 rows have a plain `ə` in one of the seven pairs the Manual names: “Between these — SZ, ShZ, ChZ, JZ, ZZ, DD, TD — some kind of vowel has to be uttered”. englishes `ˈɪŋɡlɪʃəz`, cashboxes, torches and handedness are examples: the same site written two ways. The rule reads the environment, so those rows come out right. The inconsistent tagging is an upstream defect that should be fixed at the source ([#7][quirks]).

**`terminal-es-ed` removes a tagged `Ə` whatever the Latin ending.** The rest of `terminal-es-ed` applies only when the Latin ends in -es or -ed, but the tagged vowel is removed either way. Seven entries need this: ltd, assoc, h's, s's, x's, blesséd and long-period all have a capital `Ə` upstream without the ending that names the rule.

**The -y terminal applies to loanwords.** Every rewrite it makes from a schwa is a foreign word whose final -e ReadLex pronounces: tilde, krone, lasagne, recife, hygge, firenze, karlsruhe, campagne, pologne, eiche, clotilde, bode, and the vice of vice versa. Read’s rule covers this case: “though the actual sound of terminal -y varies in pronunciation, it certainly must be constant in spelling”. So they take ·It. The -ae plurals and the -ee loans follow the same argument, applied to a vowel that ReadLex writes in full.

**The -y terminal is decided by stress, not by the vowel length ReadLex writes.** “Though the actual sound of terminal -y varies in pronunciation, it certainly must be constant in spelling. The dictionary suggests letter-·It No. 26, and leaves ·Eat No. 27 for distinction where the terminal is stressed.” Read names two conditions, and neither is vowel length: constant spelling when unstressed, ·Eat when stressed.

- An unstressed `iː` here is inside the rule. algae, apogee, jubilee, formulae and maybe take ·It, as tilde does.
- legatee `ˌleɡəˈtiː`, lessee and payee keep ·Eat, because they are stressed.
- bee, free, key and lee keep ·Eat, because a monosyllable with no stress mark counts as stressed.

fricassee is the minimal pair, and the corpus has it in both numbers. The noun `ˈfrɪkəsiː` takes ·It, and the verb `ˌfrɪkəˈsiː` keeps ·Eat, which is the distinction Read reserves ·Eat for. The plurals split the same way, from one `apply` row: fricassees NN2 follows the noun, and fricassees VVZ follows the verb. An `apply` row only removes a word from the validator’s list of undecided words. Whether the vowel is rewritten depends on the stress mark.

No other rule’s behavior changes, because only `apply_y` uses `Y_REDUCIBLE`. The rewrite goes one way only: a stressed ·It is never changed to ·Eat. So coolly, wholly, vilely, outlawry and the de of de luxe are unchanged.

**-ful follows the POS tag, and two ReadLex rows are exempted.** The Manual gives the adjective as -·Fee·Utter·Low and the noun as -·Fee·**Foot**·Low, so the rule uses the tag. Four ReadLex rows cross that line:

- brimful `ˌbrɪmˈfʊl` needs no exception, because its -ful is stressed.
- fully `ˈfʊli` needs none, because its ful is the root, not the affix.
- cupful and spadeful are noun measures that ReadLex also tags AJ0. That is an upstream tagging defect, so each has a `skip` row (`readlex-pos-defect`) and keeps the ·Foot the Manual gives it.

**A `+` marker does not hide the word’s stress mark.** ReadLex writes a hiatus `+` at a morpheme boundary with a doubled consonant. So keenness is `ˈkiːn+nəs` and goalless is `ˈɡəʊl+ləs`. The terminal’s vowel then falls after a marker that, as [`docs/ipa-to-qs.md`](ipa-to-qs.md) says, has no orthographic meaning and is spelled as nothing. Read as a chunk of its own, `nəs` has no stress mark, so the fallback for chunks without a mark treated it as stressed. The rules rewrite only unstressed vowels, so they left it alone, and those words kept an ·Utter that every -ness and -less without a `+` had already lost. The same marker occurs in -est superlatives: freest `ˈfriː+əst` and beefiest `ˈbiːfi+əst`, against driest and happiest, which have no `+`.

So the fallback is limited, by phonology rather than morphology. A `+` tail whose only vowel is a schwa has no vowel that could be stressed, so it is not treated as stressed. Every other `+` tail is left alone, because a `+` can also join two words, as in bookkeeping, clipboard, courtship and sweatshirt. There the second element has a vowel of its own and stays stressed. The test does not ask whether a tail is a suffix or a compound element, and the two groups do not line up with it. coolly and soullessly are suffixes it leaves stressed, and the -shire placenames are compound elements it demotes. Neither change alters a spelling. The [rider on rule 3](ipa-to-qs.md#the-stress-rule-for-ɪə) states the test and works through both sides.

**Edward is contracted.** `terminal-ward` applies to any unstressed -ward syllable, including the personal name (`ˈedwəRd` → ·Et·Day·Way·Day). The Manual’s one caution, “the stressed syllables ‘for—, on—,’ should not be contracted”, is about the stem, not the terminal. The Manual still writes forward and onwards contracted at the -ward, keeping their stressed ·Fee·Awe·Roe and ·Ox·No before it. The two `manual-spellings.tsv` rows record this.

- ward and wards on their own are exempt, because the rule needs a stem before the suffix.
- toward keeps its ·Awe·Roe before the stress test is applied. The rule contracts ·Way·**Utter**·Roe·Day, and a stressed -ward syllable is ·Way·**Awe**·Roe·Day (`təˈwɔːRd`), so the letters do not match.

The stress test is kept because ·Utter spells /ʌ/ and /ɜː/ as well as schwa, so a stressed -ward with ·Utter is possible, and the Manual says nothing about it. Leaving it uncontracted applies the decision **Where the Manual gives a stressed and an unstressed form, the rules enforce only the unstressed one** above. No ReadLex row has such a syllable, so `tests/test_rules.py` tests it with a made-up spelling.

**The vowel before -n't is elided in the senior column, and kept in the junior one.** Every `n't` entry that [§III’s contraction list][nt] prints writes a bare ·No·Tea directly onto the stem: can't ·Key·No·Tea, couldn't ·Key·Day·No·Tea, don't ·Day·No·Tea, didn't ·Day·Day·No·Tea, haven't ·He·Vie·No·Tea, wouldn't ·Way·Day·No·Tea. The gown-shop specimen writes the same bare ·No·Tea in running-text wasn't, a word the list does not include.

`terminal-nt` generalizes that to the senior spelling. Like every other terminal, it is keyed to the Latin (`n't`). It drops the unstressed ·Utter from ReadLex’s `ənt`, so doesn't is ·Day·Utter·Zoo·No·Tea and shouldn't is ·She·Foot·Day·No·Tea. ain't, aren't, can't, daren't, don't, mayn't, shan't, weren't and won't have no vowel there to drop, and pass through unchanged. For can't and don't, ReadLex and §III agree. The elision is not itself a §III contraction, because the stem stays spelled in full: haven't keeps the ·At that the listed ·He·Vie·No·Tea drops. So the decision that keeps people at ·Pea·Eat·Pea·Low still holds.

This is the only rule that does not apply to the junior column. Per [#8][plan], the Manual’s stated conventions are spelling and apply to both grades. The Manual never states the elision. It only writes it, and it writes it by grade. The §III list and the Senior gown-shop have a bare ·No·Tea. The Junior bo-peep keeps the vowel in doesn't ·Day·Utter·Zoo·Utter·No·Tea. So the junior column follows the Junior specimen. Every row the rule rewrites has a `qs_junior` with the vowel kept (for wasn't, on the ·Way·Ox outline it already had). Each specimen is reproduced by its own grade’s column. An earlier decision grouped the elision with the §III contractions, where it was written into no column and the gown-shop wasn't was a `differs`. Splitting it by grade matches what the Manual’s two specimens write.

## Where the Manual examples come from

`manual-spellings.tsv` records three kinds of row:

- What the Manual itself writes (`source=manual`, 137 rows).
- What this project derives for a spelling the Manual does not write out (`source=derived`, 243 rows). Each has a note saying what the rule changed.
- One `modernised` row. The Manual spells visual ·Vie·It·**Zoo·Ye**·Ooze·Utter·Low, with its 1966 /zj/. ReadLex has ʒ, and the senior column follows the IPA, giving ·Vie·It·**J’ai**·Ooze·Utter·Low. `docs/ipa-to-qs.md` records the same decision under weak u.

Two rows have spellings that cannot be checked against the pipeline, because ReadLex has no such entry. One is **jones's**: the Manual writes Mr Jones's as ··May·Roe ·Jay·Owe·No·Zoo·Zoo, with one name-dot and no apostrophe. The other is **sixty-five**. `EXPECTED_MANUAL_ABSENT` in validate.py makes a third such row fail the validator.

Where the Manual and ReadLex disagree about a word’s *pronunciation* rather than its spelling rule, the table records the disagreement instead of inventing a spelling. The clearest case is sheaths. The Manual gives the verb as -·They·Zoo and the noun as -·Thaw·See, but ReadLex has only `ʃiːðz`, the voiced form, under NN2.

## What the validator checks

The rules section of [`src/qslex/validate.py`](../src/qslex/validate.py) runs over every corpus row and fails unless:

- every rule rewrites as many rows as its entry in `EXPECTED_RULE_CHANGES`, and that table has an entry for every rule and for nothing else, so a deleted rule cannot leave its entry behind;
- `terminal-nt` stays out of the junior column: its rewrites and the word-level sign cases are the only rows with a Junior spelling. Their number must equal `EXPECTED_JUNIOR_DIVERGENCES`, and each Junior spelling must equal the spelling with the word signs unapplied and `terminal-nt` not applied ([`docs/word-signs.md`](word-signs.md#what-the-validator-checks));
- every terminal matches at least one word. This is counted per element, so a terminal that only ever matches the end of a word inside a compound still passes. The ten rules that are not terminals (-es/-ed, -ing and the eight prefixes) have no pattern to count matches for, because each decides inside its own `apply` function instead of matching the end of the Latin. They are checked by their expected counts and by the undecided-word check below;
- every Manual example word is reproduced, and exactly two are missing from ReadLex;
- every row in `rule-words.tsv` and `x-decisions.tsv` is used. A row counts as used only when the rule consulted it: the rule applied under an `apply` row, or a `skip` row stopped it. It does not count if some corpus entry merely has the same key. So the validator fails on any row that no longer matches anything;
- no -ing, -est/-ess, -ful, -y, be-/de-/re- or X-letter decision is left undecided;
- no X-letter is written for a word with no `x` in it, and no word whose `x-decisions.tsv` row says it takes no X-letter still has a ·Key·See or ·Gay·Zoo pair in its own run.

[manual]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html
[plan]: https://github.com/adiabatic/quikscript-lexicon/issues/8
[quirks]: https://github.com/adiabatic/quikscript-lexicon/issues/7
[compound]: https://github.com/adiabatic/quikscript-lexicon/issues/9
[x-letter]: https://github.com/adiabatic/quikscript-lexicon/issues/11
[es-ed]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-es-ed
[ing]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-ing
[al]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-al-el-le-il
[ally]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-ally-able
[tion]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-tion
[en-on]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-en-on
[ent]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-ent-ance
[land]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-land-ment
[nt]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#senior-contractions
[ous]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-us-ous
[ess]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-ess-est
[er]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-er
[ier]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-ier-ior
[ia]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-ia-ea
[yy]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-y
[ain]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-ain
[age]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-age
[ward]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-ward
[ful]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-ful
[con]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#prefix-con-com
[un]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#prefix-un
[an]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#prefix-an-al-ar
[ob]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#prefix-ob-of
[be]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#prefix-be-de-re
[pre]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#prefix-pre-pro
[per]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#prefix-per-pur
[in]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#prefix-in-en
