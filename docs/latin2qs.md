# The transliterator

This is the spec for [`src/qslex/latin2qs.py`](../src/qslex/latin2qs.py), the layer that consumes what the build produces: ReadLex’s `latin2shaw.py`, ported to emit Quikscript. It converts running Latin-alphabet English to Quikscript text, [issue #6](https://github.com/adiabatic/quikscript-lexicon/issues/6).

The architecture is upstream’s wholesale — spaCy tokenization and tagging, phrase matching for entries the tokenizer would split, dictionary lookup against the [converter shape](pipeline.md#the-converter-shape) with part-of-speech disambiguation for heteronyms, affix fallbacks for words the lexicon lacks — and only the lookup values and the letter-class logic change. Anything not stated below behaves as `latin2shaw.py` behaves.

Upstream reads that shape out of a file. This reads [`lexicon/quikscript-lexicon.json`](../lexicon/quikscript-lexicon.json) and rebuilds it, because the master carries every input it takes and a file of its own would only be the master’s data a second time. It costs about a third of a second at startup, once.

## Running it

The spaCy stack is heavy and optional, so it lives in an extra rather than in the package’s (empty) core dependencies:

```sh
uv sync                                       # the dev group brings in qslex[translit]
uv run python -m qslex.latin2qs < input.txt   # senior, the default
uv run python -m qslex.latin2qs --mode junior input.txt
uv run python -m qslex.latin2qs --mode x --contractions input.txt
```

`--lexicon DIR` points at a directory holding `quikscript-lexicon.json` when the repo layout is not available. Input that begins with `<!doctype html` is converted around its markup, style and script blocks; anything else is treated as plain text, line by line.

## Output modes

The three modes select among the artifact’s three spelling columns, falling back to `qs` where a sparse column is absent, exactly as the [column model](pipeline.md#the-converter-shape) intends:

| Mode               | Column      | What it is                                         |
| ------------------ | ----------- | -------------------------------------------------- |
| `senior` (default) | `qs`        | Read’s conventions plus the standard word-outlines |
| `junior`           | `qs_junior` | word-level divergences and the kept n't vowel      |
| `x`                | `qs_x`      | the ·Excite/·Exam X-letter form, built on senior   |

`--contractions` layers the [§III Senior contractions](word-signs.md#the-three-tiers) on top — the ≈50-word list `contractions.tsv` ships precisely for this consumer, applied to no column. It composes with `senior` and `x`; combined with `junior` it is an error, because the Manual’s Note on p.25 says the Senior facilities are impossible as a first stage. The layer is word-level: it substitutes a listed word, attaches clitics to a contracted stem (she's = ·She·Zoo, we'll = ·Way’·Low), and generalises `n't` to unlisted stems (shouldn't = ·She·Day·No·Tea). It never touches a proper noun or a token inside a named entity, so Will Smith keeps his name. The three `that` rows carry their C5 tags through `c5-to-penn.tsv`, so only the non-demonstrative `that` contracts — which the senior column already spells ·They·Tea anyway.

Words the affix fallback constructs take the same mode fork, because the root’s row is looked up with the same column preference. Letter names do not take it: the standalone-letter reading and the initialism test both read the `qs` column, so a standalone *x* is ·Et·Key·See in every mode and the ·Excite X-letter stays inside words.

## Letter classes, and no epenthetic vowel

Upstream’s three Shavian letter classes conditioned an epenthetic 𐑩 as well as voicing. The Manual has no epenthetic vowel — [§ Terminal -es, -ed](https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-es-ed) omits the separator between its seven pairs — so the classes reduce to two:

- **Sibilants** ·See ·Zoo ·She ·Zhivago ·Cheer ·Jay: a following possessive or plural is bare ·Zoo with nothing before it. Mr Jones's = ·May·Roe ·Jay·Owe·No·Zoo·Zoo, “with one name-dot, no apostrophe”. (·Zhivago is not among the Manual’s seven pairs, but the corpus writes garages with bare ·Zoo, so it conditions the same way — the ruling recorded in [`docs/word-signs.md`](word-signs.md).)
- **Voiceless finals** ·Pea ·Tea ·Key ·Fee ·Thaw ·See ·She ·Cheer ·Loch: a constructed -s devoices to ·See (cups, mates, racks), matching upstream’s `s_follows` exactly where the corpus was checked.
- Everything else, vowels included, takes voiced ·Zoo.

These fire only where the transliterator builds a form itself — a possessive clitic, a constructed plural — because inside the lexicon ReadLex’s IPA already wrote the voicing.

## Apostrophes

The conditioning is the one [`docs/word-signs.md`](word-signs.md#contractions-possessives-and-the-apostrophe) derived from the Manual’s own practice — not phonological, but whether the clitic’s letters could be misread as a continuation of the word:

| Class                       | Written                                      | Example                                                      |
| --------------------------- | -------------------------------------------- | ------------------------------------------------------------ |
| possessive `'s`, `s'`       | solid, apostrophe dropped, class-conditioned | Jack's = ·Jay·At·Key·See                                     |
| verbal `'s`                 | solid                                        | it's = ·It·Tea·See                                           |
| `n't`                       | solid                                        | wasn't, can't                                                |
| `'d` `'ll` `'m` `'re` `'ve` | apostrophe kept                              | they'll = ·They·Eight’·Low                                   |
| aphetic `'t...`             | leading apostrophe kept                      | 'twas = ’·Tea·Way·Utter·Zoo, ’·Tea·Way·Ox·Zoo in junior mode |

The corpus’s spellings carry no apostrophes at all, so for the keeping classes the transliterator reinserts one: a dictionary spelling that ends in the clitic’s own letters gets ’ placed before them. That reproduces the Manual’s ·They·Eight’·Low from the artifact’s ·They·Eight·Low, in every mode — the Bo-peep specimen keeping the apostrophe is Junior text.

## The namer dot

U+00B7, per [quikscript.net/namer-dot-usage](https://www.quikscript.net/namer-dot-usage/) and the Manual’s “Three name-dots suffice”: one dot at the head of a name, the run after it riding undotted. The entity logic ports from upstream directly — spaCy’s named entities of the naming kinds get a dot on their first token, a PERSON entity is expanded to include a preceding title, and a leading “the” is left outside the entity — which reproduces the Manual’s specimen exactly: At ·Rome, ·Jack met ·Mr Harold Jones.

Two rules are new here, because Shavian marks these sites differently or not at all:

- **A standalone letter is dotted.** “To refer to a letter in Quickscript, it is written with a name-dot” ([§ Punctuation etc.](https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#punctuation-etc)). A single-letter token takes the dot and the letter-name reading — the SYM row where the converter has one — except the pronoun I, the article a, and the vocative O, which are words.
- **An initialism is dotted, once.** The Manual and quikscript.net are silent on BBC-style initialisms, and Shavian’s ⸰ marker has no Quikscript analogue to port, so this is the decided treatment: a token in capitals whose spelling is exactly a run of letter-names is a name read for sound, and takes one namer dot like any other name. Detection is by decomposition against the single letters’ own spellings, so shouted ordinary words are never dotted, and a pronounced acronym like NASA is dotted only when it is an entity.

## Punctuation

- **Brackets are angled**: `(` → U+E66E, `)` → U+E66F, the two non-letter codepoints the Manual itself uses ([§ Punctuation etc.](https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#punctuation-etc)); square brackets pass through.
- **Quotes are single**: smartypants educates the dumb quotes, and the doubles it produces are then demoted to singles, because the Manual’s Quikscript text quotes with ‘…’ only. Upstream’s swap to guillemets is dropped — nothing in the Manual supports it for Quikscript.
- **etc.** → ·No·No·No arrives through the dictionary; ReadLex writes it `NNN` already.
- **Underlining numerals and foreign words** is prescribed but never exercised in the Manual, and plain text has no underline, so it is declined — recorded here rather than left as an omission.
- **Ordinals** keep upstream’s treatment — digits kept, suffix spelt: 21st = 21·See·Tea, 2nd = 2·No·Day, 3rd = 3·Roe·Day, 4th = 4·Thaw, 1960s = 1960·Zoo. The Manual has no digit inside Quikscript text anywhere, so there was no convention to follow.

## The affix fallback

Upstream constructs words the dictionary lacks from ≈40 affixes and marks them ⚠️ for proofreading; the unmatched are marked ✢. Both markers are kept — they are script-agnostic. The tables were re-expressed from the Manual’s own affix conventions and this lexicon’s data, never transliterated from the Shavian strings, and the test suite holds every affix to the spelling the lexicon uses inside real words. Three are worth calling out:

- **-ness and -less take ·Et**, the Manual’s explicit distinction from the -us, -ous terminal — the one affix a naive transliteration of upstream’s 𐑯𐑩𐑕/𐑤𐑩𐑕 would get wrong.
- **-ful splits on the part of speech**: mouthful the noun keeps ·Foot, careful the adjective reduces to ·Utter, per [§ Terminal -ful](https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-ful).
- **The productive de-, pre-, pro-, re- take the full stressed vowel** (·Day·Eat, ·Pea·Roe·Eat, ·Pea·Roe·Owe, ·Roe·Eat). The prefix rules’ reduced vowels describe lexicalised Latinate stems, which are dictionary hits and never reach the fallback; a new coining says the vowel in full, and the corpus’s own de-escalate, reissue, prejudge and proconsul all agree.

## Ambiguity the tags cannot settle

Where the converter row is a `⬌`-joined pair, the transliterator emits it verbatim, exactly as `latin2shaw.py` emits its own joined rows — the artifact [punts on this disambiguation](pipeline.md#the-converter-shape) and the consumer keeps the punt visible rather than picking silently. One consequence of the [row policy](pipeline.md#row-policy-the-rrp-family-only) is that again and against, whose second RRP pronunciations upstream drops, are always joined here; a proofreader resolves ⬌ the same way they resolve ⚠️.

## Deliberate departures from upstream

Everything else is a straight port. These are the places the port does not reproduce `latin2shaw.py`’s behaviour, each on purpose:

1. **Constructed words read the `0` row, not the first row.** Upstream takes `rows[0]` for affix and plural fallbacks, which was harmless when `NN` came first; this artifact [writes `NNP` first](pipeline.md#the-converter-shape), so the universal fallback row is addressed by its tag.
2. **`esque` moved to the suffixes.** Upstream files it under prefixes, where `startswith` can never match an English word.
3. **One affix construction per token.** Upstream’s loop keeps matching after a hit and can emit a word twice; here the first successful construction returns.
4. **A verb before “to” that fails both special cases falls through to normal conversion.** Upstream emits nothing — “she has to her credit” loses the has.
5. **`WDT` falls back to the `IN` row.** Relative that is C5’s `CJT`, the conjunction, spelt ·They·Tea — but spaCy tags it `WDT`, a tag no converter row carries.
6. **Long lines are converted, not dropped.** Upstream silently skips any line of 10,000 characters or more.
7. **No guillemets, no epenthetic vowel, no ⸰** — replaced above by the Manual’s quotes, the Manual’s -es/-ed rule, and the namer-dot treatment of initialisms.
8. **`all` is spelt from the dictionary, not the contraction table.** Upstream lists *all* among the contraction halves, which sit above the dictionary lookup, so every *all* in every text is spelt from the table. Two things follow: *do all*, *does all* and *did all* come out solid and on the *don't*, *doesn't* and *didn't* stems’ ·Day·Owe, ·Day·Utter·Zoo and ·Day·It·Day, because the opening half reads the verb as a contraction’s front and withholds the space a clitic would not want; and *All Souls Day* loses its namer dot, which only the dictionary path applies. The row is dropped here and *all* goes through the dictionary like any other word, so the dot is back wherever spaCy’s entity recogniser marks the name — on the bare phrase, with no sentence around it, it does not fire. `y'all` was the only word whose halves that row joined, and the `y'` half goes with it: lowercase *y'all*, the form the tokenizer splits, comes out as a bare Latin `y'` — unmarked, because a token carrying an apostrophe is not alphabetic and takes no ✢ — followed by the dictionary’s ·Awe·Low, while *Y'all* stays one token and passes through whole.
9. **Plain-text output is unescaped, not parsed as HTML.** The last step of the plain-text path has to turn smartypants’ numeric entities back into characters. Upstream does it by round-tripping the finished text through BeautifulSoup, which re-escapes it on the way out: `1 < 2` comes back `1 &lt; 2`, `AT&T` comes back `AT&amp;T`, and anything the parser can still read as a tag is rewritten — a line containing `<xyzzy>` gains a `</xyzzy✢>` the input never had. `html.unescape` does the decoding here instead, so the markup characters survive as themselves. The cost is the other direction, and it is wider than an `&amp;` written for a visible ampersand decoding back to one: `html.unescape` matches the semicolon-less legacy entity names by longest prefix, so an ampersand that runs straight into one of them is rewritten mid-token, in text BeautifulSoup preserved — `AT&notice` comes back AT¬ice, `M&copy` comes back M©. What that exposes is the ampersand-joined names the converter passes through verbatim, rarer text than the markup characters, and the rewrite substitutes where the round trip mangled.

## Verification

`tests/test_latin2qs.py` holds the port to the acceptance criteria:

- **Heteronyms**: read/read on tense, lead and live on part of speech, use noun against verb, that demonstrative against conjunction against relative — and the `⬌` punt is pinned where no tag can settle against.
- **Clitic conditioning**: devoiced, sibilant-bare and voiced possessives, dropped and kept apostrophes, solid n't, the constructed plural’s voicing, and the contraction layer’s stems, clitics and refusals.
- **The Manual’s specimen passages replay**, all 674 words: Senior passages in `x` mode with the contraction layer, Junior ones in `junior` mode, each word against its fixture verdict — `differs` rows accept either the Manual’s spelling or the pinned `ours`, and four rows are pinned in `REPLAY_PINS` for reasons the layers own (a leading apostrophe the fixture format cannot record, a phrase match hiding little from the word-level contraction layer, Read contracting whatever beyond his own list, and the RRPVar join on against).
- **Match-rate parity with `latin2shaw.py`**: run over *Alice’s Adventures in Wonderland* (27,336 word tokens), both converters miss exactly the same 49 tokens — Roman numerals and Carroll’s nonce words — and construct the same 2. The parity run is an exercise, not a committed test, because it needs upstream’s converter artifacts. The recipe: take readlex’s `latin2shaw.py` with its `static/` converter JSONs beside a boilerplate-stripped Gutenberg *Alice*, run it and `qslex.latin2qs` over the same text, and compare the tokens each marks ✢ and ⚠️.
