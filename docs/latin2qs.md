# The transliterator

This is the spec for [`src/qslex/latin2qs.py`](../src/qslex/latin2qs.py), which converts running Latin-alphabet English to Quikscript text ([issue #6](https://github.com/adiabatic/quikscript-lexicon/issues/6)). It is a port of ReadLex’s `latin2shaw.py` that writes Quikscript instead of Shavian, and it uses the lexicon that the build produces.

The architecture is upstream’s:

- spaCy tokenizes and tags the text.
- A phrase matcher merges entries that the tokenizer would otherwise split.
- Each word is looked up in the [converter table](pipeline.md#the-converter-shape), and the part-of-speech tag chooses between the spellings of a heteronym.
- Affix fallbacks construct words that the lexicon lacks.

Only the lookup values and the letter-class logic are new. Anything not described below works as it does in `latin2shaw.py`.

Upstream reads the converter table from a file. This module reads [`lexicon/quikscript-lexicon.json`](../lexicon/quikscript-lexicon.json) and rebuilds the table from it at startup. The lexicon JSON contains everything the table is built from, so a separate file would only repeat its data. The rebuild adds a fraction of a second to startup.

## Running it

spaCy and its dependencies are large, so they are an optional extra (`qslex[translit]`). The package’s core dependencies are empty.

```sh
uv sync                                       # the dev group brings in qslex[translit]
uv run python -m qslex.latin2qs < input.txt   # senior: X-letters and the §III contractions
uv run python -m qslex.latin2qs --junior input.txt
uv run python -m qslex.latin2qs --no-contractions input.txt
uv run python -m qslex.latin2qs --junior --x-letters input.txt
```

`--lexicon DIR` names a directory that contains `quikscript-lexicon.json`, for use outside the repository layout.

Input that begins with `<!doctype html` is treated as HTML: markup, style blocks and script blocks are copied unchanged and the text between them is converted. Any other input is treated as plain text and converted line by line.

## The grade, and the two facilities it defaults

The output is controlled by a grade and two independent switches:

- The grade is `--senior` (the default) or `--junior`.
- The switches are `--x-letters` / `--no-x-letters` and `--contractions` / `--no-contractions`.

A switch that is not given takes its value from the grade:

| Given      | `qs_junior` | `qs_x` | §III contractions |
| ---------- | ----------- | ------ | ----------------- |
| nothing    | —           | ✓      | ✓                 |
| `--senior` | —           | ✓      | ✓                 |
| `--junior` | ✓           | —      | —                 |

Senior is how a fluent writer writes, so by default it uses the X-letters and the contractions. Junior is the first stage, so by default it uses neither.

The grade sets defaults and does not forbid either facility. The Manual’s Note on p.25 says that the Sections II and III facilities “are of course impossible as a first stage in children’s writing”. That is advice about teaching children, and it does not limit what a converter may write. So `--junior --x-letters` and `--junior --contractions` are both accepted. The only combination the CLI rejects is `--senior --junior`, which argparse rejects because the two flags are mutually exclusive.

Each of the two sparse columns falls back to `qs` where it is empty, as the [column model](pipeline.md#the-converter-shape) specifies:

- `qs_x` is used when the X-letters are on.
- `qs_junior` is used when the grade is Junior.

`--junior --x-letters` therefore uses both columns. No converter row has both columns, so no row needs a rule for choosing between them. An X-letter needs an x in the word, and none of the Junior differences has one.

The §III contraction layer uses the word list in `contractions.tsv`. The build does not write that list into any spelling column. The layer works on whole words:

- It replaces a listed word with its contraction.
- It attaches clitics to a contracted stem: she's = ·She·Zoo, we'll = ·Way’·Low.
- It applies `n't` to a listed stem whose `n't` form is not itself listed: shouldn't = ·She·Day·No·Tea.

It never contracts a proper noun or a token inside a named entity of a kind that takes a namer dot, so Will Smith keeps his name.

The three `that` rows in `contractions.tsv` have C5 tags, which `c5-to-penn.tsv` maps to Penn tags. So only the non-demonstrative `that` contracts, and the senior column already spells that one ·They·Tea.

One row is accepted but never written. done = ·Day·No comes from a specimen passage rather than a rule: the No-how passage spells done out in full and then writes ·Day·No at its second occurrence. The checker accepts ·Day·No, but this layer leaves done as ·Day·Utter·No.

Words that the affix fallback constructs use the same column choice, because the root’s row is looked up with the same column preference.

Letter names do not. The standalone-letter reading and the initialism test both read the `qs` column. So a standalone *x* is always ·Et·Key·See, and the ·Excite X-letter appears only inside words.

## Letter classes, and no epenthetic vowel

Upstream has three Shavian letter classes. They decide whether a suffix is voiced and whether an epenthetic 𐑩 is inserted before it. The Manual has no epenthetic vowel: [§ Terminal -es, -ed](https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-es-ed) omits the separating vowel between its seven pairs. So this port uses two classes:

- **Sibilants** ·See ·Zoo ·She ·J’ai ·Cheer ·Jay: a following possessive or plural is a bare ·Zoo with nothing before it. Mr Jones's = ·May·Roe ·Jay·Owe·No·Zoo·Zoo, “with one name-dot, no apostrophe”.
  - ·J’ai is not in the Manual’s seven pairs. The corpus writes garages with a bare ·Zoo after ·J’ai, so it is treated as a sibilant too.
- **Voiceless finals** ·Pea ·Tea ·Key ·Fee ·Thaw ·See ·She ·Cheer ·Loch: a constructed -s devoices to ·See (cups, mates, racks). This matches upstream’s `s_follows` wherever the corpus was checked.
- Everything else, vowels included, takes a voiced ·Zoo.

The classes apply only where the transliterator builds a form itself, such as a possessive clitic or a constructed plural. Inside the lexicon, ReadLex’s IPA already gives the voicing.

## Apostrophes

The transliterator follows the rule that [`docs/word-signs.md`](word-signs.md#contractions-possessives-and-the-apostrophe) derives from the Manual’s own practice. The rule is not phonological. The apostrophe is kept where the clitic’s letters could be misread as a continuation of the word.

| Class                       | Written                                      | Example                                                      |
| --------------------------- | -------------------------------------------- | ------------------------------------------------------------ |
| possessive `'s`, `s'`       | solid, apostrophe dropped, class-conditioned | Jack's = ·Jay·At·Key·See                                     |
| verbal `'s`                 | solid                                        | it's = ·It·Tea·See                                           |
| `n't`                       | solid                                        | wasn't, can't                                                |
| `'d` `'ll` `'m` `'re` `'ve` | apostrophe kept                              | they'll = ·They·Eight’·Low                                   |
| aphetic `'t...`             | leading apostrophe kept                      | 'twas = ’·Tea·Way·Utter·Zoo, ’·Tea·Way·Ox·Zoo in junior      |

The corpus’s spellings have no apostrophes. For the classes that keep one, the transliterator reinserts it: when a dictionary spelling ends in the clitic’s own letters, ’ is placed before those letters. This turns the lexicon’s ·They·Eight·Low into the Manual’s ·They·Eight’·Low. It does this at both grades. The Bo-peep specimen, which keeps the apostrophe, is Junior text.

## The namer dot

The namer dot is U+00B7, per [quikscript.net/namer-dot-usage](https://www.quikscript.net/namer-dot-usage/) and the Manual’s “Three name-dots suffice”. A name gets one dot before its first word and none on the words after it.

The entity logic is ported from upstream:

- spaCy’s named entities of the kinds that name things get a dot on their first token.
- A PERSON entity is extended to include a title before it.
- A leading “the” is left outside the entity.

This reproduces the Manual’s specimen: At ·Rome, ·Jack met ·Mr Harold Jones.

Two rules are new, because Shavian marks these cases differently or not at all:

- **A standalone letter is dotted.** “To refer to a letter in Quickscript, it is written with a name-dot” ([§ Punctuation etc.](https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#punctuation-etc)). A single-letter token gets the dot and is spelled as the letter’s name, from the SYM row where the converter has one. The pronoun I, the article a and the vocative O are words and are not dotted.
- **An initialism gets one dot.** The Manual and quikscript.net say nothing about initialisms like BBC, and Shavian’s ⸰ marker has no Quikscript equivalent. This project’s decision is to treat an initialism as a name: a token in capitals whose spelling is a run of letter names gets one namer dot. The test splits the token into single letters and compares the letters’ spellings with the token’s spelling. So a word in capitals that is not an initialism is not dotted, and an acronym pronounced as a word, like NASA, is dotted only when spaCy marks it as an entity.

## Punctuation

- **Brackets are angled.** `(` becomes U+E66E and `)` becomes U+E66F, the two non-letter codepoints the Manual itself uses ([§ Punctuation etc.](https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#punctuation-etc)). Square brackets are copied unchanged.
- **Quotes are single.** smartypants educates the dumb quotes, and the transliterator then changes the resulting double quotes to single ones, because the Manual’s Quikscript text uses only ‘…’. Upstream converts quotes to guillemets. This port does not, because nothing in the Manual uses them for Quikscript.
- **etc.** becomes ·No·No·No through the dictionary, because ReadLex already writes it `NNN`.
- **Underlining numerals and foreign words** is not implemented. The Manual prescribes it but never shows it, and plain text has no underline.
- **Ordinals** are handled as upstream handles them: the digits are kept and the suffix is spelled. 21st = 21·See·Tea, 2nd = 2·No·Day, 3rd = 3·Roe·Day, 4th = 4·Thaw, 1960s = 1960·Zoo. The Manual never puts a digit inside Quikscript text, so there was no convention to follow.

## The affix fallback

Upstream constructs words the dictionary lacks from about 40 affixes and marks them ⚠️ for proofreading. Words it cannot match or construct are marked ✢. This port keeps both markers, because they do not depend on the script.

The affix spellings were written from the Manual’s affix conventions and this lexicon’s data, not transliterated from upstream’s Shavian strings. `tests/test_latin2qs.py` checks most of the suffixes and some of the prefixes against the spellings the lexicon uses inside real words (antifreeze, childhood, goodness, and others). Three affixes differ from a direct transliteration:

- **-ness and -less take ·Et.** The Manual distinguishes them from the -us, -ous terminal. A direct transliteration of upstream’s 𐑯𐑩𐑕/𐑤𐑩𐑕 would get these wrong.
- **-ful depends on the part of speech.** mouthful, a noun, keeps ·Foot, and careful, an adjective, reduces to ·Utter, per [§ Terminal -ful](https://adiabatic.github.io/abbots-morton-spaceport/the-manual.html#terminal-ful).
- **The productive de-, pre-, pro- and re- take the full stressed vowel** (·Day·Eat, ·Pea·Roe·Eat, ·Pea·Roe·Owe, ·Roe·Eat). The prefix rules’ reduced vowels describe lexicalized Latinate stems. Those words are in the dictionary and never reach the fallback. A new coinage says the vowel in full, and the corpus’s de-escalate, reissue, prejudge and proconsul agree.

## Ambiguity the tags cannot settle

Where a converter row is a `⬌`-joined pair, the transliterator writes it out as is, as `latin2shaw.py` does with its own joined rows. The artifact [does not choose between the alternatives](pipeline.md#the-converter-shape), and the transliterator does not pick one either. A proofreader resolves ⬌ in the same way as ⚠️.

Because of the [row policy](pipeline.md#row-policy-the-rrp-family-only), again and against are always joined here. Upstream drops their second RRP pronunciations.

## Differences from upstream

Apart from the points above, the code is a direct port. It differs from `latin2shaw.py` in these places:

1. **Constructed words use the `0` row, not the first row.** Upstream takes `rows[0]` for affix and plural fallbacks. That worked when `NN` came first, but this artifact [writes `NNP` first](pipeline.md#the-converter-shape). The fallbacks here read the last row, which the converter always writes as the `0` row.
2. **`esque` is a suffix.** Upstream lists it under prefixes, where `startswith` can never match an English word.
3. **At most one affix construction per token.** Upstream’s loop keeps matching after a hit and can write a word twice. Here the first successful construction is returned.
4. **A verb before “to” that fails both special cases is converted normally.** Upstream writes nothing, so “she has to her credit” loses the has.
5. **`WDT` falls back to the `IN` row.** Relative that is C5’s `CJT`, the conjunction, spelled ·They·Tea. spaCy tags it `WDT`, and no converter row has that tag.
6. **Long lines are converted.** Upstream silently skips any line of 10,000 characters or more.
7. **No guillemets, no epenthetic vowel, no ⸰.** These are replaced by the Manual’s quotes, the Manual’s -es/-ed rule and the namer-dot treatment of initialisms, all described above.
8. **`all` is spelled from the dictionary, not the contraction table.** Upstream lists *all* among the contraction halves. Those are checked before the dictionary lookup, so upstream spells every *all* from that table. This has two effects in upstream:
   - *do all*, *does all* and *did all* are written solid, with the verb spelled as the stem of *don't*, *doesn't* or *didn't* (·Day·Owe, ·Day·Utter·Zoo, ·Day·It·Day). The opening half treats the verb as the front of a contraction and leaves out the space.
   - *All Souls Day* loses its namer dot, which only the dictionary path adds.

   This port drops that row, and *all* is looked up in the dictionary like any other word. The dot is written wherever spaCy’s entity recognizer marks the name. It does not mark the bare phrase with no sentence around it.

   `y'all` was the only word whose halves that row joined, so the `y'` half is dropped too. Lowercase *y'all* is split by the tokenizer. It comes out as a Latin `y’` with no marker, followed by the dictionary’s ·Awe·Low. The `y’` gets no ✢ because a token with an apostrophe is not alphabetic. Capitalized *Y'all* stays one token and is copied through as Latin, with its apostrophe curled.
9. **Plain-text output is unescaped, not parsed as HTML.** The last step of the plain-text path has to turn smartypants’ numeric entities back into characters.
   - Upstream does this by passing the finished text through BeautifulSoup, which escapes it again on output. `1 < 2` comes back as `1 &lt; 2`, and `AT&T` comes back as `AT&amp;T`. Anything the parser can read as a tag is rewritten: a line containing `<xyzzy>` gains a `</xyzzy✢>` that the input never had.
   - This port uses `html.unescape` instead, so markup characters come through unchanged.
   - The downside is that some text is decoded that should not be. An `&amp;` written for a visible ampersand is decoded to `&`. Also, `html.unescape` matches the legacy entity names that need no semicolon by longest prefix, so an ampersand followed directly by one of those names is rewritten, even inside a word: `AT&notice` comes back as AT¬ice, and `M&copy` as M©. BeautifulSoup kept these unchanged. The affected text is names joined by an ampersand that the converter passes through, which is rarer than markup characters. When the error happens, it replaces a few characters. BeautifulSoup’s errors added escapes and tags.

## Verification

`tests/test_latin2qs.py` tests the port against the acceptance criteria:

- **Heteronyms**: read/read by tense; lead and live by part of speech; use as noun or verb; that as demonstrative, conjunction or relative. It also tests that against, which no tag can decide, is written as its ⬌-joined alternatives.
- **Clitics**: devoiced, sibilant and voiced possessives; dropped and kept apostrophes; solid n't; the voicing of a constructed plural; and the contraction layer’s stems, clitics, and the cases where it does not contract.
- **The Manual’s specimen passages**, all 674 words. The test runs the transliterator over each passage’s Latin and compares the output with the Manual’s spelling. Senior passages use the defaults (X-letters and contractions on) and Junior passages use `--junior`.
  - Each word is compared according to its `outcome` column in `manual-passages.tsv`. `absent` rows are skipped. A `differs` row accepts either the Manual’s spelling or the row’s `ours` spelling. Every other row must match the Manual’s spelling.
  - `PASSAGE_EXPECTED_OUTPUTS` gives the expected output for five words that the transliterator cannot write as the Manual does:
    - 'twas: `manual-passages.tsv` cannot record the leading apostrophe.
    - little: the phrase “a little” matches first, so the word-level contraction layer never sees little.
    - whatever: the passage writes the what-sign followed by ever, a contraction that is not on Read’s own list.
    - done: the checker accepts the contraction, but the transliterator does not write it.
    - against: the row policy keeps both RRPVar pronunciations, so the output joins them with ⬌.
- **Match rate compared with `latin2shaw.py`**: on *Alice’s Adventures in Wonderland* (27,336 word tokens), both converters fail to match the same 49 tokens (Roman numerals and Carroll’s nonce words) and construct the same 2. This comparison is not a committed test, because it needs upstream’s converter artifacts. To repeat it, put ReadLex’s `latin2shaw.py` and its `static/` converter JSON files next to a Gutenberg *Alice* with the boilerplate removed. Run it and `qslex.latin2qs` over the same text, and compare the tokens each one marks ✢ and ⚠️.
