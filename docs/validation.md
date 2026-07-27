# Validation and the QA harness

This is the spec for the layer that has no output of its own: the fixtures, cross-checks and assertions that hold everything the other four layers produce. It runs from [`src/qslex/validate.py`](../src/qslex/validate.py), which makes one pass over the corpus and then reports on it from several angles at once.

Everything below answers the same question in a different way — *does the lexicon still say what its sources say?* — and every one of them is arranged so that a change shows up as a number that moved rather than as a silence.

## Authority

**The Manual arbitrates; everything else is suggestive.** In practice that ordering decides every awkward case in this document:

| Source | Standing |
|---|---|
| [The Manual][manual], via the AMS transcription | arbitrates. A spelling it writes out that the rules cannot reproduce is a failure. |
| ReadLex | the corpus. It supplies pronunciations, not spellings, and the Manual overrules it where the two conflict — recorded in `shavian-divergences.tsv` and in the rule tables. |
| [hunspell-dict-qs](https://github.com/adiabatic/hunspell-dict-qs) | suggestive only, and nothing here depends on it. Written by hand by one fallible person; a disagreement with it is a place worth looking, never a defect on either side, and matching it is not a goal. Its `lint.py` supplied candidate checks, and it was cross-checked once — both below. |

Page numbers and anchors below are the Manual's own. Every letter-name spelling quoted was extracted codepoint for codepoint from the transcription's PUA text, with the presentation-only ZWNJs and variation selectors stripped.

## Artifacts

- `src/qslex/data/manual-spellings.tsv` — every spelling the Manual writes out under a rule heading, and every example word it names. Specified in [`docs/orthographic-rules.md`](orthographic-rules.md); loaded by `src/qslex/manual.py`.
- `src/qslex/data/manual-passages.tsv` — the Manual's eleven specimen passages, word by word, with a verdict on each. Loaded by `src/qslex/passages.py`.
- `src/qslex/roundtrip.py` — the reverse of the segment mapping, and the table of differences a spelling is allowed to have from the IPA it came from.
- `src/qslex/lint.py` and `src/qslex/data/lint-pragmas.tsv` — the Manual's own lint, and every word declared exempt from a check.
- `src/qslex/build.py` — the build's own coverage report, printed when it writes `lexicon/`.

## The specimen passages

The rule sections of the Manual give examples a word at a time, chosen to show one convention each. The specimens are the only place it writes *running text*, which makes them the only fixture that exercises the segment mapping, the terminals and the word signs together, in the proportions English actually uses them. There are eleven, 674 words in all:

| Passage | Level | Words |
|---|---|---|
| [No-how][no-how] | Senior | 56 |
| [Parental advice][parental] | Senior | 51 |
| [Gown shop][gown] | Senior | 64 |
| [Rip van Winkle][rip] | Senior | 120 |
| [Froude, on Drake][senior-examples] | Senior | 134 |
| [Stevenson, *Travels with a Donkey*][senior-examples] | Senior | 51 + 66 |
| [Bo-peep, Jack Horner, Ride a-cock Horse, Mary's Lamb][junior-examples] | Junior | 25 + 29 + 31 + 47 |

The Senior specimens carry their own Latin in the transcription's `data-orthodox` attribute, so the alignment of Quikscript word to Latin word is the transcriber's, not ours. The four Junior nursery rhymes carry no such attribute, and their Latin was transcribed by hand.

Each word gets a **verdict**, and the verdict is what the validator holds:

| Verdict | What it claims | What is checked |
|---|---|---|
| `senior`, `junior`, `ligature` | that column reproduces the Manual's spelling | the spelling is among the ones the lexicon carries for that word in that column |
| `contraction` | Read reached for a [§III contraction][senior-contractions], which this lexicon applies to no column | `contractions.tsv` carries exactly that spelling for that word |
| `absent` | ReadLex has no entry for the word | it still has none — if a corpus bump adds one, the row has to be revisited |
| `differs` | the two genuinely disagree | it still disagrees, and the lexicon still spells what the row pins |

A Senior passage is held to the senior and ligature columns; a Junior passage to the junior column, which is the senior spelling wherever it does not diverge. 532 of the 674 words are reproduced outright, 109 are contractions, 13 are words ReadLex does not have, and 20 differ. Every one of the 20 carries a note saying why, and they fall into five groups:

- **Read's own contractions.** He contracts more freely in running text than [§III][senior-contractions] lists: them as ·They·May, done as ·Day·No, doing as ·Day·Oolong, whatever as ·Why·Et·Vie·Utter·Roe where the list gives ·Why·Et·Vie. The lexicon spells these words out, by the same ruling that keeps people at ·Pea·Eat·Pea·Low.
- **TRAP-BATH.** passed and glass are Read's ·At against the ·Ah of the RRP row the [row policy](pipeline.md#row-policy-the-rrp-family-only) keeps — the same trade as contrast and example.
- **Pronunciation.** ReadLex and Read disagree about the word: antipodes, diminutive, everywhere.
- **Reach of a rule.** discontinued applies the Con- convention to a con- inside the word, where the prefix rules fire at the start of an element only; employ writes ·Et for an unstressed em-, which the Manual's [In-, En- rule][in-en] does not cover.
- **Junior does not use the Senior facilities.** bringing and eating keep the ·It that the -ing terminal would elide. The Manual says so directly, in the [Note][note] on p.25: "Examples of Junior Quickscript on page 26 are in separated letters as they would be in type. Of the time required to write in that manner, as much as a quarter may be saved by the writing and spelling facilities of Sections II and III. These Senior facilities are of course impossible as a first stage in children's writing." The junior column applies the affix rules all the same, per [#3][wordsigns]. That is a live question about the junior model, not about this harness, and it is recorded here rather than settled here.

## The round trip

Every shipped spelling is read back, letter by letter, to a phoneme string, and laid beside the IPA it was made from. The reverse table is *derived* from `ipa-to-qs.tsv` rather than written out, which makes deriving it a proof in itself: it fails if two IPA tokens that no documented merge joins ever land on the same letter. Only ·Excite and ·Exam are stated by hand, because no segment mapping reaches them; [§II][section-2] gives both.

The two strings will not be equal, and are not meant to be. What is checked is that every difference between them is one this project has accounted for. `EDITS` in [`src/qslex/roundtrip.py`](../src/qslex/roundtrip.py) lists the licensed ones with a reason each — an unstressed vowel a terminal convention omits, the epenthetic ·Utter the rules insert, the ·Et of a ligature — and the alignment is a shortest path over exactly those. A spelling that cannot be reached by any of them fails, and the count of each licensed difference is pinned, so a rule that starts eliding a vowel it has no business eliding shows up as a count that moved rather than as a spelling nobody looked at.

How many spellings read straight back to their own IPA with nothing elided or levelled at all is pinned as `EXPECTED_ROUNDTRIP_IDENTICAL` in [`src/qslex/validate.py`](../src/qslex/validate.py), which is the only place to read that count; `make validate` prints it. The 34 rows a word sign or standard outline rewrites are skipped: a sign stands for the written word rather than for its sounds — the Manual's three abbreviations are not even written with a break between their letters — so there is nothing to read back, and the licensed differences stay about the mapping and the terminal conventions rather than about the sign table, which is pinned word by word elsewhere.

## The Manual's own lint

[hunspell-dict-qs](https://github.com/adiabatic/hunspell-dict-qs) ships `lint.py`, ten hand-written checks its author ran over his 885 spellings to catch himself breaking Read's rules. They are a good source of *candidate* shapes and nothing more, so each was re-derived from the Manual before being ported, and the ones the Manual does not back were dropped rather than carried.

Two things change when a check moves from a hand-written dictionary to a generated one:

- **A shape-only check mostly re-reports the corpus.** "An element may not end ·Et·No·Tea" is, in a generated lexicon, equivalent to "ReadLex may not write /ent/", which is not a spelling rule at all. ·Et appears exactly where ReadLex wrote /e/, and the Manual's rider on the -land/-ment rule — "stressed vowels will be appropriately written: … cement …" — licenses every one of the 179 rows it fires on.
- **A Latin-gated check is a real re-derivation.** Firing only where the Manual's own trigger is present — the Orthodox suffix or prefix — and asserting the shape the Manual prescribes gives a check that reads zero when the rules are right, and whose every non-zero row is worth looking at.

So every ported check is Latin-gated, and the seven the lint still runs over the corpus run **per element**, at the boundaries [`src/qslex/elements.py`](../src/qslex/elements.py) cuts:

| Check | Anchor | What the Manual requires |
|---|---|---|
| `terminal-ing-vowel-omitted` | [terminal-ing][ing] | "Provided it is an affix and not a root, omit vowel-i", with its own rider for roots ending in -y |
| `terminal-al-vowel-omitted` | [terminal-al-el-le-il][al] | a final L drops the *unstressed* vowel before it, after a consonant, in the entry-final element |
| `terminal-ent-ance-utter` | [terminal-ent-ance][ent] | -ent, -ant, -ence, -ance "written invariably with standard ·Utter·No" |
| `terminal-land-ment-vowel-omitted` | [terminal-land-ment][land] | -land, -ment, -man omit the unstressed vowel |
| `terminal-men-keeps-a-vowel` | [terminal-land-ment][land] | "…except in -men", the one ending that keeps it |
| `initial-ex-et` | [§II][section-2] | an initial ex- takes ·Et before the ligature, "easier than ·It" |
| `x-ligature-only-with-x` | [§II][section-2] | "but only where Orthodox spells these sounds with X" — and "only one ·Excite in Xerxes" |

All seven read zero over all 108,425 spelt rows, which is what an independent re-derivation of a working rule should read, and `src/qslex/data/lint-pragmas.tsv` carries no rows at all. The last check to read otherwise was `initial-ex-et`, on 36 rows under 28 headwords, every one of them the same defect: `rules.py::ligate` was the last rule still scoped to the whole entry rather than to the element, so an `ex-` that was word-initial without being entry-initial — cross-examine, pre-exist, for example, corn-exchange — took the ligature but not the ·Et the Manual asks for. The 28 declarations that recorded it went out with the fix ([#11](https://github.com/adiabatic/quikscript-lexicon/issues/11)), and had to: the validator fails on a pragma that excuses nothing, so the cleanup was never optional.

A pragma states a `reason`, and `known-defect` is the only reason the table admits: every row has to point at a defect recorded elsewhere and say in its note what that defect is, so that the table cannot quietly become the bare exception list this project keeps refusing to write. The validator fails on any pragma that excuses nothing, so a fix cannot leave its excuse behind.

### Moved to the table they can only fire on

Two more checks were ported and then moved out of the lint. A ·Key·See or ·Gay·Zoo pair that no ligature covers, and the superfluous ·See for the C of -xc- that [§II][section-2] warns against, can only reach a shipped spelling through a row `x-ligatures.tsv` declares by hand — everything the mechanical path declines is caught first, and with a better message, by the undecided residue. Both are assertions on the declared row now, in `rules.py::load_x_ligatures`, where they hold every row unconditionally rather than only the rows a corpus entry happens to visit.

Half of the first one cannot move there. A row may leave the ligature column empty, ruling that its word takes no ligature at all — which is what a word with more than one x, none of them spelling a ·Key·See, has to declare. Whether the spelling that then ships still carries a pair is something the row itself cannot show, so the loader holds a row that names a ligature to actually carrying one, and the validator holds a row that names none to a run with no pair left in it — the run its own word ships, because the ruling is keyed on the element and says nothing about the elements beside it.

### Dropped, with reasons

| `lint.py` check | Rows it fires on | Why it was not ported |
|---|---:|---|
| starts ·Et·Key·See | 316 | The Manual prescribes ·Et for an initial ex- and writes ·Et·Key·See itself, for *necks*. The check is the Manual reversed. |
| ends ·Et·No·Tea / ·Et·No·See | 227 | ·Et is not a reducible vowel; every hit is a genuine ReadLex /e/, and the Manual names cement as its own exception. |
| ends ·Low·At·No·Day | 47 | The -land rule is conditioned on "the **unstressed** vowel", and ReadLex records a real /æ/. |
| ends ·May·Utter·No·Tea | 10 | Conflates -ment with -ent: ·May·Utter·No·Tea is the Manual's *required* shape for claimant, dormant, informant. |
| ends ·May·Et·No·Tea | 40 | As ·Et·No·Tea; document, ornament, implement and supplement are all correct. |
| ends ·May·Utter·No | 52 | Conflates -ment with -en/-on: ·May·Utter·No is *required* for common, lemon, sermon, omen. Replaced by `terminal-men-keeps-a-vowel`. |
| final ·Low after ·Utter after a consonant | 473 | As written it fires on 133 -ful adjectives the Manual explicitly spells -·Fee·Utter·Low, and on 236 non-final compound elements where the Manual explicitly *restores* the vowel. Re-derived as `terminal-al-vowel-omitted`. |

The pattern is the same in every row of that table: the check is a shape without its condition. Read states almost every convention with an "unstressed", a "provided it is an affix", or a "where another syllable is added" attached, and a check that drops the condition keeps the shape and loses the rule.

## The hunspell cross-check: done once, not kept

[hunspell-dict-qs](https://github.com/adiabatic/hunspell-dict-qs) is 883 hand-made Quikscript spellings, 867 of them distinct, with **no Latin column at all**. The exercise was to recover the headword for each — sound the entry out against the reversed segment mapping, match the result to ReadLex, check the reading against the entry's own `po:` field, affix flags and comment — and then classify every disagreement with the Manual as arbiter. That was done, at commit `781a01f` of that repository. This section is its result. **The table is not checked in and the validator does not run this check**, for reasons given at the end.

Of the 867, 691 agreed outright, 71 were §III contractions this lexicon applies to no column, and 26 were words ReadLex has no entry for. That leaves 79 real differences: 38 where both spellings are defensible and the two sources simply assume different sounds, 37 where the hand dictionary is wrong by the Manual's own rules, 4 gaps in this project's rules, and **no generator bugs** — a checked result, in that every difference with a lexicon counterpart was read against the Manual rule owning that word's ending.

The hand dictionary's own errors cluster, which is what a hand-written list does: it never applies [Con-, Com-][con], so computer, command, control, consider and compete all keep their ·Key·Utter-; it drops the invariable ·Utter of [-en, -on][en] in given, second, seven, listen and written; it misses [-age][age] in message and language. It gets -man right at human, roman, englishman and rifleman, and misses it only at German.

The four gaps on this side are the yield, and were filed as [#10](https://github.com/adiabatic/quikscript-lexicon/issues/10) and [#12](https://github.com/adiabatic/quikscript-lexicon/issues/12). The first is closed; the three under #12 are live:

- **terminal -y after a full `iː`, now fixed.** The rewriting rules fired on ·It and ·Utter only — the "·Et is not a reducible vowel" ruling in [`docs/orthographic-rules.md`](orthographic-rules.md), which as encoded also excluded ReadLex's full `iː`. So an unstressed terminal -e/-ee/-ae kept ·Eat where Read says the spelling "certainly must be constant" and reserves ·Eat "for distinction where the terminal is stressed". The shape reaches 159 element words over 169 corpus rows: 21 of them are compounds whose last element is a stressed word in its own right — carefree, honeybee, braintree — and 63 are classical plurals and names whose `-es` is an ending of its own — theses, vortices, hades — and both sets were right as they stood. Since stress is Read's own discriminator and ReadLex does not mark it inside an unhyphenated compound, the split is ruled on word by word in `rule-words.tsv`; [`docs/orthographic-rules.md`](orthographic-rules.md#5-whether-a-terminal--y-that-readlex-writes-in-full-is-stressed) has the argument. The hand dictionary's maybe with ·It is what pointed at this, and the lexicon now agrees with it.
- **the noun being**, under [-ing][ing]'s "spell the root fully … with somewhat changed meaning" rider.
- **doing**, which the [-ing][ing] section gives as ·Day·Oolong among the root contractions plus affix, where §III's own list stops at do, did, don't and didn't.
- **wasn't**, where the was outline is applied to the word alone and not inside the contraction, though the Manual's own gown-shop specimen writes ·Way·Utter·Zoo·No·Tea.

**Why none of this is wired into the validator.** An alignment table was built and then removed. 788 of its 867 rows said only that a source the [authority ordering](#authority) calls suggestive still agreed with us, which is not evidence of anything; what those rows would do, standing, is go stale and demand re-triage every time a rule moved. The tripwire is redundant besides — a rule change already trips the Manual fixtures, the pinned rewrite counts, the round-trip counts and the artifact-freshness check, all of them anchored to sources that arbitrate. The value here was in doing the triage once and reading the result. Redoing it against a newer `en_QS.dic` is a fresh exercise, not a regression.

## Coverage in the build log

`make artifacts` ends by printing what the build touched: rows converted, rows skipped, and how many rows carry each sparse column.

The same counts are pinned in `validate.py`, so the log is a convenience and the assertion is elsewhere — which is why it stops where it does. The per-rule and per-word-sign rewrite counts, and the reading of which rules rewrote nothing, are `make validate`'s to report and to adjudicate; printing them from the build too was a second, unasserted copy, and a build that only checks its output against disk (`--check`) counts none of it.

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
[con]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#prefix-con-com
[en]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-en-on
[age]: https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-age
