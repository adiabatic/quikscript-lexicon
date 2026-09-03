# Validation and the QA harness

This is the spec for the layer that has no output of its own: the fixtures, cross-checks and assertions that hold everything the other four layers produce. It runs from [`src/qslex/validate.py`](../src/qslex/validate.py), which makes one pass over the corpus and then reports on it from several angles at once.

Everything below answers the same question in a different way — *does the lexicon still say what its sources say?* — and every one of them is arranged so that a change shows up as a number that moved rather than as a silence.

## Authority

**The Manual arbitrates; everything else is suggestive.** In practice that ordering decides every awkward case in this document:

| Source                                          | Standing                                                                                                                                                                  |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [The Manual][manual], via the AMS transcription | arbitrates. A spelling it writes out that the rules cannot reproduce is a failure.                                                                                        |
| ReadLex                                         | the corpus. It supplies pronunciations, not spellings, and the Manual overrules it where the two conflict — recorded in `shavian-divergences.tsv` and in the rule tables. |

Page numbers and anchors below are the Manual’s own. Every letter-name spelling quoted was extracted codepoint for codepoint from the transcription’s PUA text, with the presentation-only ZWNJs and variation selectors stripped.

## Artifacts

- `src/qslex/data/manual-spellings.tsv` — every spelling the Manual writes out and every example word it names, each anchored to the rule that owns it. Specified in [`docs/orthographic-rules.md`](orthographic-rules.md); loaded by `src/qslex/manual.py`.
- `src/qslex/data/manual-passages.tsv` — the Manual’s eleven specimen passages, word by word, with a verdict on each. Loaded by `src/qslex/passages.py`.
- `src/qslex/roundtrip.py` — the reverse of the segment mapping, and the table of differences a spelling is allowed to have from the IPA it came from.
- `src/qslex/lint.py` and `src/qslex/data/lint-pragmas.tsv` — the Manual’s own lint, and every word declared exempt from a check.
- `src/qslex/data/added-words.tsv` — every entry the lexicon carries that ReadLex does not, each declaring the spelling the rules must produce for it. Specified in [`docs/pipeline.md`](pipeline.md#words-the-corpus-lacks); loaded by `src/qslex/added.py`.
- `src/qslex/build.py` — the build’s own coverage report, printed when it writes `lexicon/`.

## The specimen passages

The rule sections of the Manual give examples a word at a time, chosen to show one convention each. The specimens are the only place it writes *running text*, which makes them the only fixture that exercises the segment mapping, the terminals and the word signs together, in the proportions English actually uses them. There are eleven, 674 words in all:

| Passage                                                                 | Level  | Words             |
| ----------------------------------------------------------------------- | ------ | ----------------- |
| [No-how][no-how]                                                        | Senior | 56                |
| [Parental advice][parental]                                             | Senior | 51                |
| [Gown shop][gown]                                                       | Senior | 64                |
| [Rip van Winkle][rip]                                                   | Senior | 120               |
| [Froude, on Drake][senior-examples]                                     | Senior | 134               |
| [Stevenson, *Travels with a Donkey*][senior-examples]                   | Senior | 51 + 66           |
| [Bo-peep, Jack Horner, Ride a-cock Horse, Mary’s Lamb][junior-examples] | Junior | 25 + 29 + 31 + 47 |

The Senior specimens carry their own Latin in the transcription’s `data-orthodox` attribute, so the alignment of Quikscript word to Latin word is the transcriber’s, not ours. The four Junior nursery rhymes carry no such attribute, and their Latin was transcribed by hand.

Each word gets a **verdict**, and the verdict is what the validator holds:

| Verdict                        | What it claims                                                                                                                                                                                                         | What is checked                                                                 |
| ------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| `senior`, `junior`, `x-letter` | that column reproduces the Manual’s spelling                                                                                                                                                                           | the spelling is among the ones the lexicon carries for that word in that column |
| `contraction`                  | Read reached for a contraction `contractions.tsv` carries — the [§III list][senior-contractions], plus the doing the [terminal -ing][ing] section prints and the done the [No-how][no-how] passage writes, both of which that list omits — which this lexicon applies to no column | `contractions.tsv` carries exactly that spelling for that word                  |
| `absent`                       | ReadLex has no entry for the word                                                                                                                                                                                      | it still has none — if a corpus bump adds one, the row has to be revisited      |
| `differs`                      | the two genuinely disagree                                                                                                                                                                                             | it still disagrees, and the lexicon still spells what the row pins              |

A Senior passage is held to the senior and X-letter columns; a Junior passage to the junior column, which is the senior spelling wherever it does not diverge. 533 of the 674 words are reproduced outright, 111 are contractions, 13 are words ReadLex does not have, and 17 differ. Every one of the 17 carries a note saying why; the recurring reasons fall into five groups:

- **Read’s own contractions.** He contracts more freely in running text than [§III][senior-contractions] lists: them as ·They·May, whatever as ·Why·Et·Vie·Utter·Roe where the list gives ·Why·Et·Vie. The lexicon spells these words out, by the same ruling that keeps people at ·Pea·Eat·Pea·Low. One of his is carried: done as ·Day·No, which the [No-how][no-how] passage writes at its second occurrence after spelling the first out, has a `contractions.tsv` row under that passage as its anchor, on the same footing as the rest of the table — accepted as Senior writing, spelled ·Day·Utter·No in every column.
- **TRAP-BATH.** passed and glass are Read’s ·At against the ·Ah of the RRP row the [row policy](pipeline.md#row-policy-the-rrp-family-only) keeps — the same trade as contrast and example.
- **Pronunciation.** ReadLex and Read disagree about the word: antipodes, diminutive, everywhere.
- **Reach of a rule.** discontinued applies the Con- convention to a con- inside the word, where the prefix rules fire at the start of an element only; employ writes ·Et for an unstressed em-, which the Manual’s [In-, En- rule][in-en] does not cover.
- **Junior does not use the Senior facilities.** bringing and eating keep the ·It that the -ing terminal would elide. The Manual says so directly, in the [Note][note] on p.25: “Examples of Junior Quickscript on page 26 are in separated letters as they would be in type. Of the time required to write in that manner, as much as a quarter may be saved by the writing and spelling facilities of Sections II and III. These Senior facilities are of course impossible as a first stage in children’s writing.” The junior column applies the affix rules all the same, per [#3][wordsigns]. That is a live question about the junior model, not about this harness, and it is recorded here rather than settled here. The linking vowel before n't is the one case the model has since settled: [`terminal-nt`](orthographic-rules.md#decisions) is senior-only and the junior column keeps what bo-peep writes, which is why doesn't sits among the reproduced words and not in this list.

## The round trip

Every shipped spelling is read back, letter by letter, to a phoneme string, and laid beside the IPA it was made from. The reverse table is *derived* from `ipa-to-qs.tsv` rather than written out, which makes deriving it a proof in itself: it fails if two IPA tokens that no documented merge joins ever land on the same letter. Only ·Excite and ·Exam are stated by hand, because no segment mapping reaches them; [§II][section-2] gives both.

The two strings will not be equal, and are not meant to be. What is checked is that every difference between them is one this project has accounted for. `EDITS` in [`src/qslex/roundtrip.py`](../src/qslex/roundtrip.py) lists the licensed ones with a reason each — an unstressed vowel a terminal convention omits, the epenthetic ·Utter the rules insert, the ·Et of an X-letter — and the alignment is a shortest path over exactly those. A spelling that cannot be reached by any of them fails, and the count of each licensed difference is pinned, so a rule that starts eliding a vowel it has no business eliding shows up as a count that moved rather than as a spelling nobody looked at.

How many spellings read straight back to their own IPA with nothing elided or leveled at all is pinned as `EXPECTED_ROUNDTRIP_IDENTICAL` in [`src/qslex/validate.py`](../src/qslex/validate.py), which is the only place to read that count; `make validate` prints it. The 37 rows a word sign or standard outline rewrites are skipped: a sign stands for the written word rather than for its sounds — the Manual’s three abbreviations are not even written with a break between their letters — so there is nothing to read back, and the licensed differences stay about the mapping and the terminal conventions rather than about the sign table, which is pinned word by word elsewhere.

## The Manual’s own lint

The lint holds the finished spellings to the shapes the Manual’s own rule sections prescribe. A shape is only worth a check if the Manual backs it, so each candidate was derived from the section that states it, and the ones no section backs were dropped rather than carried.

Two things decide whether a shape check earns its place over a generated lexicon:

- **A shape-only check mostly re-reports the corpus.** “An element may not end ·Et·No·Tea” is, in a generated lexicon, equivalent to “ReadLex may not write /ent/”, which is not a spelling rule at all. ·Et appears exactly where ReadLex wrote /e/, and the Manual’s rider on the -land/-ment rule — “stressed vowels will be appropriately written: … cement …” — licenses every one of the 179 rows it fires on.
- **A Latin-gated check is a real re-derivation.** Firing only where the Manual’s own trigger is present — the Orthodox suffix or prefix — and asserting the shape the Manual prescribes gives a check that reads zero when the rules are right, and whose every non-zero row is worth looking at.

So every check that was kept is Latin-gated, and the seven the lint still runs over the corpus run **per element**, at the boundaries [`src/qslex/elements.py`](../src/qslex/elements.py) cuts:

| Check                              | Anchor                     | What the Manual requires                                                                          |
| ---------------------------------- | -------------------------- | ------------------------------------------------------------------------------------------------- |
| `terminal-ing-vowel-omitted`       | [terminal-ing][ing]        | “Provided it is an affix and not a root, omit vowel-i”, with its own rider for roots ending in -y |
| `terminal-al-vowel-omitted`        | [terminal-al-el-le-il][al] | a final L drops the *unstressed* vowel before it, after a consonant, in the entry-final element   |
| `terminal-ent-ance-utter`          | [terminal-ent-ance][ent]   | -ent, -ant, -ence, -ance “written invariably with standard ·Utter·No”                             |
| `terminal-land-ment-vowel-omitted` | [terminal-land-ment][land] | -land, -ment, -man omit the unstressed vowel                                                      |
| `terminal-men-keeps-a-vowel`       | [terminal-land-ment][land] | “…except in -men”, the one ending that keeps it                                                   |
| `initial-ex-et`                    | [§II][section-2]           | an initial ex- takes ·Et before the X-letter, “easier than ·It”                                   |
| `x-letter-only-with-x`             | [§II][section-2]           | “but only where Orthodox spells these sounds with X” — and “only one ·Excite in Xerxes”           |

All seven read zero over every corpus row the lexicon spells — and over the [added words](pipeline.md#words-the-corpus-lacks), which are linted in a pass of their own and are allowed no pragma at all — which is what an independent re-derivation of a working rule should read, and `src/qslex/data/lint-pragmas.tsv` carries no rows at all. The last check to read otherwise was `initial-ex-et`, on 36 rows under 28 headwords, every one of them the same defect: `rules.py::substitute_x` was the last rule still scoped to the whole entry rather than to the element, so an `ex-` that was word-initial without being entry-initial — cross-examine, pre-exist, for example, corn-exchange — took the X-letter but not the ·Et the Manual asks for. The 28 declarations that recorded it went out with the fix ([#11](https://github.com/adiabatic/quikscript-lexicon/issues/11)), and had to: the validator fails on a pragma that excuses nothing, so the cleanup was never optional.

A pragma states a `reason`, and `known-defect` is the only reason the table admits: every row has to point at a defect recorded elsewhere and say in its note what that defect is, so that the table cannot quietly become the bare exception list this project keeps refusing to write. The validator fails on any pragma that excuses nothing, so a fix cannot leave its excuse behind.

### Moved to the table they can only fire on

Two more checks were written and then moved out of the lint. A ·Key·See or ·Gay·Zoo pair that no X-letter covers, and the superfluous ·See for the C of -xc- that [§II][section-2] warns against, can only reach a shipped spelling through a row `x-rulings.tsv` declares by hand — everything the mechanical path declines is caught first, and with a better message, by the undecided residue. Both are assertions on the declared row now, in `rules.py::load_x_rulings`, where they hold every row unconditionally rather than only the rows a corpus entry happens to visit.

Half of the first one cannot move there. A row may leave the X-letter column empty, ruling that its word takes no X-letter at all — which is what a word with more than one x, none of them spelling a ·Key·See, has to declare. Whether the spelling that then ships still carries a pair is something the row itself cannot show, so the loader holds a row that names an X-letter to actually carrying one, and the validator holds a row that names none to a run with no pair left in it — the run its own word ships, because the ruling is keyed on the element and says nothing about the elements beside it.

### Dropped, with reasons

Seven further shapes were considered and not adopted. Each of them fires on real rows — the counts are over the corpus as it ships — and each of them turns out to be a Manual shape with the condition Read attached to it stripped off:

| Candidate shape                           | Rows it fires on | Why it was not adopted                                                                                                                                                                                                     |
| ----------------------------------------- | ---------------: | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| starts ·Et·Key·See                        |              316 | The Manual prescribes ·Et for an initial ex- and writes ·Et·Key·See itself, for *necks*. The check is the Manual reversed.                                                                                                 |
| ends ·Et·No·Tea / ·Et·No·See              |              227 | ·Et is not a reducible vowel; every hit is a genuine ReadLex /e/, and the Manual names cement as its own exception.                                                                                                        |
| ends ·Low·At·No·Day                       |               47 | The -land rule is conditioned on “the **unstressed** vowel”, and ReadLex records a real /æ/.                                                                                                                               |
| ends ·May·Utter·No·Tea                    |               10 | Conflates -ment with -ent: ·May·Utter·No·Tea is the Manual’s *required* shape for claimant, dormant, informant.                                                                                                            |
| ends ·May·Et·No·Tea                       |               40 | As ·Et·No·Tea; document, ornament, implement and supplement are all correct.                                                                                                                                               |
| ends ·May·Utter·No                        |               52 | Conflates -ment with -en/-on: ·May·Utter·No is *required* for common, lemon, sermon, omen. Narrowed to `terminal-men-keeps-a-vowel`.                                                                                       |
| final ·Low after ·Utter after a consonant |              473 | As written it fires on 133 -ful adjectives the Manual explicitly spells -·Fee·Utter·Low, and on 236 non-final compound elements where the Manual explicitly *restores* the vowel. Narrowed to `terminal-al-vowel-omitted`. |

The pattern is the same in every row of that table: the check is a shape without its condition. Read states almost every convention with an “unstressed”, a “provided it is an affix”, or a “where another syllable is added” attached, and a check that drops the condition keeps the shape and loses the rule.

## Three gaps, found and closed

Three places where the rules fell short of what Read states were found by hand and filed as [#10](https://github.com/adiabatic/quikscript-lexicon/issues/10) and [#12](https://github.com/adiabatic/quikscript-lexicon/issues/12), each one adjudicated against the Manual rule owning the word’s ending. All three are closed now, and #12’s fourth item turned out not to be a gap at all:

- **terminal -y after a full `iː`, now fixed.** The rewriting rules fired on ·It and ·Utter only — the “·Et is not a reducible vowel” ruling in [`docs/orthographic-rules.md`](orthographic-rules.md), which as encoded also excluded ReadLex’s full `iː`. So an unstressed terminal -e/-ee/-ae kept ·Eat where Read says the spelling “certainly must be constant” and reserves ·Eat “for distinction where the terminal is stressed”. The shape reaches 159 element words over 169 corpus rows: 21 of them are compounds whose last element is a stressed word in its own right — carefree, honeybee, braintree — and 63 are classical plurals and names whose `-es` is an ending of its own — theses, vortices, hades — and both sets were right as they stood. Since stress is Read’s own discriminator and ReadLex does not mark it inside an unhyphenated compound, the split is ruled on word by word in `rule-words.tsv`; [`docs/orthographic-rules.md`](orthographic-rules.md#5-whether-a-terminal--y-that-readlex-writes-in-full-is-stressed) has the argument.
- **doing, now carried.** The [-ing][ing] section prints ·Day·Oolong = doing among its Root Contractions plus Affix, where §III’s own list stops at do, did, don't and didn't — so `contractions.tsv` had no row able to hold it, and the rip-van-winkle specimen’s doing was a `differs`. It has a row now, and `authority` admits `terminal-ing` beside `senior-contractions` so that the row can say which section it comes from. A third anchor, `no-how`, was admitted later for done: the [No-how][no-how] passage spells it ·Day·Utter·No at word 35 and ·Day·No at word 38, §III’s do-sign plus the -en terminal, so the second is Read tolerating his own do-family contraction in running text rather than a slip, and a checker that accepts doing has no ground to refuse it. Three anchors now, and a fourth would have to argue for itself the same way.
- **wasn't, now fixed at the outline.** The `was` outline reaches inside the contraction, off a `word-signs.tsv` row of its own, because `n't` attaches solid and leaves no boundary for the element split to substitute at — and off a second row inside 'twas, where the aphetic `'t` walls the same outline off in the same way. Those two are the whole of it: the six other words a generalizing rule would touch are ruled out one by one in [`docs/word-signs.md`](word-signs.md#tier-3-the-standard-word-outlines), and everywhere else the outline is already what the rules give. The specimen also elides the linking vowel, and the senior column now does too — [`terminal-nt`](orthographic-rules.md#decisions) generalizes §III’s bare ·No·Tea to every n't word — while the junior column keeps the vowel, as the Junior bo-peep writes it in doesn't. Both passage rows — gown-shop’s wasn't and bo-peep’s doesn't — are reproduced outright, each by its own grade’s column.
- **the noun being, declined.** The reading that would write it ·Bay·Eat·It·Oolong takes the rider — “spell the root fully after a prefix or with somewhat changed meaning: e.g., in — beings, undoing, unthinkingly, willingness, canning” — as restoring the affix vowel in a de-verbal noun. It restores the root instead, and the section says so three ways. Its typography marks the two operations differently, and the rider uses only one of them: what it underlines is exactly what the §III root contraction drops — the *e* of beings, the *o* of undoing, the *ink* of unthinkingly, the *wi* of willingness, the *ann* of canning — where an affix vowel to be omitted is struck through instead, as in calling and writings, and bringing carries both marks at once, an underlined root *i* and a struck affix *i*. Its opening rule — “provided it is an affix and not a root, omit vowel-i” — is unconditional, and the reading that keeps the affix vowel would have to except canning from it. And its own example table prints writings with the affix vowel struck, a de-verbal noun plural spelled exactly as this lexicon spells it. The rider’s beings is already ·Bay·Eat·Oolong·Zoo here, root in full, so nothing in it is unmet. The note that opened this item also mis-stated the corpus: ReadLex has being under NN1 as well as VBG, and both come out ·Bay·Eat·Oolong. What is *not* settled is the converter layer — `contractions.tsv` carries §III’s flat be/ing/en with no part-of-speech gate, so `--contractions` writes ·Bay·Oolong for a being of light, and the rider bears on whether the root contraction should reach the noun senses of the six root-contraction-plus-affix rows that layer carries — being, coming, doing, going, making, thinking, of which the Manual’s own Root Contractions plus Affix names three. That is left open rather than ruled on: the Manual settles none of the six (its rider names the plural beings and not a being of light, and it gives no reading at all for the adjectival the coming year), and the layer reaches no column either way.

## The words the corpus lacks

The rows in `src/qslex/data/added-words.tsv` are not ReadLex’s, so they are not held to ReadLex’s standard — they are held to a stricter one, in a pass of their own after the corpus pass. Each must produce the spelling its own row declares, break no lint check, read back to its own IPA with no licensed difference at all, and reach no word sign; and the pass fails if ReadLex has grown the word, so that upstream carrying it is something a person reconciles rather than a second spelling that ships in silence.

Absolutes rather than pinned counts, because a table this small can be held to them and a row we wrote ourselves has no claim on latitude the corpus needs. Keeping the pass separate is also what leaves every corpus invariant exactly where it was, so an upstream bump still diffs against ReadLex alone. The layer is specified in [`docs/pipeline.md`](pipeline.md#words-the-corpus-lacks).

## Coverage in the build log

`make artifacts` ends by printing what the build touched: rows converted, rows skipped, how many were added beyond the corpus, and how many rows carry each sparse column.

The same counts are pinned in `validate.py`, so the log is a convenience and the assertion is elsewhere — which is why it stops where it does. The per-rule and per-word-sign rewrite counts, and the reading of which rules rewrote nothing, are `make validate`’s to report and to adjudicate; printing them from the build too was a second, unasserted copy, and a build that only checks its output against disk (`--check`) counts none of it.

[manual]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html
[no-how]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#no-how
[parental]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#parental-advice
[gown]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#gown-shop
[rip]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#rip-van-winkle
[senior-examples]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#senior-examples
[junior-examples]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#junior-examples
[senior-contractions]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#senior-contractions
[section-2]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#section-2
[in-en]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#prefix-in-en
[note]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#examples-note
[wordsigns]: https://github.com/adiabatic/quikscript-lexicon/issues/3
[ing]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-ing
[al]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-al-el-le-il
[ent]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-ent-ance
[land]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-land-ment
