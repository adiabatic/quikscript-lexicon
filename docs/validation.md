# Validation and the QA harness

This is the spec for the checks that produce no artifact of their own: the tables of expected spellings, the cross-checks and the assertions that test what the other four layers produce (the segment mapping, the orthographic rules, the word signs and the build). They run from [`src/qslex/validate.py`](../src/qslex/validate.py), which makes one pass over the corpus and then reports on it in several ways.

Each check below tests whether the lexicon still agrees with its sources. Each is set up so that a change makes the validator fail: either an expected count in `validate.py` changes, or a row stops matching.

## Authority

The Manual takes precedence over every other source. Other sources are used only as evidence. This ordering decides every difficult case in this document:

| Source                                          | Role                                                                                                                                                                                                     |
| ----------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [The Manual][manual], via the AMS transcription | Takes precedence. A spelling it writes out that the rules cannot reproduce is a failure.                                                                                                                 |
| ReadLex                                         | The corpus. It supplies pronunciations, not Quikscript spellings. Where it conflicts with the Manual, the Manual wins, and the conflict is recorded in `shavian-divergences.tsv` and in the rule tables. |

Page numbers below are the Manual’s own. Anchors are those of the AMS transcription. Every letter-name spelling quoted here was extracted codepoint for codepoint from the transcription’s PUA text, with the presentation-only ZWNJs and variation selectors removed.

## Artifacts

- `src/qslex/data/manual-spellings.tsv`: every spelling the Manual writes out and every example word it names, each with the rule it illustrates. Specified in [`docs/orthographic-rules.md`](orthographic-rules.md). Loaded by `src/qslex/manual.py`.
- `src/qslex/data/manual-passages.tsv`: the Manual’s eleven specimen passages, one row per word, each with a verdict. Loaded by `src/qslex/passages.py`.
- `src/qslex/roundtrip.py`: the reverse of the segment mapping, and the table of differences a spelling may have from the IPA it came from.
- `src/qslex/lint.py` and `src/qslex/data/lint-pragmas.tsv`: the lint checks re-derived from the Manual’s rule sections, and the table of pragmas. A pragma is a row that exempts one word from one lint check because of a known defect tracked in another issue.
- `src/qslex/data/added-words.tsv`: every entry the lexicon has that ReadLex does not, each with the spelling the rules must produce for it. Specified in [`docs/pipeline.md`](pipeline.md#words-the-corpus-lacks). Loaded by `src/qslex/added.py`.
- `src/qslex/build.py`: prints a coverage report when it writes `lexicon/`.

## The specimen passages

The rule sections of the Manual give examples one word at a time, each chosen to show one convention. The specimen passages are the only *running text* the Manual writes. They are therefore the only test data that exercises the segment mapping, the terminals and the word signs together, in the proportions ordinary English uses them. There are eleven passages, 674 words in all:

| Passage                                                                 | Level  | Words             |
| ----------------------------------------------------------------------- | ------ | ----------------- |
| [No-how][no-how]                                                        | Senior | 56                |
| [Parental advice][parental]                                             | Senior | 51                |
| [Gown shop][gown]                                                       | Senior | 64                |
| [Rip van Winkle][rip]                                                   | Senior | 120               |
| [Froude, on Drake][senior-examples]                                     | Senior | 134               |
| [Stevenson, *Travels with a Donkey*][senior-examples]                   | Senior | 51 + 66           |
| [Bo-peep, Jack Horner, Ride a-cock Horse, Mary’s Lamb][junior-examples] | Junior | 25 + 29 + 31 + 47 |

The Senior specimens have their own Latin in the transcription’s `data-orthodox` attribute, so the transcriber, not this project, decided which Latin word each Quikscript word corresponds to. The four Junior nursery rhymes have no such attribute, and their Latin was transcribed by hand.

Each word has a **verdict** in the `verdict` column. The validator checks each verdict as follows:

| Verdict                        | Meaning                                                                                                      | What is checked                                                                                |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------- |
| `senior`, `junior`, `x-letter` | That column reproduces the Manual’s spelling.                                                                | The spelling is among the lexicon’s spellings for that word in that column.                    |
| `contraction`                  | Read used a contraction that `contractions.tsv` lists. The lexicon writes these contractions into no column. | `contractions.tsv` has that spelling for that word.                                            |
| `absent`                       | ReadLex has no entry for the word.                                                                           | It still has none. If a corpus update adds one, the row must be revisited.                     |
| `differs`                      | The lexicon and the Manual disagree.                                                                         | They still disagree, and the lexicon still spells the word as the row’s `ours` column records. |

`contractions.tsv` holds the [§III list][senior-contractions] plus two forms that list omits: the doing that the [terminal -ing][ing] section prints, and the done that the [No-how][no-how] passage writes.

A Senior passage is compared with the senior and X-letter columns, and a Junior passage with the junior column. The junior column holds the senior spelling wherever the two do not differ. Only a Senior passage may use the `contraction` verdict. 533 of the 674 words are reproduced, 111 are contractions, 13 are words ReadLex does not have, and 17 differ. Each of the 17 has a note saying why. Most fall into five groups:

- **Read’s own contractions.** In running text he contracts more words than [§III][senior-contractions] lists: them as ·They·May, and whatever as ·Why·Et·Vie·Utter·Roe where the list gives ·Why·Et·Vie. The lexicon spells these words out, following the same decision that keeps people at ·Pea·Eat·Pea·Low. One of his contractions is in `contractions.tsv`: done as ·Day·No. The [No-how][no-how] passage spells done out at its first occurrence and writes ·Day·No at its second. The `contractions.tsv` row cites that passage as its authority. The spell checkers accept ·Day·No as Senior writing, but the transliterator does not write it, and every column spells done ·Day·Utter·No.
- **TRAP-BATH.** Read writes passed and glass with ·At. The lexicon writes ·Ah, from the RRP row that the [row policy](pipeline.md#row-policy-the-rrp-family-only) keeps. The Manual examples contrast and example differ in the same way.
- **Pronunciation.** ReadLex and Read pronounce the word differently: antipodes, diminutive, everywhere.
- **Scope of a rule.** In discontinued, Read applies the Con- convention to a con- inside the word, but the prefix rules apply only at the start of an element. In employ he writes ·Et for an unstressed em-, which the Manual’s [In-, En- rule][in-en] does not cover.
- **Junior does not use the Senior facilities.** In bringing and eating, Read keeps the ·It that the -ing terminal would drop. The Manual says so in the [Note][note] on p.25: “Examples of Junior Quickscript on page 26 are in separated letters as they would be in type. Of the time required to write in that manner, as much as a quarter may be saved by the writing and spelling facilities of Sections II and III. These Senior facilities are of course impossible as a first stage in children’s writing.” The junior column applies the affix rules anyway, per [#3][wordsigns]. This is an open question about the junior column, not about the validator. Only the linking vowel before n't has since been decided: [`terminal-nt`](orthographic-rules.md#decisions) is senior-only, and the junior column keeps the vowel as bo-peep writes it. That is why doesn't is among the reproduced words and not in this list.

## The round trip

Every shipped spelling is read back, letter by letter, to a phoneme string and compared with the IPA it was made from. The reverse table is *derived* from `ipa-to-qs.tsv` rather than written out. Deriving the table checks that the mapping can be inverted: it fails if two IPA tokens that no entry in `MERGES` joins are written with the same letter. Only ·Excite and ·Exam are stated by hand, because no segment mapping row writes them. [§II][section-2] gives both.

The two strings often differ, and that is expected. The check is that every difference is one this project has listed. `EDITS` in [`src/qslex/roundtrip.py`](../src/qslex/roundtrip.py) lists the allowed differences with a reason for each. Examples are an unstressed vowel that a terminal or prefix convention omits, the epenthetic ·Utter the rules insert, and the ·Et of an X-letter. The alignment is the shortest sequence of those edits that turns one string into the other. A spelling that no sequence of them reaches fails. The count of each allowed difference is asserted in `validate.py`. So if a rule starts dropping a vowel it should not drop, that difference’s count changes and the validator fails, even if nobody looks at the spelling.

`EXPECTED_ROUNDTRIP_IDENTICAL` in [`src/qslex/validate.py`](../src/qslex/validate.py) is the number of spellings that read back to their own IPA with nothing dropped or leveled. That constant is the only place the count is recorded, and `make validate` prints it. The 37 rows that a word sign or standard outline rewrites (`EXPECTED_ROUNDTRIP_SKIPPED`) are skipped. A sign stands for the written word, not for its sounds, so there is nothing to read back. The Manual even writes its three abbreviations without a break between their letters. Because these rows are skipped, every allowed difference comes from the mapping, the terminal and prefix conventions, or the X-letter spelling. The sign table has its own expected count for each word (`EXPECTED_SIGN_CHANGES`).

## The Manual’s own lint

The lint checks the finished spellings against the shapes that the Manual’s rule sections prescribe. Each candidate check was derived from the section that states it. Candidates that no section supports were dropped.

Two considerations decide whether a shape check is useful on a generated lexicon:

- A check on shape alone mostly re-reports the corpus. In a generated lexicon, “an element may not end ·Et·No·Tea” is equivalent to “ReadLex may not write /ent/”, which is not a spelling rule. ·Et appears exactly where ReadLex wrote /e/. The Manual’s rider on the -land/-ment rule, “stressed vowels will be appropriately written: … cement …”, permits all 179 rows that check would flag.
- A check conditioned on the Latin re-derives the rule. It runs only where the Manual’s own trigger, the Orthodox suffix or prefix, is present, and it asserts the shape the Manual prescribes. Such a check finds zero rows when the rules are right, and every row it does find needs review.

So every check that was kept is conditioned on the Latin. The lint runs seven checks over the corpus, each one per element, at the boundaries that [`src/qslex/elements.py`](../src/qslex/elements.py) sets:

| Check                              | Anchor                     | What the Manual requires                                                                          |
| ---------------------------------- | -------------------------- | ------------------------------------------------------------------------------------------------- |
| `terminal-ing-vowel-omitted`       | [terminal-ing][ing]        | “Provided it is an affix and not a root, omit vowel-i”, with its own rider for roots ending in -y |
| `terminal-al-vowel-omitted`        | [terminal-al-el-le-il][al] | a final L drops the *unstressed* vowel before it, after a consonant, in the entry-final element   |
| `terminal-ent-ance-utter`          | [terminal-ent-ance][ent]   | -ent, -ant, -ence, -ance are “Written invariably with — ·Utter·No”                                |
| `terminal-land-ment-vowel-omitted` | [terminal-land-ment][land] | -land, -ment, -man omit the unstressed vowel                                                      |
| `terminal-men-keeps-a-vowel`       | [terminal-land-ment][land] | “…except in -men”: -men keeps the vowel                                                           |
| `initial-ex-et`                    | [§II][section-2]           | an initial ex- takes ·Et before the X-letter, “easier than ·It”                                   |
| `x-letter-only-with-x`             | [§II][section-2]           | “but only where Orthodox spells these sounds with X”, and “only one ·Excite in Xerxes”            |

All seven checks find zero rows over every corpus row the lexicon spells. They also find zero over the [added words](pipeline.md#words-the-corpus-lacks), which are linted in a separate pass where no pragma applies. `src/qslex/data/lint-pragmas.tsv` has no rows. Zero is the expected result when a rule that works is re-derived independently.

The last check with a nonzero result was `initial-ex-et`, on 36 rows under 28 headwords, all with the same defect. `rules.py::substitute_x` was the last rule still applied to the whole entry rather than to each element. So an ex- that began a word but not the entry (cross-examine, pre-exist, corn-exchange, and the phrase for example) got the X-letter but not the ·Et the Manual asks for. The 28 pragmas that recorded the defect were removed with the fix ([#11](https://github.com/adiabatic/quikscript-lexicon/issues/11)). They had to be, because the validator fails on a pragma that exempts nothing.

Each pragma has a `reason`, and `known-defect` is the only reason the loader accepts. Each row must point at a defect recorded elsewhere and say in its note what the defect is. This keeps the table from becoming a list of bare exceptions. Because the validator fails on any pragma that exempts nothing, a fix must also remove its pragma.

### Checks moved to the X-letter table

Two more checks were written and then moved out of the lint:

- a ·Key·See or ·Gay·Zoo pair that no X-letter covers;
- a superfluous ·See for the C of -xc-, which [§II][section-2] warns against.

Either can appear in a shipped spelling only through a hand-written row in `x-rulings.tsv`. Any word the mechanical X-letter substitution does not handle is already reported by the validator as an undecided word, with a clearer message. Both checks are now assertions on the `x-rulings.tsv` rows, in `rules.py::load_x_rulings`. There they apply to every row, not only to the rows that some corpus entry uses.

Only half of the first check can move to the loader. A row may leave the `x-letter` column empty, which means the word takes no X-letter. A word with more than one x, none of which spells ·Key·See, needs such a row. The row cannot show whether the spelling that ships still contains a pair. So the check is split in two:

- The loader requires a row that names an X-letter spelling to contain an X-letter.
- The validator requires a row that names none to ship with no pair left in it. It checks the run that the row’s own word ships, because the row is keyed on the element and says nothing about the elements next to it.

### Shapes not adopted

Seven more shapes were considered and not adopted. Each one matches real rows, counted over the corpus as it ships. Each turns out to be a shape from the Manual with Read’s condition removed:

| Candidate shape                           | Rows it matches | Why it was not adopted                                                                                                                                                                                                          |
| ----------------------------------------- | --------------: | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| starts ·Et·Key·See                        |             316 | The Manual prescribes ·Et for an initial ex-, and itself writes ·Et·Key·See for *necks*. The check contradicts the Manual.                                                                                                      |
| ends ·Et·No·Tea / ·Et·No·See              |             227 | ·Et is not a reducible vowel. Every match is a real ReadLex /e/, and the Manual names cement as its own exception.                                                                                                              |
| ends ·Low·At·No·Day                       |              47 | The -land rule applies to “the **unstressed** vowel”, and ReadLex records a real /æ/.                                                                                                                                           |
| ends ·May·Utter·No·Tea                    |              10 | Confuses -ment with -ent. ·May·Utter·No·Tea is the Manual’s *required* shape for claimant, dormant, informant.                                                                                                                  |
| ends ·May·Et·No·Tea                       |              40 | The same problem as ·Et·No·Tea. document, ornament, implement and supplement are all correct.                                                                                                                                   |
| ends ·May·Utter·No                        |              52 | Confuses -ment with -en/-on. ·May·Utter·No is *required* for common, lemon, sermon, omen. Narrowed to `terminal-men-keeps-a-vowel`.                                                                                             |
| final ·Low after ·Utter after a consonant |             473 | As written, it matches 133 -ful adjectives, which the Manual explicitly spells -·Fee·Utter·Low, and 236 non-final compound elements, where the Manual explicitly *restores* the vowel. Narrowed to `terminal-al-vowel-omitted`. |

Every row of that table has the same problem: the check keeps the shape and drops the condition. Read states almost every convention with a condition attached, such as “unstressed”, “provided it is an affix” or “where another syllable is added”. A check without the condition no longer tests the rule.

## Three gaps, found and closed

Three places where the rules fell short of what Read states were found by hand and filed as [#10](https://github.com/adiabatic/quikscript-lexicon/issues/10) and [#12](https://github.com/adiabatic/quikscript-lexicon/issues/12). Each was checked against the Manual rule for the word’s ending. All three are fixed. The fourth item of #12 turned out not to be a gap.

- **Terminal -y after a full `iː`: fixed.** The rules rewrote only ·It and ·Utter. That followed from the “·Et is not a reducible vowel” decision in [`docs/orthographic-rules.md`](orthographic-rules.md), which as encoded also excluded ReadLex’s full `iː`. So an unstressed terminal -e/-ee/-ae kept ·Eat, where Read says the spelling “certainly must be constant” and reserves ·Eat “for distinction where the terminal is stressed”. The shape matches 159 element words in 169 corpus rows. Two sets among them were already right: 21 compounds whose last element is a stressed word in its own right (carefree, honeybee, braintree), and 63 classical plurals and names whose `-es` is an ending of its own (theses, vortices, hades). Stress is Read’s own criterion, and ReadLex does not mark stress inside an unhyphenated compound. So each word is decided individually in `rule-words.tsv`. [`docs/orthographic-rules.md`](orthographic-rules.md#5-whether-a-terminal--y-that-readlex-writes-in-full-is-stressed) has the argument.
- **doing: added.** The [-ing][ing] section prints ·Day·-ing = doing among its Root Contractions plus Affix. §III’s own list stops at do, did, don't and didn't. So `contractions.tsv` had no row for doing, and the rip-van-winkle specimen’s doing had the verdict `differs`. It has a row now. The `authority` column accepts `terminal-ing` as well as `senior-contractions`, so the row can name the section it comes from. A third authority, `no-how`, was added later for done. The [No-how][no-how] passage spells done ·Day·Utter·No at word 35 and ·Day·No at word 38, which is §III’s do-sign plus the -en terminal. So the second is Read accepting his own do-family contraction in running text, not a slip, and a checker that accepts doing has no reason to reject done. There are three authorities now. A fourth would need the same kind of argument.
- **wasn't: fixed with the `was` outline.** A `word-signs.tsv` row of its own applies the `was` outline inside the contraction. The row is needed because `n't` attaches with no separator, so the element split leaves no boundary at which to substitute the outline. A second row applies the outline inside 'twas, where the aphetic `'t` blocks it in the same way. Those two rows are the only ones. [`docs/word-signs.md`](word-signs.md#tier-3-the-standard-word-outlines) explains, word by word, why the six other words a general rule would change are excluded. Everywhere else, the rules already produce the outline. The specimen also drops the linking vowel, and the senior column now does too: [`terminal-nt`](orthographic-rules.md#decisions) generalizes §III’s bare ·No·Tea to every n't word. The junior column keeps the vowel, as the Junior bo-peep writes it in doesn't. Both passage rows, gown-shop’s wasn't and bo-peep’s doesn't, are reproduced, each by its own grade’s column.
- **The noun being: the alternative reading rejected.** That reading would write the noun ·Bay·Eat·It·-ing. It takes the rider, “spell the root fully after a prefix or with somewhat changed meaning: e.g., in — beings, undoing, unthinkingly, willingness, canning”, as restoring the affix vowel in a de-verbal noun. The rider restores the root instead, and the section shows this in three ways:
  - Its typography marks the two operations differently, and the rider uses only one of them. What it underlines is exactly what the §III root contraction drops: the *e* of beings, the *o* of undoing, the *ink* of unthinkingly, the *wi* of willingness, the *ann* of canning. An affix vowel to be omitted is struck through instead, as in calling and writings. bringing has both marks, an underlined root *i* and a struck affix *i*.
  - Its opening rule, “provided it is an affix and not a root, omit vowel-i”, has no exceptions. The reading that keeps the affix vowel would have to make canning an exception to it.
  - Its own example table prints writings with the affix vowel struck. That is a de-verbal noun plural, spelled as this lexicon spells it.

  The rider’s beings is already ·Bay·Eat·-ing·Zoo here, with the root in full, so the lexicon already meets the rider. The note that opened this item also mis-stated the corpus: ReadLex has being under NN1 as well as VBG, and both come out ·Bay·Eat·-ing.

  The converter layer is *not* settled. `contractions.tsv` has §III’s flat be/ing/en with no part-of-speech condition, so `--contractions` writes ·Bay·-ing for a being of light. The rider bears on whether the root contraction should apply to the noun senses of the six root-contraction-plus-affix rows in that layer: being, coming, doing, going, making, thinking. The Manual’s own Root Contractions plus Affix names three of them. This question is open. The Manual settles none of the six: its rider names the plural beings, not a being of light, and it gives no reading at all for the adjectival the coming year. The layer writes into no column either way.

## The words the corpus lacks

The rows in `src/qslex/data/added-words.tsv` do not come from ReadLex, so the validator checks them more strictly than corpus rows, in a separate pass after the corpus pass. Each added row must:

- produce the spelling its row records;
- pass every lint check, with no pragma;
- read back to its own IPA using only the allowed differences in `roundtrip.EDITS`;
- not be rewritten by any word sign.

The pass also fails if ReadLex now has the word. A person then has to reconcile the two entries, so the lexicon cannot ship a second spelling of the word.

These requirements hold for every row, rather than being expected counts, because the table is small. Rows we wrote ourselves get no per-row tolerances. The differences listed in `roundtrip.EDITS` are the only exceptions. Keeping the pass separate also means the expected counts cover corpus rows only, so an upstream update changes them only through ReadLex’s own rows. The layer is specified in [`docs/pipeline.md`](pipeline.md#words-the-corpus-lacks).

## Coverage in the build log

`make artifacts` ends by printing what the build did: rows converted, rows skipped, rows added beyond the corpus, and how many rows have a junior or X-letter spelling (the sparse columns).

These counts are informational. The corpus loader checks the corpus row count. The validator checks the number of rows the row policy keeps, against the counts in `var-tags.tsv`, and the number of corpus rows with a junior spelling, against `EXPECTED_JUNIOR_DIVERGENCES`. Nothing asserts the X-letter row count or the number of added words, although the validator checks each added word.

The build does not print the per-rule and per-word-sign rewrite counts, or which rules rewrote nothing. `make validate` prints and checks those. The build used to print them as well, but nothing checked that copy. `python -m qslex.build --check`, which only compares a fresh build with the files on disk, computes none of these counts.

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
