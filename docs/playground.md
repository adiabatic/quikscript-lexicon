# The playground

[`site/index.html`](../site/index.html) is the lexicon with a user interface on it: type Markdown on the left, read it set in Quikscript on the right, and every Quikscript word the grade you are writing in does not accept gets a dotted red underline you can click for suggestions that edit the source back — or for an Ignore that leaves the word alone from then on. A Junior/Senior checkbox switches grade. A button copies the source out.

It is one file of 2,502,236 bytes with nothing outside it — five font faces, a Markdown parser and all 75,636 spellings are inlined — so it opens from a `file:` URL, with no font installed, no build step, no server and no request to anywhere. That is the whole point of the shape: a spelling dictionary nobody can install is a spelling dictionary nobody uses, and hunspell is not a thing most people have.

This is the spec for [`src/qslex/playground.py`](../src/qslex/playground.py), which builds the page, and for the four template files in [`src/qslex/web/`](../src/qslex/web) it builds it out of.

## Projected, not written

The page is generated from [`lexicon/quikscript-lexicon.json`](../lexicon/quikscript-lexicon.json) — the same master [`docs/pipeline.md`](pipeline.md) projects `lexicon/` from — and committed beside it, exactly like the artifacts are. **Nothing in `site/` is hand-edited.** `make check` rebuilds the page in memory and fails if what is on disk differs, so a page that disagrees with the lexicon is a freshness failure rather than a discovery someone makes months later with a word list that no longer matches the `.dic` shipped next to it.

The builder reads the master, four template files, and the vendored assets, and substitutes each into a placeholder token by plain `str.replace`:

| Inlined | From | Bytes |
|---|---|---|
| the word set and its frequencies | `lexicon/quikscript-lexicon.json`, `src/qslex/data/contractions.tsv` | 1,928,336 |
| five `.woff2` faces, base64 in their `@font-face` rules | `data/abbots-morton-spaceport/` | 370,007 |
| marked 18.0.7, verbatim, in a `<script>` of its own | `data/marked/marked.umd.js` | 42,757 |
| the page's own markup, CSS and JavaScript | `src/qslex/web/` | 18,081 |

Three rules keep that honest. Every vendored file's SHA-256 is pinned in the module and verified before it is inlined, so a font or a parser that had drifted cannot be baked into a generated file and shipped without a diff anyone can read — [the font README](../data/abbots-morton-spaceport/README.md) and [the marked README](../data/marked/README.md) carry the same digests and the provenance for both. Every substituted chunk is refused if it contains `</script` in any case, because such a chunk would end its own element wherever the browser's tokenizer found the string and the page would truncate in silence rather than fail to build. And any `__QS_…__` placeholder left unfilled is an error, so a template that grows a token the builder does not know about fails loudly.

The word list is serialized as one string of one spelling to a line, with a tab and a frequency after it where there is one, rather than as a JSON object, and that is worth a sentence because it is three-quarters of the file. 75,636 short keys quoted and comma-separated is several hundred kilobytes of punctuation in a file that is fetched whole; a tab-separated block costs one `split` at startup and nothing else. The frequency is omitted where it is zero, which is most of the list.

## The invariants the build asserts

Three of them, all re-derived from the master rather than read out of the files they are compared against, so that the page and the dictionary cannot disagree quietly:

- **The dictionary's word set is the dictionary's.** The 75,568 spellings `spellings()` gives over all three columns — the same derivation [`en-Qaas.dic`](../lexicon/en-Qaas.dic) is, down to the dropped spaced entries — compared against the `.dic`'s own first-line count and word list, in order. A mismatch means one of the two artifacts is stale, not that the page wants a wider set. The page then accepts those **plus** the §III Senior contractions, which is a widening the `.dic` deliberately has no way to express; the section after next is about that.
- **The letter order is the affix file's `TRY`.** `by_frequency()` over the dictionary's word set — not over the wider one the page carries — compared against the single `TRY` line in [`en-Qaas.aff`](../lexicon/en-Qaas.aff). The suggester walks hunspell's alphabet rather than one recounted for the page, deliberately: 68 further spellings do not move 44 letter counts far enough to be worth two orders that then have to be kept from drifting apart.
- **The two grades cover every spelling between them.** `senior | junior == union`, which is what makes "the active set is the union minus the other grade's own" a legal way to switch grades at runtime.

The replacement table is the `.aff`'s `REP`, derived from the same `LIGATURES` constant: ·Excite bridged to ·Key·See and ·Exam to ·Gay·Zoo, in both directions, four directed pairs. It earns its place here for the reason [it earns it there](pipeline.md#en-qaasdic--en-qaasaff) — the letters around a ligature change with it, so neither form of a word is a single-letter edit from the other and no edit-distance suggester alone will turn the other up.

## The two grades

`qs` is Senior and `qs_junior` is Junior where it says anything at all, which is [8 rows over 5 words](word-signs.md#tier-3-the-standard-word-outlines). The ligature column `qs_x` belongs to **both**, because it is a way of writing a spelling rather than a grade of its own. So:

- **senior** = every `qs` + every `qs_x` + [every §III contraction](#the-iii-senior-contractions) — 75,632 spellings
- **junior** = every `qs_junior` where there is one, else `qs`, + every `qs_x` — 75,563
- **senior_only** = senior − junior, 73 spellings; **junior_only** = junior − senior, 4

Five divergent rows produce five pairs but only four junior-only spellings, and the missing one is not an off-by-one. The Junior spelling of non-demonstrative that is ·They·At·Tea, and ·They·At·Tea is also the *Senior* spelling of demonstrative that — Quikscript makes a heteronym here that Shavian does not ([`qs_converter.json`](pipeline.md#qs_converterjson) has to give `CJT` and `DT0` separate Penn tags for the same reason). So the junior form of one row is already in the senior set by way of another row, and subtracting sets rather than counting rows is what gets that right. The consequence in the page is exactly the one you want: writing ·They·At·Tea is correct in both grades, and neither mode underlines it.

## The §III Senior contractions

[`src/qslex/data/contractions.tsv`](../src/qslex/data/contractions.tsv) is the Manual's §III contraction list, and it is [Tier 2](word-signs.md#the-three-tiers): an optional Senior facility, not how a word is spelt, so it **reaches no column** and nothing in `lexicon/` carries it. The page is the first thing in this repo that can hold that distinction, because it has a grade switch and a dictionary does not. So make = ·May·Key is accepted in Senior mode and underlined in Junior, and the Junior suggestion for it is the full ·May·Eight·Key.

They are loaded through `qslex.words.load_contractions()`, the same loader the transliterator uses, and 77 of the 79 rows are taken. **The two `clitic` rows stay out**: `n't` attaches solid, so it is never written as a token of its own and the checker can never see one, and a bare `'ll` after an apostrophe is flagged here for exactly the reason the dictionary flags it — [the apostrophe is deliberately outside `WORDCHARS`](pipeline.md#en-qaasdic--en-qaasaff), a run breaks at U+2019, the host word is blessed and the clitic half is not. That ruling and its cost are pipeline.md's; the page mirrors it rather than reopening it.

The 77 rows write **74 distinct spellings**, and **six of the 74 are already in the `.dic`**, so the page's word set grows by 68 rather than 74. The `be` row's own note in the TSV predicts one of the six and is right: ·Bay is the §III contraction for be *and* [one of the core eight](word-signs.md#tier-1-the-core-eight), which is a Junior-sanctioned word sign the senior column has carried all along. The other five are worth naming because only two of them are that kind of agreement:

| Contraction | Also in the `.dic` as |
|---|---|
| be = ·Bay | the core-eight word sign for be, in both columns |
| that = ·They·Tea | the [Common words](word-signs.md#tier-3-the-standard-word-outlines) outline for conjunctive that, in the senior column |
| cannot = ·Key·At·No·Ox·Tea | cannot, spelt by the ordinary rules exactly as the list spells it |
| do = ·Day | the ordinal suffixes nd and rd, an unrelated word that happens to be one letter |
| think = ·Thaw | the ordinal suffix th, likewise |
| she = ·She | the interjection sh, likewise |

Set arithmetic gets all six right where counting rows would not, which is the same lesson the junior `that` teaches one section up. Only one of the six changes the grade split: ·They·Tea was already `senior_only`, so `senior_only` is 5 + 69 − 1 = **73**, not 5 + 74.

Three more things follow from a contraction being on the page:

- **It pairs with the full spelling Junior writes.** For each row the builder finds the lexicon rows for its `word` — matched on `(Latn, pos)` where the row carries a part-of-speech tag, on `Latn` alone where it does not — and adds `[contraction, junior form]` to the same `pairs` table the divergent rows use. That is what puts ·May·Eight·Key first when Junior mode flags ·May·Key. A row whose word matches **no** lexicon row fails the build rather than being skipped, because a contraction the page could offer no full form for is a dead end the user would have to guess their way out of; today none do. Two rows pair with nothing at all — be and cannot, whose contraction *is* the full spelling — because a pair is a move from one grade's spelling to the other's and there is no move there. So 5 pairs become **77**.
- **It takes the frequency of the word it contracts**, the highest over the rows it matched, so edit-distance ranking treats ·May·Key as being as common as make instead of sorting it last at zero. Where a contraction collides with an unrelated entry the entry inherits that count too: ·Day is as common in the suggestion ranking as do, not as common as the ordinal nd. That is the intended reading of `freq_of` — the highest count of anything that writes this spelling — and it is right for a spelling that is now two words at once.
- **It is Senior writing only.** The contractions join `senior` and nothing else, so `senior_only` is what keeps them out of Junior mode, and the Junior set is still exactly the union minus that list. Nothing about the Junior grade moved.

## What the toggle switches

Three things, and they move together because they are read from one checkbox:

1. **The face.** The preview and the popover get a `senior` class, which swaps Abbots Morton Spaceport Sans Junior for Sans Senior — unligated letters for joined ones. The textarea stays Mono in both grades: it is the source, not the reading copy.
2. **The accepted set.** Junior checks against union − senior_only, Senior against union − junior_only. Both Sets are built once at startup from the one word list.
3. **The direction of the cross-grade suggestion.** In Junior mode a senior-only spelling is offered its junior counterpart; in Senior mode a junior-only spelling is offered its senior one. The pairs table carries both halves, so one table serves both directions — though in practice the Senior direction is served by the five divergent rows alone, a contraction never being junior-only.

A grade change re-renders and dismisses any open popover. Nothing else in the page knows about grades.

## Checking, and where it departs from hunspell

A token is a run matching `/[\uE650-\uE67E][\uE650-\uE67E-]*/g` — a Quikscript letter followed by any number of Quikscript letters and hyphens. A token passes if it is in the active set; failing that, if it contains a hyphen, it passes when every non-empty piece is in the active set. Nothing is case-folded, because Quikscript has no case, and there is no affix machinery to consult, because [the `.aff` declares none](pipeline.md#en-qaasdic--en-qaasaff).

That is deliberately hunspell's behaviour under this dictionary, and it inherits hunspell's own recorded weakness with it: default `BREAK` accepts any hyphenated join of two entries whether or not the join is a word, and with 20 single-letter entries in the `.dic` that reaches down to ·Zoo-·Vie. An edge hyphen leaves an empty piece, which is nothing to look up and passes — so the 43 prefix-style entries like pre- are accepted for the same reason here as there. Middle dots, namer dots and U+2019 all fall outside the token, so a run breaks at each of them; that too is hunspell under this `.aff`, where the apostrophe is [deliberately kept out of `WORDCHARS`](pipeline.md#en-qaasdic--en-qaasaff) and a transliterated clitic gets its host word blessed and its own half flagged.

Six places the page does **not** behave as `hunspell -i utf-8 -d lexicon/en-Qaas` would, all of them chosen:

- **A run of bare hyphens is never a token, so it is never flagged.** hunspell's `WORDCHARS` carries the hyphen, which makes a spaced `--`, a `---` rule or the `- ` opening a bullet a token of its own that no entry matches; pipeline.md records that as the cost of the hyphen and declines to pay it back. Here the token pattern requires a leading Quikscript letter, so those never reach the checker at all. The input to this page is Markdown, where every one of those strings is syntax rather than a word.
- **`pre` and `code` are skipped**, along with anything inside the popover. hunspell has no notion of markup and would check a fenced block like prose; the page checks *rendered* HTML, where a code span is quoted text and flagging it would be flagging the author's example.
- **One grade at a time.** The `.dic` is the union of all three columns, so hunspell accepts Senior, Junior and ligature spellings all at once and cannot be asked to do otherwise; a dictionary has nowhere to put a grade. The page can, and does.
- **Senior mode accepts 68 spellings the `.dic` does not carry at all**, the [§III contractions](#the-iii-senior-contractions). hunspell flags every one of them, correctly, because they are not spellings — they are a Senior writing facility, and the only reason the page can accept them is that it knows which grade you are writing in.
- **The suggestions are the page's own.** hunspell's ngram and phonetic suggesters are not reimplemented — see below for what is.
- **No HTML sanitizer.** `marked.parse()` output goes straight into `innerHTML`, with marked's defaults, which pass raw HTML through. The page is local, single-user, and its only input is what its own user typed into it, so the thing a sanitizer defends against is the user attacking themselves; vendoring and pinning a second library to prevent that is not a trade worth making. The ruling has a cost and here it is: **do not serve this page anywhere that puts someone else's Markdown into that textarea.** If that is ever wanted, a sanitizer is vendored under `data/` with a digest, like everything else.

## Suggesting

`suggest(word, ctx)` in [`core.js`](../src/qslex/web/core.js) is pure — no DOM, no globals beyond its arguments — and returns at most 8 distinct strings, never the input, every one of them a spelling the *active* set takes. Four sources, in this order, each drained before the next is tried:

1. **The `REP` bridge**, each single occurrence of each of the four directed pairs replaced. First because a ligature and the pair it stands for are two ways of writing one word that no single-letter edit connects, so the tier below cannot reach them at any depth it is willing to search.
2. **The cross-grade counterpart**, when the word is only in the other grade. hunspell has no notion of this; it is the whole reason the pairs table is on the page.
3. **Edit distance 1** — deletions, transpositions, substitutions, insertions — over the 44 letters in `TRY` order, keeping what the active set takes, ranked by corpus frequency descending and tied by generation order. Frequency comes from `freq_of`, which is the highest count any row writing that spelling carries in any column, so a ligature or Junior form inherits its row's count rather than falling to zero and sorting last.
4. **Two-word splits**, every split point where both halves pass, joined with a space and ranked on the rarer half. Last, because a word that is one letter from a real word is far likelier to be a typo than two words run together.

## Fixing an occurrence

Choosing a suggestion edits the textarea, not the preview. Every token in the preview is numbered per word string in document order, the number is written to the span as `data-occ`, and the fix runs the same token regex over the *source* and splices into the match with that index. The two orders agree for ordinary prose, and the design keeps them agreeing where it can: occurrences inside `pre` and `code` are **counted** even though they are never flagged, precisely so that a code span earlier in the document does not shift every index after it.

Where they can disagree, they are documented rather than solved:

- A Quikscript word inside an image's alt text, a link title or a URL is a token in the source and not a text node in the preview, so it consumes an index on one side only.
- The same goes for anything else that is source but not rendered text: reference-style link definitions, HTML comments, YAML front matter.
- Raw HTML in the Markdown can put text into the preview in an order the source does not have.

When the index does not exist on the source side the fix falls back to the first occurrence of that word, and when the word is not in the source at all it does nothing. Both are quiet, and both are the right failure: the alternative is a page that refuses to fix the ordinary case because the extraordinary one exists.

The popover itself is one reusable `<div popover="auto">`, so light-dismiss is the browser's job. It is placed with [CSS anchor positioning](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_anchor_positioning) where `CSS.supports("anchor-name: --qs")` says so, and otherwise by measuring the clicked span and clamping the popover into the viewport by hand. Rendering is debounced 150 ms off the textarea's `input` event.

## Ignoring

Every popover ends with an **Ignore** button, below the suggestions and set in `system-ui` so it reads as the secondary thing it is. Clicking it adds the word to a set the page keeps and re-renders, and the underline is gone. This is hunspell's personal dictionary, which is the answer to the same problem: a lexicon of 75,568 spellings will not carry your surname, your employer or the word you just coined, and a checker that cannot be told so is a checker people stop reading.

The semantics are deliberately the plainest available:

- **Exact whole-token match, both grades.** An ignored string is checked before the accepted set is consulted, against the token exactly as it was written. There is no hyphen-piece rule for ignoring — ignoring ·Zoo-·Vie does not bless ·Zoo — and no grade filter, because a word you have said is fine is fine in both.
- **`core.js` does not know about it.** `accepts()` stays pure, takes a set and a word, and is what the node tests hold. Ignoring lives entirely in `app.js`, one `Set` consulted one line before `accepts()` is called.
- **An ignored word can never be suggested.** It is not in either accepted set, and every suggestion tier filters against those sets, so nothing extra was needed to keep your surname out of the list of fixes for someone else's typo. Worth saying because the opposite would also have been defensible; it just is not what the sets do.

The set is persisted to `localStorage` under `qs-playground.ignored`, as a JSON array of strings, read once at startup and rewritten on every change. **Both accesses are wrapped in `try`/`catch`, and the caveat is real**: a page opened from a `file:` URL is an opaque origin in some browsers, where touching `localStorage` throws a `SecurityError` rather than returning null. The page degrades to session-only there — ignoring still works, it is just forgotten when the tab closes — which is the right failure for a facility that is a convenience, and much better than a page that will not render because storing a preference threw.

The header carries a small chip reading `Ignored: N — clear`, shown only when N is above zero and sitting between the title and the controls so that its appearing moves neither. Clicking it empties the set and the storage together and re-renders, which is the whole of the management interface: a list of ignored words with per-word removal is a feature this page has not earned yet, and clearing is the operation people actually want when they realise they ignored a typo.

## Type, and why every size is a multiple of 11

Abbots Morton Spaceport is a pixel font, and [its README](../data/abbots-morton-spaceport/README.md#which-face-is-which) states the rule the page follows rather than reinvents: **every font size on Quikscript-bearing text is a multiple of 11px**, because anything else lands the pixels off the grid and blurs them. So the preview sets 22px on 33px line-height, 44px for `h1`, 33px for `h2`, 22px bold for `h3` and below, 22px for code and `pre`; the textarea and the popover are 22px/33px; margins and padding are multiples of 11 too, which is not required but keeps the rhythm. The Bold weight is a half-pixel overstrike of the Regular and needs 22px or better to read, which every one of those sizes clears.

Smoothing is turned off with all three declarations the font README names — `-webkit-font-smoothing: none`, `-moz-osx-font-smoothing: unset`, `font-smooth: never` — on the preview, the textarea and the popover.

The page's own furniture is exempt, and deliberately: the header, the footer, the "No suggestions" line and the popover's Ignore button are `system-ui` at ordinary `rem` sizes, because none of them carries a Quikscript glyph and setting a toolbar in a pixel font at 22px would make a page that shouts. The preview's Latin — headings, prose, anything the author wrote in the Latin alphabet — renders in the Mono face, which bundles the whole of [Departure Mono](https://departuremono.com/) and sits behind Sans as its fallback, so Latin and Quikscript share one pixel grid instead of one being set in the system's sans.

## What is proved, and where

[`tests/test_playground.py`](../tests/test_playground.py) holds the builder: that two builds are byte-identical, that both cross-checks hold against the shipped `.dic` and `.aff`, that the grade sets diverge where the junior column does and where a §III contraction is and nowhere else, that the Junior `that` is not among the junior-only spellings, that only the `word` rows of the contraction list reach the page and that a contraction naming no lexicon row fails the build, that every pinned digest verifies and a single flipped byte is refused, that no injected chunk closes a script early, that exactly five faces are inlined and no placeholder survives, and that `--check` passes on a fresh page, fails on an edited one and fails on a missing one. Every count it pins over the contractions is derived from `load_contractions()` and the built payload rather than written out as PUA.

The page's own JavaScript is held by two node scripts, run through `subprocess` from that same module against a page built into a temporary directory — not against `site/`, so a run neither depends on `make site` having been run nor leaves anything behind:

- [`tests/playground_core.js`](../tests/playground_core.js) requires `core.js` directly and reads the real payload back out of the built page: tokenization (dots and apostrophes split, hyphens bind, bare-hyphen runs never tokenize), the hyphen-piece rule including edge hyphens, all four suggestion sources in their right order over real spellings, a §III contraction accepted in Senior and refused in Junior with the full form offered first, and occurrence-indexed replacement.
- [`tests/playground_page.js`](../tests/playground_page.js) runs the page's four inline scripts in a `node:vm` context over a shimmed DOM: the first render underlining exactly the one word the sample gets wrong, the click that opens the popover, choosing a fix, the copy button, the grade toggle changing both the class and the set, occurrence numbering across a code span, anchor positioning in both branches, the debounce, and the whole ignore flow — the button, the underline going, the chip appearing and clearing, the word read back by a second page over the same storage stub, and a storage stub that throws on every access still ignoring for the session.

Both are skipped when `node` is not on `PATH`, and neither needs a package installed.

What that leaves unproved, stated plainly because the gap is real: **nothing drives a browser.** The Popover API, CSS anchor positioning, the clipboard write, `@font-face` loading and every pixel of the layout are exercised by hand, not by the suite. The DOM shim is a shim — it flattens rendered HTML to a single text node, so the walk across several text nodes is not exercised, and `pre`/`code` skipping is asserted only as the occurrence *counting* it implies, never as an ancestor test that returns true. A headless render is a cheap sanity check when the CSS moves:

```sh
chrome --headless=new --screenshot=shot.png --window-size=1400,900 \
  "file://$PWD/site/index.html"
```

Any Chromium build will do; on macOS the binary is the one inside `Google Chrome.app/Contents/MacOS/`. At 1400×900 that should show two panes, Quikscript rendering as glyphs rather than as tofu, and exactly one dotted red underline — the sample document is built to carry exactly one misspelling, and [`playground_page.js`](../tests/playground_page.js) asserts the same thing without the pixels. The popover and the ignore chip are not in that shot and cannot be: both need a click, and a fresh profile has nothing ignored.

## Regenerating

```sh
make site          # rewrite site/index.html
make check         # lint, types, tests, validator, and artifact freshness
```

`make all` is still `artifacts` alone: the page is built on demand, and freshness pins it afterwards. That means a lexicon change that moves the word set leaves `site/index.html` stale until `make site` is rerun — and so does a change to `contractions.tsv`, which reaches the page without reaching `lexicon/` at all. `make check`'s `python -m qslex.playground --check` step says so, in the same words `build.py --check` uses. Rerunning it is the whole fix; the page has no state of its own to reconcile.

The counts and byte sizes written out above are prose, and prose cannot fail: after a corpus bump they are what to re-read by hand, alongside [the list `pipeline.md` keeps](pipeline.md#regenerating) for the same reason. The build prints five of them — spellings, how many of those the dictionary lists, how many are contractions it does not, senior-only and junior-only — plus the finished size, every time it runs.

Bumping a font or bumping marked is a deliberate, reviewable change by construction, because the digest is pinned in two places: replace the file, update `src/qslex/playground.py` and that directory's README together, then `make site` and `make check`. The footer names the marked version, so it moves with it.
