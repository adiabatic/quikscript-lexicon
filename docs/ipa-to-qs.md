# The canonical IPA → Quikscript segment mapping

This is the spec for [`data/ipa-to-qs.tsv`](../data/ipa-to-qs.tsv): a total function from every symbol that appears in ReadLex's IPA column to Quikscript letters, encoded as PUA codepoints U+E650–U+E67E per the [quikscript.net CSUR proposal][csur]. It resolves issue #1.

Authority links go to the [AMS Manual transcription][manual]. Everything below was verified against the PUA text of that document; spellings quoted as letter names were extracted codepoint-for-codepoint.

## Artifacts

- `data/ipa-to-qs.tsv` — the mapping. Columns: `ipa` (token), `condition` (empty, or `stressed`/`unstressed`, or `pre-r`/`no-r`), `qs` (PUA string), `codepoints` (`U+XXXX …`), `letters` (`·Name·Name`), `kind`, `example`, `authority` (anchor slug into the Manual).
- `data/ipa-quirks.tsv` — pre-tokenization normalizations for upstream data quirks (issue #7's territory). Applied top to bottom; scopes are `row` (exact-string), `sub` (literal substring), `regex`.
- `src/qslex/` — mapping loader (self-verifies letters ↔ codepoints ↔ PUA agreement against the CSUR table), tokenizer, and the exhaustive validator.

Run the proofs:

```
uv run pytest
uv run python -m qslex.validate tmp/readlex/kingsleyreadlexicon.tsv
```

The validator tokenizes all 110,056 IPA strings and fails unless there is **zero unmapped residue**, every mapping row is exercised at least once, every quirk rule fires, and the corpus invariant counts hold (R 27,317; Ə 7,778; I 616; Æ 1,707; Ɑː 1,705; ʍ 538; word signs 156; schwa-less `ɪR`/`aɪR`/`aʊR` nonexistent).

## Tokenizer contract

Tokens are matched greedily, longest first, over the quirk-normalized string. Three rules, all load-bearing:

- **A stress mark bounds vowel tokens.** coyote `kaɪˈəʊti` must parse as `aɪ·ˈ·əʊ`, never as an `aɪə` triphthong spanning the mark. This falls out of literal contiguous matching.
- **A stress mark does not break vowel+r adjacency.** thereafter `ðeəˈrÆftəR` still counts its `eə` as pre-r (·Eight); the `pre-r`/`no-r` lookahead skips marks before testing for `r`/`R`.
- **A schwa-final vowel token yields to a following GOAT vowel.** In bio `ˈbaɪəʊ`, diode, flyover, heliograph (88 rows), the `ə` belongs to `əʊ`, so `aɪə`/`ɪə` decline to match when `ʊ` follows and the split is `aɪ`+`əʊ` → ·I·Owe (the Shavian column concurs: 𐑲𐑴). The validator enforces this with an əʊ-conservation check: every `əʊ` in the normalized text must surface as an ·Owe token. No `eəʊ`/`ʊəʊ`/`aʊəʊ` exists in the corpus, so the rule only ever fires on the bio class.

Chunks are the `-`/space/`+`-separated spans of an entry; stress conditioning never crosses a chunk boundary, and token matching cannot cross a separator — which is also what keeps hiatus sequences like angrier `ˈæŋɡrɪ+əR` from fusing into a spurious `ɪə`. Stress marks and structural separators map to no letters (separators pass through as themselves).

## The obvious rows

All consonants are 1:1: p→·Pea b→·Bay t→·Tea d→·Day k→·Key ɡ→·Gay θ→·Thaw ð→·They f→·Fee v→·Vie s→·See z→·Zoo ʃ→·She ʒ→·Zhivago tʃ→·Cheer dʒ→·Jay j→·Ye w→·Way h→·He m→·May n→·No ŋ→·Oolong l→·Low r→·Roe, plus ʍ→·Why (538 rows keep the wh distinction — the reason this project pivots on the IPA column), x→·Loch (koch, the corpus's one /x/), and ɬ→·Llan (llanfair, via quirk normalization of upstream `L`).

Simple vowels: ɪ→·It iː→·Eat e→·Et eɪ→·Eight æ→·At aɪ→·I ɑː→·Ah ɒ→·Ox ɔː→·Awe ɔɪ→·Oy aʊ→·Out əʊ→·Owe ʊ→·Foot uː→·Ooze, and the big merge ə, ʌ, ɜː → ·Utter — [§ Vowels + R][vr]: letter 36 "serves both for Hut and for Hurt, for Us, Upon and Urge" (Manual-verified: hut = ·He·Utter·Tea, hurt = ·He·Utter·Roe·Tea).

## Non-obvious rows, with one example each

| Row | Example | Result | Authority |
|---|---|---|---|
| `R` → ·Roe, always | baker `ˈbeɪkəR` | ·Bay·Eight·Key·Utter·Roe | [§ Spell all R's][rs]; [§ Vowels + R][vr] (-er = ·Utter·Roe) |
| happY `i` → ·It | money, coffee | final ·It | [§ Terminal -y][y] |
| weak `u` → ·Ooze | visual `ˈvɪʒuəl` | ·Vie·It·Zhivago·Ooze·Utter·Low | [§ -al, -el, -le, -il][al] — see decision below |
| `juː` → ·Ye + ·Ooze (compositional) | few `fjuː` | ·Fee·Ye·Ooze | [alphabet chart][chart] ("Ewe, Use, Few") |
| `eə` pre-r → ·Eight | there `ðeəR` | ·They·Eight·Roe | [alphabet chart][chart] ("Pair, Dare, There"); common-words there = ·They·Eight·Roe |
| `eə` no-r → ·Et·Utter | yeah `ˈjeə` | ·Ye·Et·Utter | lexical-scale: 3 occurrences in the corpus (yeah ×2, elo quirk row); Shavian 𐑘𐑧𐑩 precedent |
| `ʊə` → ·Ooze·Utter | moor `mʊəR` | ·May·Ooze·Utter·Roe | [§II][sec2] join table: moor |
| `ɪə` stressed → ·Eat·Utter | career `kəˈrɪəR` | ·Key·Utter·Roe·Eat·Utter·Roe | [§ Terminal -ier, -ior][ier]; [§ -ia, -ea][ia] (Korea, idea); §II (dear, mere, fear) |
| `ɪə` unstressed → ·It·Utter | carrier `ˈkærɪəR` | ·Key·At·Roe·It·Utter·Roe | [§ Terminal -ier, -ior][ier] (happier, senior, junior); [§ -ia, -ea][ia] (India, area) |
| `aɪə` pre-r → ·I (schwa absorbed) | mire `ˈmaɪəR` | ·May·I·Roe | [§II][sec2]: mire = ·May·I·Roe |
| `aʊə` pre-r → ·Out (schwa absorbed) | our `ˈaʊəR` | ·Out·Roe | [§II][sec2] (sour); [§ Common words][common]: our = ·Out·Roe |
| `aɪə` no-r → ·I·Utter | science `ˈsaɪəns` | ·See·I·Utter·No·See | decision below |
| `aʊə` no-r → ·Out·Utter | bowel `ˈbaʊəl` | ·Bay·Out·Utter·Low | decision below |

Convergence note: ReadLex writes India-type words with happY `i` + `ə` (`ˈɪndiə`) and happier-type words with `ɪə`; both routes produce ·It·Utter, matching the Manual's -ia rule either way.

## The stress rule for ɪə

Mechanical, per chunk, scanning left from the `ɪə`:

1. Hit a stress mark (ˈ or ˌ) before any vowel → **stressed** (only consonants between the mark and the ɪə syllable: appear `əˈpɪəR`, career `kəˈrɪəR`).
2. Hit a vowel first → **unstressed** (happier `ˈhæpɪəR`, senior, period's second ɪə).
3. Reach the chunk start → **stressed** if the chunk carries no stress mark at all, else unstressed. This covers the Manual-cited monosyllables (dear `dɪəR`, here, year — ReadLex monosyllables carry no ˈ) and, identically, mark-less compound elements: anti-hero `ˈænti-hɪərəʊ`, world-weary, operating-theatre keep the ·Eat·Utter of standalone hero, weary, theatre (their Shavian column concurs, using stressed 𐑽).

Two recorded interpretations of issue #1's wording:

- **ˌ counts as stress.** The issue's rule names only ˈ, but bacteriology `bækˌtɪəriˈɒlədʒi` and 73 similar occurrences put ˌ directly before the ɪə syllable; classifying them stressed preserves morphological families (bacteria → bacteriology, both ·Eat·Utter).
- **Rule 3 generalizes "monosyllable."** A literal monosyllable test would flip the hero/weary/ theatre compounds to ·It·Utter, splitting them from their standalone forms.

Corpus outcome: 1,202 stressed / 2,482 unstressed occurrences; the validator prints the full audit.

## Decision: weak u = ·Ooze (not ·Foot)

The Manual spells visual ·Vie·It·Zoo·Ye·Ooze·Utter·Low ([§ -al, -el, -le, -il][al]) — the weak-u vowel is unambiguously **·Ooze** in the primary source, and this project's standing rule is that the Manual arbitrates. ·Foot (arguably closer to the modern lax [u] of coalesced /ˈvɪʒuəl/, /əkˈsentʃueɪt/) is rejected for that reason and recorded here. The consonant difference is expected and intentional: the Manual's 1966 pronunciation had /zj/ (·Zoo·Ye); ReadLex has ʒ, and per issue #8 the senior column follows the IPA, so the lexicon will write ·Vie·It·Zhivago·Ooze·Utter·Low. The row covers all 636 short-`u` occurrences (ju 170, tʃu 207, ʒu 90, plus hiatus after other consonants: affluence, influence).

## Decision: non-rhotic aɪə/aʊə keep the schwa

Issue #1 asked to "verify the handful of non-rhotic aɪə/aʊə (if any) get the same treatment" as the pre-r absorption. Verification overturned the premise: there are **518 aɪə and 51 aʊə non-rhotic occurrences** — science, client, quiet, diet, giant, lion, diary, trial, dial, bowel, towel, vowel, avowal, allowance — not a handful. (A further 31 raw `aɪəʊ` matches are bio-class words where the `ə` belongs to a following GOAT vowel; the tokenizer splits those as `aɪ`+`əʊ` per the contract above.) The mapping absorbs the schwa **only before r/R**, keeping ·I·Utter / ·Out·Utter otherwise, because:

- Every absorption example in the Manual is a vowel+R join (mire, sour, our, §II join tables). None of the candidate non-rhotic words appears with a spelling anywhere in the Manual (dial, lion, diary, towel, quiet, riot, fire, power, etc. are absent; trial and vowel occur in prose only).
- The Manual's loyal = ·Low·Oy·Utter·Low ([§ -al, -el, -le, -il][al]) keeps the schwa in the exactly analogous non-rhotic diphthong+ə position.
- Absorption would collapse minimal pairs: quiet/quite, lion/line, vial/vile, science/signs.

## Tagged pass-throughs (owned by later issues)

| Token | Naive value | Tag semantics | Owner |
|---|---|---|---|
| `Ə` (7,778) | ·Utter | Shavian epenthetic-vowel site in -es/-ed (kisses `ˈkɪsƏz`); QS convention differs | #2 |
| `I` (616) | ·It | unstressed-ɪ site where Shavian writes schwa (banquet `ˈbæŋkwIt`) | #2 |
| `Ɑː`/`Æ` (1,705/1,707) | ·Ah / ·At | TRAP-BATH dual variant rows (bath `bⱭːθ`/`bÆθ`) | #4 (row policy) |
| `Ð T N V F` (156) | ·They ·Tea ·No ·Vie ·Fee | word signs the/to/and/of/for | #3 (canonical spellings) |

## Quirk normalizations (→ issue #7)

`data/ipa-quirks.tsv` fixes 25 rules' worth of upstream irregularities before tokenization — stray Shavian letters (𐑴 in hyperfocus, 𐑑 in oakshott), ASCII `g` for `ɡ` (29 rows), Latin-orthography leaks (`ai` in brainpan/brainstem = eɪ but in lobotomise = aɪ, per the Shavian column), bare `a`/`ɑ`/`ɔ` missing length or laxness marks, `əː` for `ɜː` (goulburn — not in issue #7's list; found by the residue check), misplaced marks (nauvoo `nɔˈː`), and the `.`/`'`/U+0329 strays. Every rule names its affected words and was cross-checked against the row's Shavian column; the validator fails if any rule stops matching, so the file doubles as a to-do list for upstream fixes.

## Reconciling issue #1's counts

- ʊə "1,229 total": 760 standalone `ʊə` tokens + 321 inside `aʊə` + 148 regex matches spanning the `əʊ`+`ə` boundary (goer, follower) = 1,229. The issue's figure was a raw substring count.
- aɪəR 515 / aʊəR 226: capital-R-only rows. Token-level pre-r counts are 655/270 because intervocalic lowercase r (firing, dowry) conditions the same absorption.
- EAR "always ɪəR, never ɪR": confirmed — the validator forbids schwa-less `ɪR`/`aɪR`/`aʊR`.
- GOAT conservation: all 10,506 `əʊ` in the normalized text tokenize as ·Owe — none is lost to a neighboring triphthong token.

## Acceptance (issue #1)

- [x] Mapping file: `data/ipa-to-qs.tsv`
- [x] Tokenizer proves total coverage — zero unmapped residue over all 110,056 IPA strings, including stress marks inside vowel+r sequences
- [x] Stress-conditioned ɪə rule implemented and audited
- [x] Weak-u decision resolved (·Ooze) and recorded above

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
