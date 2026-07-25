# The canonical IPA → Quikscript segment mapping

This is the spec for [`src/qslex/data/ipa-to-qs.tsv`](../src/qslex/data/ipa-to-qs.tsv): a total function from every symbol that appears in ReadLex's IPA column to Quikscript letters, encoded as PUA codepoints U+E650–U+E67E per the [quikscript.net CSUR proposal][csur]. It resolves issue #1.

Authority links go to the [AMS Manual transcription][manual]. Everything below was verified against the PUA text of that document; spellings quoted as letter names were extracted codepoint-for-codepoint.

## Artifacts

- `src/qslex/data/ipa-to-qs.tsv` — the mapping. Columns: `ipa` (token), `condition` (empty, or `stressed`/`unstressed`, or `pre-r`/`no-r`), `qs` (PUA string), `codepoints` (`U+XXXX …`), `letters` (`·Name·Name`), `kind`, `example`, `authority` (anchor slug into the Manual).
- `src/qslex/data/ipa-quirks.tsv` — 63 pre-tokenization normalizations for upstream data quirks (issue #7's territory). Applied top to bottom; scopes are `row` (exact-string), `sub` (literal substring), `regex`. Each names the words it may touch, and the validator holds it to that list.
- `src/qslex/data/ipa-overrides.tsv` — 43 per-word stress overrides, for the words where the mechanical ɪə rule provably contradicts the evidence. See [Where the mechanical rule breaks](#where-the-mechanical-rule-breaks-and-the-override-file).
- `src/qslex/data/shavian-divergences.tsv` — 173 words where the mapping deliberately contradicts ReadLex's Shavian column because the Manual prescribes otherwise. Every row carries its authority; the validator rejects one that does not.
- `src/qslex/` — mapping loader (self-verifies letters ↔ codepoints ↔ PUA agreement against the CSUR table), tokenizer, and the exhaustive validator.
- `data/readlex/` — the ReadLex corpus, vendored at a pinned commit with its MIT licence and SHA-256 ([provenance](../data/readlex/README.md)). The mapping tables live inside the package so an installed wheel can load them; the corpus lives outside it, because a consumer transcribing IPA does not need 6 MB of ReadLex.

Run the proofs:

```
uv run pytest
uv run python -m qslex.validate
uv run ruff check . && uv run ruff format --check . && uv run mypy
```

The validator tokenizes all 110,056 IPA strings and fails unless there is **zero unmapped residue**, every mapping row is exercised at least once, every quirk rule and stress override fires, no quirk rule touches a word it does not declare, no ɪə decision contradicts the Shavian column without a recorded authority, no structural marker leaks into the output, and the corpus invariant counts hold (R 27,317; Ə 7,778; I 616; Æ 1,707; Ɑː 1,705; ʍ 538; word signs 156; weak `u` 578; schwa-less `ɪR`/`aɪR`/`aʊR` nonexistent). It verifies the corpus digest first, so those pinned counts can only move when someone deliberately bumps the corpus.

## Tokenizer contract

Tokens are matched greedily, longest first, over the quirk-normalized string. Three rules, all load-bearing:

- **A stress mark bounds vowel tokens.** coyote `kaɪˈəʊti` must parse as `aɪ·ˈ·əʊ`, never as an `aɪə` triphthong spanning the mark. This falls out of literal contiguous matching.
- **A stress mark does not break vowel+r adjacency.** thereafter `ðeəˈrÆftəR` still counts its `eə` as pre-r (·Eight); the `pre-r`/`no-r` lookahead skips marks before testing for `r`/`R`.
- **A schwa-final vowel token yields to a following GOAT vowel.** In bio `ˈbaɪəʊ`, diode, flyover, heliograph (88 rows), the `ə` belongs to `əʊ`, so `aɪə`/`ɪə` decline to match when `ʊ` follows and the split is `aɪ`+`əʊ` → ·I·Owe (the Shavian column concurs: 𐑲𐑴). The validator enforces this with an əʊ-conservation check: every `əʊ` in the normalized text must surface as an ·Owe token. No `eəʊ`/`ʊəʊ`/`aʊəʊ` exists in the corpus, so the rule only ever fires on the bio class.

Chunks are the `-`/space/`+`-separated spans of an entry; stress conditioning never crosses a chunk boundary, and token matching cannot cross a separator — which is also what keeps hiatus sequences like angrier `ˈæŋɡrɪ+əR` from fusing into a spurious `ɪə`. Stress marks map to no letters. Of the three separators, `-` and space are orthographic and pass through as themselves; `+` is a ReadLex encoding artifact marking hiatus, carries no orthographic meaning, and is therefore `kind=hiatus` and emitted as nothing — angrier is ·At·Oolong·Gay·Roe·It·Utter·Roe, with no `+` in it. The validator forbids a `+` in any output.

## The obvious rows

All consonants are 1:1: p→·Pea b→·Bay t→·Tea d→·Day k→·Key ɡ→·Gay θ→·Thaw ð→·They f→·Fee v→·Vie s→·See z→·Zoo ʃ→·She ʒ→·Zhivago tʃ→·Cheer dʒ→·Jay j→·Ye w→·Way h→·He m→·May n→·No ŋ→·Oolong l→·Low r→·Roe, plus ʍ→·Why (538 rows keep the wh distinction — the reason this project pivots on the IPA column), x→·Loch (koch, the corpus's one /x/), and ɬ→·Llan (llanfair, via quirk normalization of upstream `L`).

Simple vowels: ɪ→·It iː→·Eat e→·Et eɪ→·Eight æ→·At aɪ→·I ɑː→·Ah ɒ→·Ox ɔː→·Awe ɔɪ→·Oy aʊ→·Out əʊ→·Owe ʊ→·Foot uː→·Ooze, and the big merge ə, ʌ, ɜː → ·Utter — [§ Vowels + R][vr]: letter 36 "serves both for Hut and for Hurt, for Us, Upon and Urge" (Manual-verified: hut = ·He·Utter·Tea, hurt = ·He·Utter·Roe·Tea).

## Non-obvious rows, with one example each

| Row | Example | Result | Authority |
|---|---|---|---|
| `R` → ·Roe, always | baker `ˈbeɪkəR` | ·Bay·Eight·Key·Utter·Roe | [§ Spell all R's][rs]; [§ Vowels + R][vr] (-er = ·Utter·Roe) |
| happY `i` → ·It | money, coffee | final ·It | [§ Terminal -y][y] |
| weak `u` → ·Ooze | visual `ˈvɪʒuəl` | ·Vie·It·Zhivago·Ooze·Utter·Low | [§ -al, -el, -le, -il][al] — see decision below, which explains the ·Zhivago |
| `juː` → ·Ye + ·Ooze (compositional) | few `fjuː` | ·Fee·Ye·Ooze | [alphabet chart][chart] ("Ewe, Use, Few") |
| `eə` pre-r → ·Eight | there `ðeəR` | ·They·Eight·Roe | [alphabet chart][chart] ("Pair, Dare, There"); common-words there = ·They·Eight·Roe |
| `eə` no-r → ·Et·Utter | yeah `ˈjeə` | ·Ye·Et·Utter | lexical-scale: 3 occurrences (yeah ×2, elo); Shavian 𐑘𐑧𐑩 precedent — but see the note below |
| `ʊə` → ·Ooze·Utter | moor `mʊəR` | ·May·Ooze·Utter·Roe | [§II][sec2] join table: moor |
| `ɪə` stressed → ·Eat·Utter | career `kəˈrɪəR` | ·Key·Utter·Roe·Eat·Utter·Roe | [§ Terminal -ier, -ior][ier]; [§ -ia, -ea][ia] (Korea, idea); §II (dear, mere, fear) |
| `ɪə` unstressed → ·It·Utter | carrier `ˈkærɪəR` | ·Key·At·Roe·It·Utter·Roe | [§ Terminal -ier, -ior][ier] (happier, senior, junior); [§ -ia, -ea][ia] (India, area) |
| `aɪə` pre-r → ·I (schwa absorbed) | mire `ˈmaɪəR` | ·May·I·Roe | [§II][sec2]: mire = ·May·I·Roe |
| `aʊə` pre-r → ·Out (schwa absorbed) | our `ˈaʊəR` | ·Out·Roe | [§II][sec2] (sour); [§ Common words][common]: our = ·Out·Roe |
| `aɪə` no-r → ·I·Utter | science `ˈsaɪəns` | ·See·I·Utter·No·See | decision below |
| `aʊə` no-r → ·Out·Utter | bowel `ˈbaʊəl` | ·Bay·Out·Utter·Low | decision below |

Convergence note: ReadLex writes India-type words with happY `i` + `ə` (`ˈɪndiə`) and happier-type words with `ɪə`; both routes produce ·It·Utter, matching the Manual's -ia rule either way.

Caveat on `eə` no-r: of its three occurrences, two are yeah, whose Shavian 𐑧𐑩 does support ·Et·Utter. The third is elo, and there the Shavian column is 𐑺𐑤𐑴 (AIR) — it contradicts its own row's IPA rather than corroborating the mapping. So this row rests on yeah alone, and elo is an upstream data defect that issue #7 should fix at source rather than evidence for anything. The validator pins the count at 3 so that fixing it upstream is noticed here.

## The stress rule for ɪə

Mechanical, per chunk, scanning left from the `ɪə`:

1. Hit a stress mark (ˈ or ˌ) before any vowel → **stressed** (only consonants between the mark and the ɪə syllable: appear `əˈpɪəR`, career `kəˈrɪəR`).
2. Hit a vowel first → **unstressed** (happier `ˈhæpɪəR`, senior, period's second ɪə).
3. Reach the chunk start → **stressed** if the chunk carries no stress mark at all, else unstressed. This covers the Manual-cited monosyllables (dear `dɪəR`, here, year — ReadLex monosyllables carry no ˈ) and, identically, mark-less compound elements: anti-hero `ˈænti-hɪərəʊ`, world-weary, operating-theatre keep the ·Eat·Utter of their standalone forms. Shavian corroborates two of those three — hero 𐑣𐑽 and weary 𐑢𐑽 — but **not** theatre, which is 𐑔𐑾. An earlier draft claimed all three concurred; in fact Shavian writes 𐑾 for every non-rhotic ɪə regardless of stress, so in that environment it expresses no opinion and cannot corroborate anything.

Two recorded interpretations of issue #1's wording:

- **ˌ counts as stress.** The issue's rule names only ˈ, but bacteriology `bækˌtɪəriˈɒlədʒi` and 73 similar occurrences put ˌ directly before the ɪə syllable; classifying them stressed preserves morphological families (bacteria → bacteriology, both ·Eat·Utter).
- **Rule 3 generalizes "monosyllable."** A literal monosyllable test would flip the hero/weary/theatre compounds to ·It·Utter, splitting them from their standalone forms.

### Where the mechanical rule breaks, and the override file

The rule above reads ReadLex's stress marks, and ReadLex does not mark stress inside compounds. So rule 2 demotes the second element of any **unhyphenated** compound — the first element's vowel is in the same chunk — while the hyphenated form comes out right, because the hyphen starts a new chunk:

| | mechanical | standalone form |
|---|---|---|
| `musk-deer` | ·Day·**Eat**·Utter·Roe ✓ | deer `dɪəR` → ·Day·Eat·Utter·Roe |
| `reindeer` | ·Day·**It**·Utter·Roe ✗ | same morpheme, no hyphen |

The same fault ran through -sphere (atmosphere, biosphere, stratosphere…), -mere placenames, headgear, greybeard, compeer, godfearing, and — via rule 3's pre-tonic branch — hereafter/hereby/hereof/hereto, which split from herein/herewith purely on whether ReadLex happened to write a `ˌ`. There is no IPA-only signal that separates reindeer from happier: both are stress-mark + full vowel + Cɪə(R) at chunk end. Relaxing rule 2 would wreck the 1,751 non-rhotic occurrences the Manual explicitly makes unstressed (Austria, India, Virginia, area).

So the rule stays, and the exceptions are **data**: `src/qslex/data/ipa-overrides.tsv`, 43 rows keyed on the exact normalized IPA string, each naming the words it covers, the condition to force, and the evidence. The validator fails if any override stops firing or touches a word it does not declare, so a dead override cannot linger.

### The Shavian column as an oracle

ReadLex's Shavian column is independent evidence: it writes 𐑽 (EAR) for stressed rhotic ɪə and 𐑦𐑼 for unstressed. The validator therefore checks, for every one of the 110,056 rows, that the number of 𐑽 in the Shavian column equals the number of ɪə tokens the mapping resolves as stressed-and-rhotic.

Counting per row rather than aligning per segment is a deliberate trade: segment alignment between IPA and Shavian is itself a heuristic, and a wrong alignment would produce confident false failures. The cost is that two compensating errors in the same row would cancel. That exposure is bounded and small — 178 rows carry more than one ɪə token, and only **42 rows (29 words)** have two *rhotic* ɪə differing in stress, the shape where a pure swap would hide. 39 of those 42 are already recorded divergences. So this is a strong row-level invariant, not a per-segment proof.

Any mismatch fails the build unless it is enumerated in `src/qslex/data/shavian-divergences.tsv` **with an authority**. That file has 173 rows, and they are not excuses — they are the places where the Manual outranks ReadLex:

- **161 rows, the -ier/-ior families** (-ier/-ior 111, -iary 21, -iorate 18, -erior 9, -iorism 2: barrier, courier, senior, junior, warrior, apiary, ameliorate, exterior, incendiarism). [§ Terminal -ier, -ior][ier] is explicit — "If unstressed, -·It·Utter·Roe : if stressed, -·Eat·Utter·Roe" — and names happier, carrier, furrier, senior, junior as the unstressed set. ReadLex is internally inconsistent here: it writes carrier 𐑒𐑨𐑮𐑦𐑼 but barrier 𐑚𐑨𐑮𐑽, the same rhyme, and splits the homograph furrier by sense. The Manual arbitrates.
- **11 rows, the meteor- and unresolved stems** (meteorite, meteorology, meteoroid, panjshir, protocadherin, tyrconnel), authority `no-promotion-evidence`: Shavian says 𐑽, but the stem has no stressed-EAR attestation anywhere in ReadLex — `meteor` itself is `ˈmiːtɪɔːR` → 𐑥𐑰𐑑𐑦𐑹, no EAR at all — and the Manual's *terminal* rule does not reach a word-medial -eor-. Recorded rather than guessed.
- **1 row, `we're`**, where Shavian spells the contraction morphologically (𐑢𐑰𐑼 = we + 're) rather than phonologically.

Seven of the 173 carry `condition=none`: they are words still written with happY `i`, so they produce no ɪə token at all and only the Shavian column claims an EAR there. The loader enforces that vocabulary, and the validator checks each recorded Shavian string against the corpus, so a divergence row cannot quietly go stale.

Corpus outcome: 1,267 stressed / 2,447 unstressed occurrences. Against the Shavian oracle: 1,088 rows agree, 173 diverge with a recorded authority, **0 diverge unexpectedly**, and 2,247 carry a non-rhotic ɪə, where Shavian writes 𐑾 regardless of stress and so has no opinion to offer.

## Decision: weak u = ·Ooze (not ·Foot)

The Manual spells visual ·Vie·It·Zoo·Ye·Ooze·Utter·Low ([§ -al, -el, -le, -il][al]) — verified codepoint by codepoint, the fifth letter is U+E67E ·Ooze, not U+E67D ·Foot. The weak-u vowel is therefore unambiguously **·Ooze** in the primary source, and this project's standing rule is that the Manual arbitrates. ·Foot (arguably closer to the modern lax [u] of coalesced /ˈvɪʒuəl/, /əkˈsentʃueɪt/) is rejected for that reason and recorded here.

Two honest qualifications. First, ReadLex's own Shavian column writes visual with 𐑫 (WOOL, i.e. FOOT) — so on this row the Shavian column **dissents and the Manual overrules it**, the reverse of the corroboration relied on elsewhere in this spec. Second, the Manual's ·Ooze is the second element of Read's /zj/, so the evidence is direct for the `ju`/`tʃu`/`ʒu` cases and extrapolated to post-consonantal hiatus (affluence, influence). The consonant difference is expected and intentional: the Manual's 1966 pronunciation had /zj/ (·Zoo·Ye); ReadLex has ʒ, and per issue #8 the senior column follows the IPA, so the lexicon writes ·Vie·It·Zhivago·Ooze·Utter·Low.

The row covers all **578** short-`u` occurrences (ju 170, tʃu 207, ʒu 90, plus 111 hiatus cases after other consonants). The validator pins that count, so the figure cannot drift again.

## Decision: non-rhotic aɪə/aʊə keep the schwa

Issue #1 asked to "verify the handful of non-rhotic aɪə/aʊə (if any) get the same treatment" as the pre-r absorption. Verification overturned the premise: there are **518 aɪə and 51 aʊə non-rhotic occurrences** — science, client, quiet, diet, giant, lion, diary, trial, dial, bowel, towel, vowel, avowal, allowance — not a handful. (A further 31 raw `aɪəʊ` matches are bio-class words where the `ə` belongs to a following GOAT vowel; the tokenizer splits those as `aɪ`+`əʊ` per the contract above.) The mapping absorbs the schwa **only before r/R**, keeping ·I·Utter / ·Out·Utter otherwise, because:

- Every absorption example in the Manual is a vowel+R join (mire, sour, our, desire, hours, §II join tables), and the sequences ·I·Utter and ·Out·Utter appear nowhere in the document. Almost no candidate non-rhotic word is spelt in the Manual at all (dial, lion, diary, towel, quiet, riot, fire, power are absent; trial, vowel, violence, liable occur in prose only). The one exception cuts the right way: **highest** is spelt, in [§ Terminals -ess, -est][ess], and it does **not** absorb the schwa — it writes a vowel letter, `-·Et·See·Tea`. Note that the letter is ·Et rather than ·Utter, which is a suffix convention this segment mapping cannot express; see [What a segment mapping cannot do](#what-a-segment-mapping-cannot-do).
- The Manual's loyal = ·Low·Oy·Utter·Low ([§ -al, -el, -le, -il][al]) keeps the schwa in the exactly analogous non-rhotic diphthong+ə position.
- Absorption would collapse minimal pairs: quiet/quite, lion/line, vial/vile, science/signs.

## Tagged pass-throughs (owned by later issues)

| Token | Naive value | Tag semantics | Owner |
|---|---|---|---|
| `Ə` (7,778) | ·Utter | Shavian epenthetic-vowel site in -es/-ed (kisses `ˈkɪsƏz`); QS convention differs | #2 |
| `I` (616) | ·It | unstressed-ɪ site where Shavian writes schwa (banquet `ˈbæŋkwIt`) | #2 |
| `Ɑː`/`Æ` (1,705/1,707) | ·Ah / ·At | TRAP-BATH dual variant rows (bath `bⱭːθ`/`bÆθ`) | #4 (row policy) |
| `Ð T N V F` (156) | ·They ·Tea ·No ·Vie ·Fee | word signs the/to/and/of/for | #3 (canonical spellings) |

## What a segment mapping cannot do

A total function from IPA segments to letters cannot see suffix identity, so several of the Manual's prescriptions are structurally out of reach here. They are listed so that nobody mistakes this table's silence for the Manual's. All belong to the rules layer, issue #2.

| Manual rule | Manual spelling | This mapping | Scale |
|---|---|---|---|
| [§ Terminals -ess, -est, -less, -ness][ess]: "Distinguished from the -us, -ous terminal by writing vowel No. 28 ·Et" | hostess `-·Et·See`, highest `-·Et·See·Tea`, hopeless `-·Low·Et·See`, goodness `-·No·Et·See` | ·Utter, because ReadLex writes plain `ə` in both families | 1,856 rows (1,789 words); the contrasting [-us/-ous][us] family, 694 rows, is correctly ·Utter |
| [§ Terminal -al, -el, -le, -il][al]: "omit any unstressed vowel sound between L and the preceding consonant" | final, rifle, couple, easel, devil lose the vowel; Spaniel = ·See·Pea·At·No·Ye·Low | keeps it: final = ·Fee·I·No·Utter·Low | the same section that authorises weak-u = ·Ooze |
| [§ Terminal -ing][ing]: affix -ing omits the vowel | calling = ·Key·Awe·Low·Oolong (but root wing keeps ·It) | ·It always | affix/root distinction is morphological |
| [§ Terminal -tion][tion], [§ -land, -ment][land] | action = ·At·Key·She·No | ·At·Key·She·Utter·No | |
| [§ Terminal -age][age] | manage = `-·Utter·Jay`, marriage = `-·It·Jay` after a -y root | ·It, since ReadLex writes plain `ɪ` — so the `I` tag does not catch it | |

The pattern is consistent: Quikscript's terminal conventions are keyed to the *spelling* of the suffix, and the IPA column does not carry that information. Issue #2 owns them; issue #1's mapping deliberately produces the segment-faithful form and lets the rules layer rewrite it.

## Quirk normalizations (→ issue #7)

`src/qslex/data/ipa-quirks.tsv` fixes 63 rules' worth of upstream irregularities before tokenization — stray Shavian letters (𐑴 in hyperfocus, 𐑑 in oakshott), ASCII `g` for `ɡ` (29 rows), Latin-orthography leaks (`ai` in brainpan/brainstem = eɪ but in lobotomise = aɪ, per the Shavian column), bare `a`/`ɑ`/`ɔ` missing length or laxness marks, a spurious length mark (goulburn `əː` — not in issue #7's list; found by the residue check), misplaced marks (nauvoo `nɔˈː`, ursae majoris `dˈʒ`), missing hiatus markers that let `t`+`ʃ` fuse (sweatshirt, wiltshire) or a stray one that split `eə` (whate'er), `dz` for `dʒ` (jonnie), a missing `ə` in SQUARE (sierra leone), and the `.`/`'`/U+0329 strays.

The largest single class, 29 rows, is **happY `i` written for EAR `ɪ`**: ReadLex spells shakespeare `ˈʃeɪkspiəR`, lightyear `ˈlaɪtjiəR`, pierce `piəRs` and 26 others with `iə`, which tokenizes to ·It·Utter — the unstressed spelling — while their own Shavian column says 𐑽. Upstream contradicts itself in the clearest possible way here: it writes god-fearing `ˈɡɒd-ˌfiərɪŋ` but godfearing `ˈɡɒdfɪərɪŋ`, magnetosphere with `iə` but atmosphere with `ɪə`. Every one of the 29 is justified by an independently attested standalone form (year, sphere, mere, near, sheer, zero, series, period), and three of them — lear, pierce, vere — sit inside a structural fact: of the 190 mark-less `(C)(C)ɪəR` monosyllable rows in ReadLex, every single one carries 𐑽, and exactly those three are written with `iə`. Nine of the 29 need a stress override on top of the normalization, because after the fix the mechanical rule still demotes them.

Every rule names the words it affects, and the validator now **enforces** that list: a rule that touches a word it does not declare fails the build, as does a rule that declares a word it no longer touches. Two caveats on the evidence, since an earlier draft of this document overclaimed it:

- Most rules were cross-checked against the row's Shavian column, but not all of them could be. `L`→`ɬ` is a **judgment call, not Shavian-corroborated**: llanfair's Shavian is 𐑤𐑨𐑯𐑓𐑺, plain /l/, because Shavian has no letter for /ɬ/ and upstream could not have written one. Quikscript does have ·Llan, and the capital `L` is clearly a deliberate upstream marker, so the rule stands — but on judgment. Likewise drm's Shavian is an initialism with no vowel letters, so it cannot corroborate `ɑ`→`ɑː`; the other nine words of that rule are 𐑸-confirmed.
- goulburn's fix was originally `əː`→`ɜː`, citing Shavian 𐑼. That citation refutes rather than supports NURSE: 𐑼 is schwa+r (auburn, melbourne), while NURSE is 𐑻 (burn). The rule now drops the spurious length mark instead, `əː`→`ə`. Output is unchanged — ə and ɜː both give ·Utter — but the normalized corpus no longer carries a wrong vowel for issues #2 and #4 to inherit.

The validator fails if any rule stops matching, so the file doubles as a to-do list for upstream fixes. Because the corpus is vendored at a pinned commit, that can only happen when someone deliberately bumps the pin — the file cannot go red on its own.

## Reconciling issue #1's counts

- ʊə "1,229 total": 760 standalone `ʊə` tokens + 321 inside `aʊə` + 148 regex matches spanning the `əʊ`+`ə` boundary (goer, follower) = 1,229. The issue's figure was a raw substring count.
- aɪəR 515 / aʊəR 226: capital-R-only rows. Token-level pre-r counts are 655/270 because intervocalic lowercase r (firing, dowry) conditions the same absorption.
- EAR "always ɪəR, never ɪR": confirmed — the validator forbids schwa-less `ɪR`/`aɪR`/`aʊR`.
- GOAT conservation: all 10,506 `əʊ` in the normalized text tokenize as ·Owe — none is lost to a neighboring triphthong token.
- Affricate conservation: 4,355 `tʃ` tokens against 4,352 Shavian 𐑗, and 5,802 `dʒ` against 5,793 𐑡. The gaps of 3 and 9 are exactly the initialisms whose Shavian column spells letter names rather than sounds — adhd, nlg and who for `tʃ`; dm, gmt, gnp, gop, lgbt, lgbtq, lgbtqi, lgbtqia and again nlg for `dʒ`. Both counts are pinned, which is what now guards the compound-boundary fusion fix.

## Acceptance (issue #1)

- [ ] **Mapping file merged** — `src/qslex/data/ipa-to-qs.tsv` exists and is complete, but this branch is not merged and has no PR yet. The box stays unticked until it is.
- [x] Tokenizer proves total coverage — zero unmapped residue over all 110,056 IPA strings, including stress marks inside vowel+r sequences, reproducible from a clean checkout against the vendored corpus
- [x] Stress-conditioned ɪə rule implemented, audited, and cross-checked against the Shavian column
- [x] Weak-u decision resolved (·Ooze) and recorded above

## Out of scope, deliberately

·Excite (U+E66B) and ·Exam (U+E66C) are in the CSUR table but appear in no mapping row. That is intentional and not an oversight: the Manual scopes them to "a Tall ·Excite for ·Key·See sounds : a Deep ·Exam for ·Gay·Zoo sounds — **but only where Orthodox spells these sounds with X**", giving ·Excite in tax, fix, ox but ·Key·See in tacks, licks, locks. Tax and tacks are homophones, so the choice is unrecoverable from IPA alone and cannot belong to a segment mapping. Per issue #8 the lexicon stores the ligature form in a `qs_x` column built on the senior column; the rule spec is #2 and the artifact shape is #4.

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
