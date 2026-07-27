# Read's orthographic rules

Quikscript spelling is not naive transcription. [`docs/ipa-to-qs.md`](ipa-to-qs.md) maps IPA segments to letters and stops there, with a section — [What a segment mapping cannot do](ipa-to-qs.md#what-a-segment-mapping-cannot-do) — listing the Manual's terminal and affix conventions as structurally out of reach, because they are keyed to the *spelling* of a suffix rather than to its sounds. This is the layer that owns them.

Section III of the Manual is the complete inventory: eighteen terminal rules and eight prefix rules, plus the §II X-ligature substitution. Per [#8][plan] these are not Senior-only — they are simply how Quikscript is spelt, in every column. Authority links go to the [AMS Manual transcription][manual]; every letter-name spelling quoted below was extracted codepoint-for-codepoint from its PUA text, with the presentation-only ZWNJs stripped.

## Artifacts

- `src/qslex/rules.py` — the engine and the twenty-six rules. Pure functions over a `Context` of (Latin spelling, POS, quirk-normalised IPA, tokens, and whether the entry ends with this word); the rulings a single row cannot make for itself come from declared tables, not from corpus lookups inside a rule.
- `src/qslex/elements.py` — where an entry's boundaries are. One split into elements, shared with the word-sign layer, so the two cannot disagree about them ([One entry, several words](#one-entry-several-words)).
- `src/qslex/data/manual-spellings.tsv` — the fixture: 380 rows covering every rule, 136 of them spellings the Manual writes out itself. Twenty belong to the word-sign layer rather than to a rule ([`docs/word-signs.md`](word-signs.md)). Columns: `word`, `pos`, `column` (`senior`/`ligature`), `kind` (`word`/`terminal`/`prefix`), `spelling`, `source`, `rule`, `note`.
- `src/qslex/data/rule-words.tsv` — per-word rulings for the five rules whose trigger the data cannot settle: 453 rows, each `apply` or `skip` with an authority and a note.
- `src/qslex/data/x-ligatures.tsv` — the ten words where the mechanical Latin-`x` ↔ letter-pair alignment cannot place the ligature by itself.
- `src/qslex/manual.py` — the fixture loader, which rejects an unknown rule anchor, an unknown letter name, or a derived spelling with no note.

Run the proofs:

```
make check
```

## What the rules actually do

The headline finding is that **eleven of the twenty-six rules never rewrite anything**. ReadLex's IPA already yields the Manual's spelling for every word those rules name, because Read was standardising a *variable unstressed vowel* and ReadLex writes that vowel as a schwa which the segment mapping already sends to ·Utter. They ship anyway, as normalisers: a ReadLex row that ever contradicts the Manual gets corrected rather than passed through, and the validator pins each rule's rewrite count so a rule that stops mattering — or starts — is visible.

How many rows each rule rewrites, counted over the rows the lexicon spells, is pinned in `EXPECTED_RULE_CHANGES` in [`src/qslex/validate.py`](../src/qslex/validate.py), which is the only place to read those counts; `make validate` prints the tally rule by rule. What each one does:

| Rule | What it does |
|---|---|
| [`terminal-ing`][ing] | affix -ing loses vowel-i: calling ·Key·Awe·Low·Oolong |
| [`terminal-es-ed`][es-ed] | the epenthetic vowel goes: kisses ·Key·It·See·Zoo |
| [`terminal-al-el-le-il`][al] | vowel omitted before a final L: tribal ·Tea·Roe·I·Bay·Low |
| [`terminal-tion`][tion] | vowel omitted before N: action ·At·Key·She·No |
| [`terminal-ess-est`][ess] | ·Et, not ·Utter: highest ·He·I·Et·See·Tea |
| [`prefix-con-com`][con] | unstressed con-/com- lose the vowel: content (adj) ·Key·No·Tea·Et·No·Tea |
| [`terminal-ally-able`][ally] | -·Utter·Low·It, -·Utter·Bay·Low, -·Utter·Bay·Low·It |
| [`terminal-land-ment`][land] | vowel omitted: England ·It·Oolong·Gay·Low·No·Day |
| [`terminal-age`][age] | -·Utter·Jay, but -·It·Jay after a -y root |
| [`terminal-ward`][ward] | contracted: eastward ·Eat·See·Tea·Way·Day |
| [`terminal-en-on`][en-on] | invariably -·Utter·No: chicken ·Cheer·It·Key·Utter·No |
| [`terminal-ain`][ain] | unstressed -·Utter·No: captain ·Key·At·Pea·Tea·Utter·No |
| [`terminal-y`][yy] | the unstressed terminal vowel is ·It, a full ·Eat included: tilde ·Tea·It·Low·Day·It, algae ·At·Low·Gay·It |
| [`terminal-ia-ea`][ia] | stressed -·Eat·Utter: European ·Ye·Ooze·Utter·Roe·Utter·Pea·Eat·Utter·No |
| [`terminal-us-ous`][ous] | invariably -·Utter·See: hippolytus |
| [`terminal-ent-ance`][ent], [`terminal-er`][er], [`terminal-ier-ior`][ier], [`terminal-ful`][ful], [`prefix-un`][un], [`prefix-an-al-ar`][an], [`prefix-ob-of`][ob], [`prefix-be-de-re`][be], [`prefix-pre-pro`][pre], [`prefix-per-pur`][per], [`prefix-in-en`][in] | no-ops on this corpus; see below |

The zeroes are not idle. `per-/pur-` is automatic because ɜː and ə both map to ·Utter, so the Manual's "stressed or not" needs no rule. `in-/en-` is automatic because ReadLex writes en- words with ɪn (enquiry `ɪnˈkwaɪəri`), which is exactly the Manual's "alike unless stressed". `un-` is automatic including the doubled N of unknown `ˌʌnˈnəʊn`. `-ier/-ior` and most of `-ia/-ea` were already settled by #1's stressed/unstressed ɪə conditioning. `-ful` is automatic because ReadLex itself splits the adjective and adverb (`fəl`, 246 rows) from the noun (`fʊl`), exactly as the Manual does; the four rows that cross that line are handled below.

## The six things the IPA cannot tell you

### 1. Which Latin suffix this is

The Manual's own minimal pair settles the question: **fashion is -·She·No but ashen is -·She·Utter·No**, identical /ʃən/, opposite treatment. So the Latin column is a pipeline input, not a convenience, and the terminal rules are selected by matching the Latin spelling.

Terminal rules are **mutually exclusive**: exactly one owns the end of a word, chosen by taking the first match in a fixed order that runs longest and most specific first. That order is what resolves the interactions the issue asked about — `-ment` beats `-ent` (settlement), `-tion` beats `-en/-on` (fashion), `-age` beats `-e` (manage), `-le` beats `-e` (eagle), `-ier` beats `-er` (carrier). Every pattern carries an optional trailing inflection group, so a rule sees through a plural without a separate pass: finals, villages, onwards, writings.

Two rules sit outside that competition because they attach further in: `terminal-es-ed` (position-free) and `terminal-ing`, which finds the rightmost ·It + ·Oolong and can therefore fire alongside a terminal — willingness = ·Way·It·Low·Oolong·No·Et·See applies both -ing and -ness.

### 2. Whether -ing is an affix or a root

"Provided it is an affix and not a root, omit vowel-i." No root -ing word is ever a present participle, so any form that **is, or ends in, something ReadLex tags `VVG`** is an affix by construction — that decides 6,500-odd words mechanically, including compounds (bookkeeping ends in keeping). Roots ending in -y are exempt by the Manual's own rule (carrying = ·Key·At·Roe·It·It·Oolong).

The 251 words that test cannot decide are ruled on one at a time in `rule-words.tsv`, with an authority saying why: `root` (an unanalysable stem — bring, ceiling, farthing), `ling-suffix` (the diminutive -ling, whose /l/ belongs to the suffix — duckling, seedling, hireling), `compound` (inherits from a root-final element — bullring, anything, shoestring), `placename` (Ealing, Dorking, Nanning), `stem` (a real stem plus -ing — being, coloring, caravanning), and `manual` for the three the Manual writes itself. The validator fails on any -ing word that is neither decided mechanically nor ruled on here, so the residue cannot silently grow.

### 3. Whether the Latin -est/-ess is really the terminal

The Manual distinguishes this family from -us/-ous by writing vowel No. 28 ·Et. But **the POS tag is not a usable gate**: ReadLex tags the Manual's own example word `highest` as AV0 as well as AJS, and tags closest, earliest, fastest, lowest, nearest, fewest and a dozen more as AV0/PRP/DT0 only. So the rule fires on the Latin spelling and the exceptions are enumerated: 19 `skip` rulings, all of them words where the -est/-ness is the root rather than the suffix (the forest family, harvest, tempest, honest, modest, earnest, interest, Guinness, Furness), plus 4 `apply` rulings — two superlatives that survive an AJS gate's absence, and burgess and mattress, which have no -ess morpheme at all.

The validator's residue check is keyed on the vowel: Read is standardising a *variable* unstressed vowel, which ReadLex writes as schwa, so a rewrite starting from ·It is evidence that the Latin string is the root and demands a ruling before it is allowed through.

`-ess` fires on words with no -ess morpheme at all (buttress, cypress, fortress, mattress, burgess). That is deliberate — Read's rule is explicitly keyed to the Orthodox spelling ("Distinguished from the -us, -ous terminal by writing vowel No. 28"), and phonology cannot separate them.

Whether the vowel arrives reducible at all is a separate question, and the doubled-consonant seams of keenness and goalless once answered it wrongly: see **A `+` seam does not hide the word's stress mark** below.

### 4. Whether be-, de- and re- are prefixes at all

The Manual gives unstressed be-/de-/re- as ·Bay·It-, ·Day·It-, ·Roe·It-, and ReadLex already writes ɪ for every word it names (begin `bɪˈɡɪn`, decide `dɪˈsaɪd`, receive `rɪˈsiːv`). But nothing in the data separates those from Berlin, Bermuda, Denise, Rebecca and berserk, which merely start with the same letters and whose schwa is correct.

So the rule fires on the Latin string and every word it would rewrite is ruled on: all eighteen turn out to be placenames, given names or loanwords with no prefix, each carrying a `not-the-prefix` skip. Its rewrite count of 0 therefore means something — ReadLex never contradicts the Manual on a genuine be-/de-/re- prefix — rather than being an artefact of a rule that could not fire. Any nineteenth word fails the build until someone rules on it.

### 5. Whether a terminal -y that ReadLex writes in full is stressed

Read's discriminator for this terminal is the stress — "the dictionary suggests letter-·It No. 26, and leaves ·Eat No. 27 for distinction where the terminal is stressed" — and ReadLex marks no stress inside an **unhyphenated** compound, which is the same fault [`docs/ipa-to-qs.md`](ipa-to-qs.md#where-the-mechanical-rule-breaks-and-the-override-file) already tabulates for reindeer against musk-deer. So honeybee `ˈhʌnɪbiː` and jubilee `ˈdʒuːbɪliː` are the same shape segment for segment, and the one keeps the ·Eat its own bee carries while the other takes ·It.

Nothing else separates them. The hyphenated compounds come out right on their own, because a hyphen opens a chunk of its own that [rule 3's fallback](ipa-to-qs.md#the-stress-rule-for-ɪə) calls stressed (ash-key `ˈæʃ-kiː`, christmas-tree), as do the monosyllables bee, free, key and lee; and the Shavian column is no oracle here, writing 𐑰 for carefree and algae alike. A rule may not look the tail up in the corpus either — the rulings a single row cannot make for itself come from declared tables. So the 159 element words where an unstressed ·Eat lands on this terminal, over 169 corpus rows, are ruled on one at a time, under seven authorities: `compound` (21 skips, each naming the word the last element is — bumblebee and honeybee are bee, carefree and icefree are free, the -tree, -key, -quay and -lee names likewise), `readlex-stress-defect` (3 rows: adoptee, where every other agentive -ee in ReadLex is marked final-stressed, from absentee to refugee, so `əˈdɒptiː` is the outlier and its ·Eat stands, and squeegee with its plural, the outlier among the -ee verbs, argued at the `-ed`/`-ing` seam below), `latin-plural` (the twenty -ae plurals, algae to vertebrae), `loan` (40 rows: twenty-three -ee loanwords, apogee to yippee, and the seventeen plurals of them the corpus carries), `orthographic` (aries, facie, rabies, scabies, series, specie, species, subspecies, superficies — no -y or -ee morpheme at all, keyed to the Orthodox spelling on the same footing as -ess at burgess and mattress), `lexicalised` (maybe, wannabe and its plural, whose compound-final -be is reduced in speech), and `not-the-terminal` for the plurals in the next paragraph. The validator fails on any word of that shape with no ruling, so the residue cannot silently grow when the corpus moves.

A plural `-s` doubles that question rather than settling it. Every terminal pattern sees through an inflection and this one has to, because Read's terminal "certainly must be constant in spelling": apogees cannot end in a letter apogee does not. But an `-es` is also how English spells the plural of a silent `-e` and how Greek and Latin spell an ending of their own — theses is not these plus s, vortices is not vortice plus s, and precises is the s-form of precis, whose own ·Eat this terminal never reaches at all. Where the Latin says `-y` or `-ie` it settles it (latchkeys, rabies); where it says `-es` it does not, and the vowel is the only remaining evidence: what an English plural adds there is a reduced one, which `terminal-es-ed` has usually dropped before this rule runs, so behind an `-es` the rule takes a full ·Eat and nothing else. Which kind of ·Eat that is stays a ruling — 23 of them repeat the ruling their own singular carries (apogees as apogee, honeybees as honeybee, wannabes as wannabe, and crosstrees, which ends in the word tree though the corpus has no crosstree), and 63 carry `not-the-terminal`, the ending being the word's own: the classical plurals theses, crises, indices, vertices, oases, and the names hades, pisces, ecclesiastes.

An `-ed` or an `-ing` is where the seeing-through stops, here as at every other terminal. A terminal is keyed to the end of a word, and `-eed` is not an ending that says what precedes it: the corpus's aniseed, seaweed and nosebleed end in the words seed, weed and bleed, so a pattern wide enough to read squeegeed as squeegee plus d would claim those too and then have to be told one at a time that their `-d` is no inflection. The seam is therefore left where the rest of §III leaves it — manage is -·Utter·Jay and managed keeps its ·It, captain is -·Utter·No and captained keeps its ·It — and the two lemmas that carry both an -ed/-ing form and a row this terminal reaches, fricassee and squeegee, are held to Read's "constant in spelling" by hand.

fricassee needs nothing: ReadLex marks the verb final-stressed, so fricasseed and fricasseeing keep the ·Eat the verb keeps, and only the noun reduces. squeegee would have split. `ˈskwiːdʒiː` is the one -ee verb in ReadLex with a syllable before the terminal and no mark on it — agree, decree, disagree, foresee, fricassee, guarantee, oversee, referee and unsee are unanimously final-stressed — so the base would have taken ·It while squeegeed and squeegeeing, out of the terminal's reach, kept ·Eat. Unanimous is what makes the mark the outlier rather than the word, so squeegee is the `readlex-stress-defect` skip above and the whole paradigm keeps ·Eat.

### 6. Where Orthodox spells the sounds with x

·Excite substitutes for ·Key·See and ·Exam for ·Gay·Zoo, "**but only where Orthodox spells these sounds with X**". tax and tacks are homophones; next and necks are homophones. The choice is unrecoverable from IPA, so the lexicon stores the ligature form rather than deriving it, in a `qs_x` column built on top of senior ([#8][plan]).

The alignment is mechanical where it can be, and it is per **word** of the entry ([One entry, several words](#one-entry-several-words)): one `x` in a word's Latin, one ·Key·See or ·Gay·Zoo pair in that word's spelling, substitute there. A word with no such pair gets no ligature and needs no ruling — anxious (/ŋkʃ/), sexual (/kʃu/), luxury, faux, xenon, xylophone are all correctly left alone. The ten words where that fails — two x's (xerox, executrix, vaxxed) or one x and several pairs (textbooks, waxworks, alexics) — are ruled on in `x-ligatures.tsv`.

**·Et is scoped to a word-initial unstressed ex-.** The Manual's rider — "·Et·Excite for Excite, Extreme, Expect with an initial vowel ·Et easier than ·It" — is a convenience that concedes ·It as the sound, and the Manual's own `sixty` = ·See·It·Excite·Tea·It keeps ·It, so it is not a blanket vowel rule. The senior column simply follows the IPA (ReadLex has unstressed ex- as /ɪk/-/ɪɡ/-, giving ·It·Key·See, with ·Et only for genuine DRESS: next, text, texture, expert).

Word-initial means the *word* and not the entry, so cross-examine and for example take the ·Et on a word that is not the one the entry begins with. Unstressed means ReadLex's own mark at the head of that element's chunk, and not the stress the tokenizer reads off it: corn-exchange `ˈkɔːRn-ɪkstʃeɪndʒ` writes its one mark on corn, which leaves the ex- of exchange unstressed and takes the ·Et, while exquisite `ˈɪkskwɪzɪt` marks the ex- itself and keeps its ·It, as sixty does. [Rule 3's fallback](ipa-to-qs.md#the-stress-rule-for-ɪə) answers a different question — it reads a mark-less chunk as a word keeping the stress it has standing alone, which is right for the monosyllables and compound elements it was written for and wrong for a polysyllable whose own mark is not initial — so this rider asks the narrower one instead of widening that. Concretely:

| | senior | `qs_x` |
|---|---|---|
| expect | ·It·Key·See·Pea·Et·Key·Tea | ·Et·Excite·Pea·Et·Key·Tea |
| exam | ·It·Gay·Zoo·At·May | ·Et·Exam·At·May |
| next | ·No·Et·Key·See·Tea | ·No·Et·Excite·Tea |
| sixty | ·See·It·Key·See·Tea·It | ·See·It·Excite·Tea·It |
| exquisite | ·It·Key·See·Key·Way·It·Zoo·It·Tea | ·It·Excite·Key·Way·It·Zoo·It·Tea |
| cross-examine | ·Key·Roe·Ox·See-·It·Gay·Zoo·At·May·It·No | ·Key·Roe·Ox·See-·Et·Exam·At·May·It·No |
| corn-exchange | ·Key·Awe·Roe·No-·It·Key·See·Cheer·Eight·No·Jay | ·Key·Awe·Roe·No-·Et·Excite·Cheer·Eight·No·Jay |
| tacks | ·Tea·At·Key·See | — |

The Manual writes only three ligature words out in full anywhere outside the §II rule statement, all in the prose specimens on pages 24–25, and **the generator reproduces all three**: next = ·No·Et·Excite·Tea, sixty-five = ·See·It·Excite·Tea·It-·Fee·I·Vie, and experiment = ·Et·Excite·Pea·Et·Roe·It·May·No·Tea — the last of which also applies `terminal-land-ment`, so it is independent confirmation of that rule as well as of the ligature.

No superfluous S-letter is needed for the C in excite or excess: ReadLex writes /ks/ once, so the naive spelling already has a single ·See for the ligature to absorb.

## One entry, several words

A terminal is keyed to the end of a word and a prefix to the start of one, and 6,556 ReadLex entries carry a space or a hyphen. Matching the whole entry string therefore left a terminal for the last element only and a prefix for the first, and every element in between kept a vowel the Manual drops: adding-machine came out ·At·Day·**It**·Oolong-·May·Utter·She·Eat·No where adding on its own is ·At·Day·Oolong ([#9][compound]). So the entry is cut into its words first, at every boundary, space and hyphen alike, and the rule stack runs over each.

The cut is the word-sign layer's ([§ Phrase entries](word-signs.md#phrase-entries)), and now literally the same code — [`src/qslex/elements.py`](../src/qslex/elements.py) — so that the two layers cannot disagree about where a boundary is. Its alignment guard is load-bearing here for the same reason it is there: an entry whose Latin words and spelt runs are not the same shape is left whole, which is what keeps to-day (one spelt run against three Latin parts) and dhs (one Latin part against seven runs) from being mangled. 629 entries spell differently for this, and `qs_converter_phrases.txt` lost 571 of them, because an entry that composes from its own elements no longer has to be matched whole.

**The vowel before a final L is scoped to the end of the entry.** The Manual's rider on that terminal is explicit: "Where another syllable is added, the vowel sound before this L must be clearly pronounced and spelt in most cases: as it must be in — finally, orally, animality, initially, officially, levelling, devilry, caviller, rif(u)leman". A following element adds a syllable exactly as a suffix does, so able-bodied is ·Eight·Bay·**Utter**·Low-·Bay·Ox·Day·It·Day where able alone is ·Eight·Bay·Low, and cable-car is ·Key·Eight·Bay·**Utter**·Low-·Key·Ah·Roe where cable alone is ·Key·Eight·Bay·Low. That scopes two rules and no others: [`terminal-al-el-le-il`][al], and the -able/-ible half of [`terminal-ally-able`][ally], which omits the same vowel in the same position. The -ally/-ably/-ibly half is untouched, because there the L is not final in the first place — and the Manual's own list of restorations, finally and orally and initially, *is* that half. 181 compound entries keep a vowel this way that the element carrying it drops when it stands alone, which is why they still have to be matched whole.

**What the Manual attests, and what it does not.** It writes seven hyphenated compounds out in Quikscript — gold-hunting, she-ass, under-jaw, high-bred, sixty-five in the Senior specimens, Bo-peep and a-cock in the Junior ones — and in every one the rule-bearing element is already last, so none of them distinguishes a per-element stack from a per-entry one. ReadLex has no entry for any of them either. The compound rows in `manual-spellings.tsv` are therefore `derived`, one per affected family, each checked against the element standing alone: adding-machine, air-conditioned, combination-lock, cribbage-board, gentleman-at-arms, chicken-house, witness-box, breeches-buoy, mountain ash, haywards heath, vice versa, feeding-bottle, and able-bodied and cable-car for the restored vowel.

**A rule the compound hides is not the same thing as a pronunciation it does not have.** ReadLex gives some compounds a pronunciation their parts do not: a la mode has ɑː where a has eɪ, aide-de-camp ends kɑːm, black-lead is `led` and not `liːd`, bay-wreaths takes a voiceless θs. This layer is downstream of the IPA and follows it, here as everywhere.

**The rulings are keyed on the element, not on the entry.** 38 rows keyed on a compound went away with this, because the element each was really about was already ruled on — gas-ring and napkin-ring and wedding-ring all say what `ring` already says. Two were re-keyed onto the element that asks for them, barrow-in-furness to `furness` and spring-mattress to `mattress`, and nine words the split newly exposes were ruled on: `revoir` inside au revoir, and eight -ing words that are not ReadLex entries in their own right, so no `VVG` tag reaches them (`circuiting` from short-circuiting, `poohing` from pooh-poohing, `ding` from ding-dong, and five more).

`x-ligatures.tsv` has since followed ([#11][ligature]), the X-ligature having been the last rule still matched against the whole entry. Its exercise-books row retired with the move: per element, exercise has one x against one pair, and the ·Key·See that books keeps — spelling its ks with k + s, as the ruling recorded — is no longer a second pair of exercise's, only the x-count gate protecting it, so the mechanical path now reproduces what the ruling declared. The ten rulings left are all single words, and what a ruling means has widened with the key — a row keyed `xerox` would fire inside a compound containing xerox, which is what keying on the element is for, and since no entry in the corpus reaches the difference, a synthetic ruling on the `box` of ballot-box pins it instead of a word.

## Decisions

**·Et is not a reducible vowel.** Where ReadLex writes ·Et in an unstressed syllable it is recording a genuine DRESS vowel, and the Manual's counter-examples are exactly those: seamen -·May·Et·No against seaman -·May·No, cement and Overland and unman against England, "stressed vowels will be appropriately written". Without this, content (noun) `ˈkɒntent` and comment `ˈkɒment` would both lose a vowel the Manual keeps. No rule may rewrite it, and none does.

That ruling is about ·Et, No. 28, and the code once encoded it as a `REDUCIBLE` set of ·It and ·Utter, which as a side effect also locked out ·Eat, No. 27 — a different letter, the FLEECE vowel, on which the Manual's DRESS argument has nothing to say. `Y_REDUCIBLE` in [`src/qslex/rules.py`](../src/qslex/rules.py) separates them: it is the same set with ·Eat added, `apply_y` is the only rule passed it, and every other rule takes the default. So the sentence to read off this section is that a rewriting rule fires on ·It or ·Utter, and terminal -y also on an unstressed ·Eat.

**Only the unstressed branch of a stress-conditioned rule prescribes.** The Manual's stressed rows are descriptive — they say what the sound already gives — so the rules force the unstressed form and leave the stressed one alone. Forcing the stressed branch would break again (`əˈɡen`, whose -ain is not the terminal), company (`ˈkʌmpəni`, stressed but with ʌ not ɒ), and present the verb (`prɪˈzent`, whose -ent carries the stress).

**-ing stays bare after a prefix.** The Manual's "spell the root fully after a prefix or with somewhat changed meaning: e.g., in — beings, undoing, unthinkingly, willingness, canning" forbids the *root contraction* (·Bay·Oolong = being, ·Day·Oolong = doing, ·Thaw·Oolong = thinking), not the affix rule, which is stated unconditionally. So beings = ·Bay·Eat·Oolong·Zoo and unthinkingly = ·Utter·No·Thaw·It·Oolong·Key·Oolong·Low·It. Those root contractions are not in this column at all: per [#8][plan] the §III contraction list is an optional converter layer, which is also why often stays ·Ox·Fee·Utter·No here rather than taking the Manual's listed ·Ox·Fee·No.

The rider's own typography settles which of the two it restores: what it underlines is exactly what the root contraction drops — the *e* of beings, the *o* of undoing, the *ink* of unthinkingly, the *wi* of willingness, the *ann* of canning — where an affix vowel to be omitted is struck through instead, as in calling and writings, and bringing carries both marks at once. The section's own example table then prints writings with the affix vowel struck, a de-verbal noun plural, so a "changed meaning" does not keep it; and the reading that would keep it has to except canning from the rule stated one paragraph above. The noun being is therefore ·Bay·Eat·Oolong, exactly as the participle is, and the plural is the beings the rider names. This was the reading a hunspell cross-check disputed, at ·Bay·Eat·It·Oolong; [`docs/validation.md`](validation.md#the-hunspell-cross-check-done-once-not-kept) records the whole argument and the one question it leaves open — whether the converter's contraction layer, which carries §III's flat be/ing/en with no part-of-speech gate, should reach the noun senses of the six root-contraction-plus-affix rows that layer carries, three of which the Manual's own Root Contractions plus Affix names. That is a question about a layer no column sees, and the Manual settles none of the six, so it is recorded rather than answered.

**Lexicalised participles keep the affix rule; fully grammaticalised forms do not.** cunning, fleeting, scathing and excruciating are still participial in form and behaviour, so the vowel goes. during has become a preposition with no participial function left, so it does not. The line is recorded per word in `rule-words.tsv` rather than left to a heuristic.

**-ally is written even where no vowel is spoken.** "These terminals should always be written as shown, even if a preceding penlift results." ReadLex gives basically `ˈbeɪsɪkli` with no vowel between /k/ and /l/; the rule inserts one, giving ·Bay·Eight·See·It·Key·Utter·Low·It. This is the only rule that adds a letter.

**The epenthetic vowel is identified by its environment, not only by upstream's tag.** ReadLex marks most -es/-ed sites with a capital `Ə`, but 85 rows carry a plain `ə` in one of the seven pairs the Manual names — "Between these — SZ, ShZ, ChZ, JZ, ZZ, DD, TD — some kind of vowel has to be uttered". englishes `ˈɪŋɡlɪʃəz`, cashboxes, torches, handedness and their like are the same site written two ways. The rule reads the environment, so those come out right; the tag inconsistency is an upstream defect worth fixing at source ([#7][quirks]).

**The strip that opens the rule is not keyed to the Latin.** Everything else in `terminal-es-ed` waits on an -es or -ed in the Latin, but the tagged vowel goes either way, and seven entries need it to: ltd, assoc, h's, s's, x's, blesséd and long-period all carry a capital `Ə` upstream without the ending that names the rule.

**The -y terminal reaches loanwords.** The rewrites it makes from a schwa are all foreign words whose final -e ReadLex gives a genuine one: tilde, krone, lasagne, recife, hygge, firenze, karlsruhe, campagne, pologne, eiche, clotilde, bode, and the vice of vice versa. Read's rule is explicitly about this case — "though the actual sound of terminal -y varies in pronunciation, it certainly must be constant in spelling" — so they take ·It. The -ae plurals and the -ee loans the rule now also reaches are the same argument applied to a vowel ReadLex writes in full instead.

**What decides this terminal is the stress, not the length ReadLex writes.** "Though the actual sound of terminal -y varies in pronunciation, it certainly must be constant in spelling. The dictionary suggests letter-·It No. 26, and leaves ·Eat No. 27 for distinction where the terminal is stressed." Read names two conditions and neither is a vowel length: constant spelling below, stress above. So an unstressed `iː` here is inside the rule, and algae, apogee, jubilee, formulae and maybe take ·It exactly as tilde does, while legatee `ˌleɡəˈtiː`, lessee and payee keep ·Eat because they are stressed and bee, free, key and lee keep it because a mark-less monosyllable is stressed too. fricassee is the minimal pair, and the corpus supplies it twice over: `ˈfrɪkəsiː` the noun takes ·It and `ˌfrɪkəˈsiː` the verb keeps ·Eat, which is the distinction Read reserves ·Eat for, and the plural rows split the same way because a ruling only silences the residue — what rewrites is the missing stress mark, so fricassees NN2 follows the noun and fricassees VVZ the verb off one `apply` row. No other rule's domain moves, because `Y_REDUCIBLE` is passed by `apply_y` and by nothing else, and the rewrite is one-directional: a stressed ·It is never promoted, so coolly, wholly, vilely, outlawry and the de of de luxe are untouched.

**-ful trusts the POS, and two ReadLex rows have to be excused.** The Manual's split is adjective -·Fee·Utter·Low against noun -·Fee·**Foot**·Low, so the rule keys on the tag. Four ReadLex rows cross the line: brimful `ˌbrɪmˈfʊl` needs no exception because its -ful is stressed, fully `ˈfʊli` needs none because the ful is the root and not the affix, and cupful and spadeful are noun measures ReadLex tags AJ0 — an upstream tagging defect, so both carry a `skip` ruling rather than losing the ·Foot the Manual gives them.

**A `+` seam does not hide the word's stress mark.** ReadLex writes a hiatus `+` at a doubled-consonant morpheme seam, so keenness is `ˈkiːn+nəs` and goalless `ˈɡəʊl+ləs`, and the terminal's vowel lands on the far side of a marker [`docs/ipa-to-qs.md`](ipa-to-qs.md) already calls orthographically meaningless and spells as nothing. Read as a chunk of its own, `nəs` carries no stress mark at all, which made the mark-less-element fallback call it stressed; **·Et is not a reducible vowel** above then declined to touch it, and those words kept an ·Utter that every seamless -ness and -less had already lost. The same seam reaches the -est superlatives, where freest `ˈfriː+əst` and beefiest `ˈbiːfi+əst` stood against a seamless driest and happiest. So the fallback is scoped, on the phonology rather than on the morphology: a `+` tail whose only vowel is a schwa has nothing that could carry the stress it would be granted, so it does not get it. Every other `+` tail is left alone; what motivates leaving them is the seam that really does join two words — bookkeeping, clipboard, courtship, sweatshirt — whose second element has a vowel of its own and stays stressed. Which tails are suffixes and which are compound elements is not what the test asks, and the two do not line up with it: coolly and soullessly are suffixes it leaves stressed, the -shire placenames compound elements it demotes, and neither costs a letter. The [rider on rule 3](ipa-to-qs.md#the-stress-rule-for-ɪə) states it and works through both sides.

**Edward is contracted.** `terminal-ward` fires on any unstressed -ward syllable, which includes the personal name (`ˈedwəRd` → ·Et·Day·Way·Day). The Manual's one caution — "the stressed syllables 'for—, on—' should not be contracted" — is about the stem and not the terminal: it writes forward and onwards contracted at the -ward all the same, keeping their stressed ·Fee·Awe·Roe and ·Ox·No in front of it, which is what both `manual-spellings.tsv` rows record. Standalone ward and wards are exempt by construction (the rule needs a stem before the suffix), and toward keeps its ·Awe·Roe without ever reaching the stress test: the rule contracts ·Way·**Utter**·Roe·Day, and a stressed -ward syllable is ·Way·**Awe**·Roe·Day (`təˈwɔːRd`), so the shape it looks for has already declined the word. The stress test is kept because ·Utter is /ʌ/ and /ɜː/ as well as schwa, so the shape could in principle arrive stressed and the Manual says nothing about that case; declining it is the **Only the unstressed branch of a stress-conditioned rule prescribes** decision above applied here, and since no ReadLex row writes one, a synthetic spelling pins it instead of a word.

## Where the fixture came from

`manual-spellings.tsv` records what the Manual itself writes (`source=manual`, 136 rows), what this project derives for a word the Manual names but does not write out (`source=derived`, 243 rows, each carrying a note saying what the rule changed), and one `modernised` row: the Manual spells visual ·Vie·It·**Zoo·Ye**·Ooze·Utter·Low with its 1966 /zj/, where ReadLex has ʒ and the senior column follows the IPA, giving ·Vie·It·**Zhivago**·Ooze·Utter·Low — the same decision `docs/ipa-to-qs.md` already records for weak u.

Two rows carry a spelling the pipeline cannot be checked against, because ReadLex has no such entry: **Mr Jones's** = ··May·Roe ·Jay·Owe·No·Zoo·Zoo (one name-dot, no apostrophe) and **sixty-five**. The count is pinned, so a third cannot appear unnoticed.

Where the Manual and ReadLex disagree about a word's *pronunciation* rather than its spelling rule, the fixture says so rather than inventing a spelling. The clearest case is sheaths: the Manual splits verb -·They·Zoo from noun -·Thaw·See, but ReadLex has only `ʃiːðz`, the voiced form, under NN2.

## What the validator checks

The rules section of [`src/qslex/validate.py`](../src/qslex/validate.py) runs over every corpus row and fails unless:

- every rule rewrites exactly as many rows as `EXPECTED_RULE_CHANGES` pins;
- every terminal claims at least one word — counted per element, so a terminal that only ever owns the end of a word inside a compound still has to claim it. The ten rules that are not terminals — -es/-ed, -ing and the eight prefixes — carry no pattern to be claimed by, because each decides inside its own `apply` rather than by matching the end of the Latin; what holds them is their pinned count and the undecided residue below;
- every Manual example word reproduces exactly, and exactly two are missing from ReadLex;
- every ruling in `rule-words.tsv` and `x-ligatures.tsv` is exercised — exercised meaning the rule consulted the row, not that some corpus entry shares its key, so a row the per-element lookup can no longer reach cannot linger;
- no -ing, -est/-ess, -ful, -y, be-/de-/re- or ligature decision is left undecided;
- no ligature is emitted for a word with no `x` in it, and no word whose ruling declares it takes none still ships a ·Key·See or ·Gay·Zoo pair in its own run.

[manual]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html
[plan]: https://github.com/adiabatic/quikscript-lexicon/issues/8
[quirks]: https://github.com/adiabatic/quikscript-lexicon/issues/7
[compound]: https://github.com/adiabatic/quikscript-lexicon/issues/9
[ligature]: https://github.com/adiabatic/quikscript-lexicon/issues/11
[es-ed]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-es-ed
[ing]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-ing
[al]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-al-el-le-il
[ally]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-ally-able
[tion]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-tion
[en-on]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-en-on
[ent]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-ent-ance
[land]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-land-ment
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
[sec2]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#section-2
