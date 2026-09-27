const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const [CORE, PAGE] = process.argv.slice(2);
assert.ok(CORE && PAGE, "usage: node desk_core.js <core.js> <index.html>");

const {
  TOKEN,
  tokens,
  accepts,
  distance,
  suggest,
  replaceOccurrence,
  replaceOccurrences,
  stripFrontMatter,
} = require(path.resolve(CORE));
const page = fs.readFileSync(PAGE, "utf8");

const OPEN = "<script>const QS = ";
const at = page.indexOf(OPEN);
assert.ok(at > 0, "the page has its data script");
const QS = JSON.parse(page.slice(at + OPEN.length, page.indexOf(";</script>", at)));
assert.deepEqual(Object.keys(QS).sort(), ["confusions", "rep", "try_order", "words"]);

const counts = new Map();
for (const line of QS.words.split("\n")) {
  const tab = line.indexOf("\t");
  if (tab < 0) counts.set(line, 0);
  else counts.set(line.slice(0, tab), Number(line.slice(tab + 1)));
}
const UNION = [...counts.keys()];
const ACCEPTED = new Set(UNION);

const suggestContext = (extra) =>
  Object.assign(
    {
      active: ACCEPTED,
      freq: counts,
      groups: QS.confusions,
      letters: QS.try_order,
      rep: QS.rep,
    },
    extra,
  );

const freq = (word) => counts.get(word) || 0;
const show = (word) => [...word].map((one) => one.codePointAt(0).toString(16)).join(" ");

const done = [];
function check(name, body) {
  try {
    body();
  } catch (failure) {
    for (const each of done) console.log(`ok    ${each}`);
    console.log(`FAIL  ${name}`);
    throw failure;
  }
  done.push(name);
}

check("the page's word list is the whole lexicon and the senior contractions", () => {
  assert.equal(UNION.length, 75674);
  assert.equal(QS.try_order.length, 44);
  assert.equal(QS.rep.length, 4);
  assert.equal(QS.confusions.length, 1);
});

const [A, B, C] = [...QS.try_order];
const NAMER_DOT = "·";
const WORD_SEPARATOR_DOT = "⸱";
const APOSTROPHE = "’";
const ANGLE_OPEN = "\uE66E";
const ANGLE_CLOSE = "\uE66F";
const UNASSIGNED = "\uE66D";
const ZWNJ = "\u200C";
const ZWJ = "\u200D";
const VARIATION = "\uFE0F";
const SOFT_HYPHEN = "\u00AD";

check("tokens are runs of Quikscript letters with their offsets", () => {
  assert.deepEqual(tokens(""), []);
  assert.deepEqual(tokens("plain latin text"), []);
  const one = tokens(`  ${A}${B}${C}  `);
  assert.equal(one.length, 1);
  assert.equal(one[0].word, A + B + C);
  assert.equal(one[0].start, 2);
  assert.equal(one[0].end, 5);
});

check("a middle dot splits a run", () => {
  assert.deepEqual(
    tokens(`${A}${B}${NAMER_DOT}${C}${A}`).map((hit) => hit.word),
    [A + B, C + A],
  );
  assert.deepEqual(
    tokens(`${WORD_SEPARATOR_DOT}${A}${B}`).map((hit) => hit.word),
    [A + B],
  );
});

check("a single letter after a namer dot is a letter named, not a word", () => {
  assert.deepEqual(tokens(`${NAMER_DOT}${A}`), []);
  assert.deepEqual(tokens(`${NAMER_DOT}${A} ${NAMER_DOT}${B}${NAMER_DOT}${C}`), []);
  assert.deepEqual(
    tokens(`${NAMER_DOT}${A}${B} ${A} ${WORD_SEPARATOR_DOT}${A}`).map((hit) => hit.word),
    [A + B, A, A],
  );
  assert.deepEqual(
    tokens(`${A} ${NAMER_DOT}${B} ${C}`).map((hit) => hit.start),
    [0, 5],
  );
});

check("an invisible mark inside a run does not split it", () => {
  for (const mark of [ZWNJ, ZWJ, VARIATION, SOFT_HYPHEN]) {
    const hits = tokens(`${A}${mark}${B}`);
    assert.equal(hits.length, 1, show(mark));
    assert.equal(hits[0].word, A + B, show(mark));
    assert.equal(hits[0].start, 0);
    assert.equal(hits[0].end, 3);
  }
  assert.deepEqual(
    tokens(`${A}${ZWNJ} ${B}`).map((hit) => [hit.word, hit.start, hit.end]),
    [
      [A, 0, 1],
      [B, 3, 4],
    ],
  );
  assert.deepEqual(tokens(`${NAMER_DOT}${ZWNJ}${A}`), []);
});

check("a right single quote splits a run", () => {
  assert.deepEqual(
    tokens(`${A}${B}${APOSTROPHE}${C}`).map((hit) => hit.word),
    [A + B, C],
  );
});

check("an angled parenthesis splits a run", () => {
  assert.deepEqual(
    tokens(`${ANGLE_OPEN}${A}${B}${C}${ANGLE_CLOSE}`).map((hit) => hit.word),
    [A + B + C],
  );
  assert.deepEqual(
    tokens(`${A}${ANGLE_CLOSE} ${ANGLE_OPEN}${B}`).map((hit) => hit.word),
    [A, B],
  );
  assert.deepEqual(tokens(`${ANGLE_OPEN}${ANGLE_CLOSE}`), [], "a bare pair is not a word");
  assert.deepEqual(
    tokens(`${A}${UNASSIGNED}${B}`).map((hit) => hit.word),
    [A, B],
    "the third codepoint in the same gap has no letter either",
  );
});

check("a hyphen that follows a letter is part of that letter's token", () => {
  assert.deepEqual(
    tokens(`${A}-${B}`).map((hit) => hit.word),
    [A + "-" + B],
  );
  assert.deepEqual(
    tokens(`${A}--${B} ${C}-`).map((hit) => hit.word),
    [A + "--" + B, C + "-"],
  );
});

check("a run of bare hyphens is never a token", () => {
  assert.deepEqual(tokens("--"), []);
  assert.deepEqual(tokens("- - -"), []);
  assert.deepEqual(tokens("a --- b"), []);
  assert.deepEqual(
    tokens(`- ${A}`).map((hit) => hit.word),
    [A],
  );
});

check("the shared regex is not left mid-string between calls", () => {
  const text = `${A}${B} ${C}${A}`;
  assert.deepEqual(tokens(text), tokens(text));
  TOKEN.lastIndex = 3;
  assert.equal(tokens(text).length, 2);
});

check("a leading YAML front matter block is stripped", () => {
  const body = "# heading\n\nprose\n";
  assert.equal(stripFrontMatter(`---\ntitle: x\ndraft: true\n---\n${body}`), body);
  assert.equal(stripFrontMatter(`---\r\ntitle: x\r\n---\r\n${body}`), body);
  assert.equal(stripFrontMatter(`---\n---\n${body}`), body, "an empty block still strips");
});

check("front matter is only recognized at the very start of the document", () => {
  const prose = "not front matter\n\n---\ntitle: x\n---\n";
  assert.equal(stripFrontMatter(prose), prose);
  assert.equal(stripFrontMatter(`\n---\ntitle: x\n---\nbody\n`), `\n---\ntitle: x\n---\nbody\n`);
});

check("an unterminated opening delimiter is left alone", () => {
  const open = "---\ntitle: x\n\nno closing delimiter\n";
  assert.equal(stripFrontMatter(open), open);
});

check("a Quikscript word inside front matter is not tokenized", () => {
  const word = UNION[0];
  const stripped = stripFrontMatter(`---\ntitle: ${word}\n---\n\n${word}\n`);
  assert.deepEqual(
    tokens(stripped).map((hit) => hit.word),
    [word],
    "only the copy after the front matter tokenizes",
  );
});

const SHORT = UNION.find((word) => word.length === 3);
const HYPHENATED = UNION.filter((word) => word.includes("-") && word.length > 3);

check("a listed spelling is accepted and a doctored one is not", () => {
  const word = UNION[1000];
  assert.equal(accepts(ACCEPTED, word), true);
  assert.equal(accepts(ACCEPTED, word + word), false);
  assert.equal(accepts(ACCEPTED, ""), false);
});

check("an unlisted compound passes when every hyphen piece is listed", () => {
  const left = SHORT;
  const right = UNION[2000];
  const joined = `${left}-${right}`;
  assert.equal(ACCEPTED.has(joined), false, show(joined));
  assert.equal(accepts(ACCEPTED, joined), true);
  assert.equal(accepts(ACCEPTED, `${left}-${right}-${left}`), true);
  assert.equal(accepts(ACCEPTED, `${left}-${right}${A}${B}${C}${A}${B}${C}`), false);
});

check("an edge hyphen leaves an empty piece, which passes", () => {
  const word = UNION[3000];
  assert.equal(ACCEPTED.has(`-${word}`), false);
  assert.equal(accepts(ACCEPTED, `-${word}`), true);
  assert.equal(accepts(ACCEPTED, `${word}-`), true);
  assert.equal(accepts(ACCEPTED, `-${word}-`), true);
  assert.equal(accepts(ACCEPTED, "-"), true);
  assert.equal(accepts(ACCEPTED, "--"), true);
});

check("hyphenated entries the lexicon lists are accepted whole", () => {
  assert.ok(HYPHENATED.length > 100, `${HYPHENATED.length} hyphenated entries`);
  for (const word of HYPHENATED.slice(0, 50)) assert.equal(accepts(ACCEPTED, word), true);
});

const X_LETTERED = QS.rep
  .filter(([written, meant]) => written.length === 1 && meant.length === 2)
  .flatMap(([xLetter, pair]) =>
    UNION.filter((word) => word.includes(xLetter)).map((word) => ({
      spelled: word,
      spelled_out: word.split(xLetter).join(pair),
    })),
  )
  .filter((entry) => !ACCEPTED.has(entry.spelled_out));

check("a spelled-out X-letter word gets its REP-table form as the first suggestion", () => {
  assert.ok(X_LETTERED.length > 0, "some X-letter word has an unlisted spelled-out form");
  const { spelled, spelled_out } = X_LETTERED[0];
  assert.equal(accepts(ACCEPTED, spelled_out), false);
  const suggestions = suggest(spelled_out, suggestContext());
  assert.equal(suggestions[0], spelled, `${show(suggestions[0])} != ${show(spelled)}`);
});

check("the REP table also maps letter pairs to X-letters, and an unlisted spelling is never suggested", () => {
  const { spelled, spelled_out } = X_LETTERED[0];
  const suggestions = suggest(spelled, suggestContext());
  assert.ok(!accepts(ACCEPTED, spelled_out));
  assert.ok(!suggestions.includes(spelled_out), "an unlisted spelling is never suggested");
  const listed = QS.rep
    .filter(([written, meant]) => written.length === 2 && meant.length === 1)
    .flatMap(([pair, xLetter]) =>
      UNION.filter((word) => word.includes(pair)).map((word) =>
        word.split(pair).join(xLetter),
      ),
    )
    .filter((word) => ACCEPTED.has(word));
  assert.ok(listed.length > 0, "the spelled-out to X-letter direction has listed targets");
});

const GROUP = QS.confusions[0];
const MISVOWELED = "\uE663\uE67A\uE652\uE65A";
const WHATS = "\uE663\uE678\uE652\uE65A";

const isVowelSwap = (word) => (suggestion) => {
  if (suggestion.length !== word.length) return false;
  const differing = [...suggestion]
    .map((letter, slot) => [letter, word[slot]])
    .filter(([one, other]) => one !== other);
  return (
    differing.length === 1 &&
    QS.confusions.some((group) => differing[0].every((letter) => group.includes(letter)))
  );
};

check("the confusion group is the fifteen vowels", () => {
  assert.equal(GROUP.length, 15);
  assert.equal(new Set(GROUP).size, 15);
  for (const letter of GROUP) {
    const codepoint = letter.codePointAt(0);
    assert.ok(codepoint >= 0xe670 && codepoint <= 0xe67e, show(letter));
  }
});

check("a one-vowel swap is suggested before edit-distance suggestions", () => {
  assert.equal(accepts(ACCEPTED, MISVOWELED), false, show(MISVOWELED));
  assert.equal(accepts(ACCEPTED, WHATS), true, show(WHATS));
  assert.equal(freq(WHATS), 0, "the corpus gives this word no count; if an update gives it one, pick another word");
  const suggestions = suggest(MISVOWELED, suggestContext());
  const at = suggestions.indexOf(WHATS);
  assert.ok(at >= 0, `${show(WHATS)} not in ${suggestions.map(show).join(" | ")}`);
  for (const suggestion of suggestions.slice(0, at)) {
    assert.ok(isVowelSwap(MISVOWELED)(suggestion), show(suggestion));
  }
});

const CONTRACTION = "\uE665\uE654";
const FULL = "\uE665\uE673\uE654";

check("a \u00A7III contraction and its full spelling are both accepted at once", () => {
  assert.equal(accepts(ACCEPTED, CONTRACTION), true, show(CONTRACTION));
  assert.equal(accepts(ACCEPTED, FULL), true, show(FULL));
  assert.equal(freq(CONTRACTION), freq(FULL), "it is as common as the word it writes");
});

const SAMPLE = page.slice(page.indexOf("<textarea"), page.indexOf("</textarea>"));
const SAMPLE_WORDS = tokens(SAMPLE).map((hit) => hit.word);
const WRONG = SAMPLE_WORDS.filter((word) => !accepts(ACCEPTED, word));

check("the sample has exactly one word the lexicon does not list", () => {
  assert.equal(SAMPLE_WORDS.length, 5);
  assert.equal(WRONG.length, 1);
});

check("the sample's misspelling is an edit away from the word it was made from", () => {
  const suggestions = suggest(WRONG[0], suggestContext());
  assert.ok(suggestions.length > 0);
  assert.ok(suggestions.length <= 10);
  const meant = SAMPLE_WORDS[0];
  assert.ok(
    suggestions.includes(meant),
    `${show(meant)} not in ${suggestions.map(show).join(" | ")}`,
  );
});

check("vowel swaps come first, then suggestions by edit distance, each group most frequent first", () => {
  const suggestions = suggest(WRONG[0], suggestContext());
  const single = suggestions.filter((suggestion) => !suggestion.includes(" "));
  const hasRepSubstitution = QS.rep.some(([written]) => WRONG[0].includes(written));
  assert.equal(hasRepSubstitution, false);
  const isSwap = isVowelSwap(WRONG[0]);
  const groups = [
    single.filter(isSwap),
    single.filter((suggestion) => !isSwap(suggestion) && distance(WRONG[0], suggestion, 3) === 1),
    single.filter((suggestion) => !isSwap(suggestion) && distance(WRONG[0], suggestion, 3) === 2),
    single.filter((suggestion) => !isSwap(suggestion) && distance(WRONG[0], suggestion, 3) === 3),
  ];
  assert.deepEqual(
    single,
    groups.flat(),
    "vowel swaps, then one edit, then two, then three",
  );
  for (const group of groups) {
    const scores = group.map(freq);
    assert.deepEqual(scores, [...scores].sort((one, other) => other - one), scores.join(","));
  }
  assert.ok(freq(single[0]) > 0);
});

const LONGISH = UNION.find((word) => word.length >= 9 && !word.includes("-"));
const TWO_AWAY = LONGISH[1] + LONGISH.slice(3);
const swap = (letter) => (letter === A ? B : A);
const THREE_AWAY =
  swap(LONGISH[0]) +
  LONGISH[1] +
  swap(LONGISH[2]) +
  LONGISH[3] +
  swap(LONGISH[4]) +
  LONGISH.slice(5);
const GIBBERISH = A.repeat(10);

check("a typo two edits away still has the word it came from among its suggestions", () => {
  assert.equal(ACCEPTED.has(TWO_AWAY), false, show(TWO_AWAY));
  const suggestions = suggest(TWO_AWAY, suggestContext());
  assert.ok(
    suggestions.includes(LONGISH),
    `${show(LONGISH)} not in ${suggestions.map(show).join(" | ")}`,
  );
});

check("a typo three edits away still has the word it came from among its suggestions", () => {
  assert.equal(ACCEPTED.has(THREE_AWAY), false, show(THREE_AWAY));
  assert.equal(distance(THREE_AWAY, LONGISH, 3), 3);
  const suggestions = suggest(THREE_AWAY, suggestContext());
  assert.ok(
    suggestions.includes(LONGISH),
    `${show(LONGISH)} not in ${suggestions.map(show).join(" | ")}`,
  );
});

check("a two-edit suggestion comes before a more frequent three-edit suggestion", () => {
  const suggestions = suggest(TWO_AWAY, suggestContext()).filter(
    (suggestion) => !suggestion.includes(" "),
  );
  const edits = suggestions.map((suggestion) => distance(TWO_AWAY, suggestion, 3));
  const near = edits.indexOf(2);
  const far = edits.indexOf(3);
  assert.ok(near >= 0, "no two-edit suggestion");
  assert.ok(far >= 0, "no three-edit suggestion");
  assert.ok(edits.lastIndexOf(2) < far, suggestions.map(show).join(" | "));
  assert.ok(
    freq(suggestions[far]) > freq(suggestions[near]),
    "the three-edit suggestion must be more frequent, or frequency alone would order these",
  );
});

check("a typo with no word within three edits gets no suggestions", () => {
  assert.equal(ACCEPTED.has(GIBBERISH), false, show(GIBBERISH));
  assert.deepEqual(suggest(GIBBERISH, suggestContext()), []);
});

check("every suggestion is accepted and differs from the word", () => {
  const sampled = [WRONG[0], CONTRACTION, ...UNION.slice(0, 40)];
  for (const word of sampled) {
    const ctx = suggestContext();
    const suggestions = suggest(word, ctx);
    assert.ok(suggestions.length <= 10);
    assert.equal(new Set(suggestions).size, suggestions.length, show(word));
    for (const suggestion of suggestions) {
      assert.notEqual(suggestion, word);
      for (const piece of suggestion.split(" ")) {
        assert.equal(accepts(ctx.active, piece), true, `${show(word)} -> ${show(suggestion)}`);
      }
    }
  }
});

const COMMON = UNION.filter((word) => freq(word) > 5000 && !word.includes("-"));
const RUN_ON = (() => {
  for (const left of COMMON) {
    for (const right of COMMON) {
      const joined = left + right;
      if (!ACCEPTED.has(joined)) return { left, right, joined };
    }
  }
  return null;
})();

check("a run-together pair of words gets the split pair as a suggestion", () => {
  assert.ok(RUN_ON, "some pair of common words runs together into an unlisted string");
  const { left, right, joined } = RUN_ON;
  assert.equal(accepts(ACCEPTED, joined), false);
  const suggestions = suggest(joined, suggestContext({ limit: 200 }));
  const split = suggestions.filter((suggestion) => suggestion.includes(" "));
  assert.ok(split.length > 0, show(joined));
  assert.ok(
    suggestions.includes(`${left} ${right}`),
    `${show(left)} ${show(right)} not in ${split.map(show).join(" | ")}`,
  );
  for (const suggestion of split) {
    const [one, other] = suggestion.split(" ");
    assert.equal(accepts(ACCEPTED, one), true);
    assert.equal(accepts(ACCEPTED, other), true);
  }
});

check("splits are ranked by the less frequent half, most frequent first", () => {
  const { joined } = RUN_ON;
  const split = suggest(joined, suggestContext({ limit: 200 })).filter((suggestion) =>
    suggestion.includes(" "),
  );
  const scores = split.map((suggestion) => Math.min(...suggestion.split(" ").map(freq)));
  assert.deepEqual(scores, [...scores].sort((one, other) => other - one), scores.join(","));
});

check("splits come after every single-word suggestion", () => {
  const { joined } = RUN_ON;
  const suggestions = suggest(joined, suggestContext({ limit: 200 }));
  const first = suggestions.findIndex((suggestion) => suggestion.includes(" "));
  if (first >= 0) {
    assert.ok(suggestions.slice(first).every((suggestion) => suggestion.includes(" ")));
  }
});

const [ONE, TWO, THREE] = [UNION[100], UNION[200], UNION[300]];
const PROSE = `${ONE} ${TWO} ${ONE} and ${ONE}${NAMER_DOT}${THREE}`;

check("the numbered occurrence of a word is the one replaced", () => {
  assert.equal(tokens(PROSE).filter((hit) => hit.word === ONE).length, 3);
  const first = replaceOccurrence(PROSE, ONE, 0, TWO);
  const middle = replaceOccurrence(PROSE, ONE, 1, TWO);
  const last = replaceOccurrence(PROSE, ONE, 2, TWO);
  assert.equal(first, `${TWO} ${TWO} ${ONE} and ${ONE}${NAMER_DOT}${THREE}`);
  assert.equal(middle, `${ONE} ${TWO} ${TWO} and ${ONE}${NAMER_DOT}${THREE}`);
  assert.equal(last, `${ONE} ${TWO} ${ONE} and ${TWO}${NAMER_DOT}${THREE}`);
  assert.notEqual(first, middle);
});

check("a replacement containing a space is inserted whole", () => {
  const fixed = replaceOccurrence(PROSE, ONE, 1, `${TWO} ${THREE}`);
  assert.equal(fixed, `${ONE} ${TWO} ${TWO} ${THREE} and ${ONE}${NAMER_DOT}${THREE}`);
});

check("an occurrence past the end falls back to the first", () => {
  assert.equal(replaceOccurrence(PROSE, ONE, 9, TWO), replaceOccurrence(PROSE, ONE, 0, TWO));
  assert.equal(replaceOccurrence(PROSE, ONE, -1, TWO), replaceOccurrence(PROSE, ONE, 0, TWO));
});

check("a word that is not there is left alone", () => {
  const absent = UNION[400];
  assert.equal(replaceOccurrence(PROSE, absent, 0, TWO), PROSE);
  assert.equal(replaceOccurrence("", ONE, 0, TWO), "");
});

check("several numbered occurrences are replaced in one pass", () => {
  const replaced = replaceOccurrences(PROSE, ONE, [0, 2], TWO);
  assert.equal(replaced, `${TWO} ${TWO} ${ONE} and ${TWO}${NAMER_DOT}${THREE}`);
  assert.equal(replaceOccurrences(PROSE, ONE, [2, 0], TWO), replaced, "order does not matter");
  assert.equal(replaceOccurrences(PROSE, ONE, [1, 1], TWO), replaceOccurrence(PROSE, ONE, 1, TWO));
  assert.equal(
    replaceOccurrences(PROSE, ONE, [0, 1, 2], TWO),
    `${TWO} ${TWO} ${TWO} and ${TWO}${NAMER_DOT}${THREE}`,
  );
});

check("a list naming no occurrence that is there falls back like the single form", () => {
  const first = replaceOccurrence(PROSE, ONE, 0, TWO);
  assert.equal(replaceOccurrences(PROSE, ONE, [], TWO), first);
  assert.equal(replaceOccurrences(PROSE, ONE, [7, 9], TWO), first);
  assert.equal(
    replaceOccurrences(PROSE, ONE, [9, 1], TWO),
    replaceOccurrence(PROSE, ONE, 1, TWO),
    "a stray index is dropped, not rounded to the first",
  );
  assert.equal(replaceOccurrences(PROSE, UNION[400], [0, 1], TWO), PROSE);
  assert.equal(replaceOccurrences("", ONE, [0], TWO), "");
});

check("occurrences are numbered past the front matter, as the page numbers them", () => {
  const doc = `---\ntitle: ${ONE}\n---\n\n${ONE} ${TWO} ${ONE}\n`;
  assert.equal(
    replaceOccurrence(doc, ONE, 0, THREE),
    `---\ntitle: ${ONE}\n---\n\n${THREE} ${TWO} ${ONE}\n`,
    "the copy in the front matter does not count and is never touched",
  );
  assert.equal(
    replaceOccurrences(doc, ONE, [0, 1], THREE),
    `---\ntitle: ${ONE}\n---\n\n${THREE} ${TWO} ${THREE}\n`,
  );
});

check("a hyphenated token is replaced whole, not piecewise", () => {
  const compound = `${ONE}-${TWO}`;
  const written = `here ${compound} ends`;
  assert.equal(replaceOccurrence(written, compound, 0, THREE), `here ${THREE} ends`);
  assert.equal(replaceOccurrence(written, ONE, 0, THREE), written);
});

for (const each of done) console.log(`ok    ${each}`);
console.log(`\n${done.length} checks passed`);
