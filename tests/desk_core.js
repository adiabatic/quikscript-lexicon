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
assert.ok(at > 0, "the page carries its data script");
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

const advice = (extra) =>
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
  assert.equal(UNION.length, 75652);
  assert.equal(QS.try_order.length, 44);
  assert.equal(QS.rep.length, 4);
  assert.equal(QS.confusions.length, 1);
});

const [A, B, C] = [...QS.try_order];
const DOT = "·";
const NAMER = "⸱";
const APOSTROPHE = "’";
const ANGLE_OPEN = "\uE66E";
const ANGLE_CLOSE = "\uE66F";
const UNASSIGNED = "\uE66D";

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
    tokens(`${A}${B}${DOT}${C}${A}`).map((hit) => hit.word),
    [A + B, C + A],
  );
  assert.deepEqual(
    tokens(`${NAMER}${A}${B}`).map((hit) => hit.word),
    [A + B],
  );
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
    "the third codepoint in the same gap carries no letter either",
  );
});

check("hyphens bind into the run they follow a letter in", () => {
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

check("a Quikscript word inside stripped front matter never reaches a token scan", () => {
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

check("an X-letter word spelled out is bridged back by the rep table first", () => {
  assert.ok(X_LETTERED.length > 0, "some X-letter word has an unlisted spelled-out form");
  const { spelled, spelled_out } = X_LETTERED[0];
  assert.equal(accepts(ACCEPTED, spelled_out), false);
  const offers = suggest(spelled_out, advice());
  assert.equal(offers[0], spelled, `${show(offers[0])} != ${show(spelled)}`);
});

check("the rep table bridges the other way too", () => {
  const { spelled, spelled_out } = X_LETTERED[0];
  const offers = suggest(spelled, advice());
  assert.ok(!accepts(ACCEPTED, spelled_out));
  assert.ok(!offers.includes(spelled_out), "an unlisted spelling is never offered");
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

const misgrouped = (word) => (offer) => {
  if (offer.length !== word.length) return false;
  const differing = [...offer]
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
    const held = letter.codePointAt(0);
    assert.ok(held >= 0xe670 && held <= 0xe67e, show(letter));
  }
});

check("a wrong vowel is fixed ahead of every other kind of edit", () => {
  assert.equal(accepts(ACCEPTED, MISVOWELED), false, show(MISVOWELED));
  assert.equal(accepts(ACCEPTED, WHATS), true, show(WHATS));
  assert.equal(freq(WHATS), 0, "a corpus bump that counts it needs a new specimen");
  const offers = suggest(MISVOWELED, advice());
  const at = offers.indexOf(WHATS);
  assert.ok(at >= 0, `${show(WHATS)} not in ${offers.map(show).join(" | ")}`);
  for (const offer of offers.slice(0, at)) {
    assert.ok(misgrouped(MISVOWELED)(offer), show(offer));
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

check("the sample opens with exactly one word the lexicon does not carry", () => {
  assert.equal(SAMPLE_WORDS.length, 5);
  assert.equal(WRONG.length, 1);
});

check("the sample's misspelling is an edit away from the word it was made from", () => {
  const offers = suggest(WRONG[0], advice());
  assert.ok(offers.length > 0);
  assert.ok(offers.length <= 10);
  const meant = SAMPLE_WORDS[0];
  assert.ok(offers.includes(meant), `${show(meant)} not in ${offers.map(show).join(" | ")}`);
});

check("edit-distance offers come commonest first within their tier", () => {
  const offers = suggest(WRONG[0], advice());
  const single = offers.filter((offer) => !offer.includes(" "));
  const bridged = QS.rep.some(([written]) => WRONG[0].includes(written));
  assert.equal(bridged, false);
  const grouped = misgrouped(WRONG[0]);
  const tiers = [
    single.filter(grouped),
    single.filter((offer) => !grouped(offer) && distance(WRONG[0], offer, 3) === 1),
    single.filter((offer) => !grouped(offer) && distance(WRONG[0], offer, 3) === 2),
    single.filter((offer) => !grouped(offer) && distance(WRONG[0], offer, 3) === 3),
  ];
  assert.deepEqual(
    single,
    tiers.flat(),
    "in-group fixes, then one edit, then two, then three",
  );
  for (const tier of tiers) {
    const scores = tier.map(freq);
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

check("a typo two edits away is still offered the word it came from", () => {
  assert.equal(ACCEPTED.has(TWO_AWAY), false, show(TWO_AWAY));
  const offers = suggest(TWO_AWAY, advice());
  assert.ok(
    offers.includes(LONGISH),
    `${show(LONGISH)} not in ${offers.map(show).join(" | ")}`,
  );
});

check("a typo three edits away is still offered the word it came from", () => {
  assert.equal(ACCEPTED.has(THREE_AWAY), false, show(THREE_AWAY));
  assert.equal(distance(THREE_AWAY, LONGISH, 3), 3);
  const offers = suggest(THREE_AWAY, advice());
  assert.ok(
    offers.includes(LONGISH),
    `${show(LONGISH)} not in ${offers.map(show).join(" | ")}`,
  );
});

check("a two-edit offer outranks a commoner offer three edits out", () => {
  const offers = suggest(TWO_AWAY, advice()).filter((offer) => !offer.includes(" "));
  const edits = offers.map((offer) => distance(TWO_AWAY, offer, 3));
  const near = edits.indexOf(2);
  const far = edits.indexOf(3);
  assert.ok(near >= 0, "no two-edit offer to hold ahead");
  assert.ok(far >= 0, "no three-edit offer to hold behind");
  assert.ok(edits.lastIndexOf(2) < far, offers.map(show).join(" | "));
  assert.ok(
    freq(offers[far]) > freq(offers[near]),
    "the far offer must be commoner, or frequency alone would order these",
  );
});

check("a typo nothing is within three edits of is offered nothing", () => {
  assert.equal(ACCEPTED.has(GIBBERISH), false, show(GIBBERISH));
  assert.deepEqual(suggest(GIBBERISH, advice()), []);
});

check("every offer is a spelling the accepted set takes, and never the word itself", () => {
  const sampled = [WRONG[0], CONTRACTION, ...UNION.slice(0, 40)];
  for (const word of sampled) {
    const ctx = advice();
    const offers = suggest(word, ctx);
    assert.ok(offers.length <= 10);
    assert.equal(new Set(offers).size, offers.length, show(word));
    for (const offer of offers) {
      assert.notEqual(offer, word);
      for (const piece of offer.split(" ")) {
        assert.equal(accepts(ctx.active, piece), true, `${show(word)} -> ${show(offer)}`);
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

check("a run-together pair of words is offered split", () => {
  assert.ok(RUN_ON, "some pair of common words runs together into an unlisted string");
  const { left, right, joined } = RUN_ON;
  assert.equal(accepts(ACCEPTED, joined), false);
  const offers = suggest(joined, advice({ limit: 200 }));
  const split = offers.filter((offer) => offer.includes(" "));
  assert.ok(split.length > 0, show(joined));
  assert.ok(
    offers.includes(`${left} ${right}`),
    `${show(left)} ${show(right)} not in ${split.map(show).join(" | ")}`,
  );
  for (const offer of split) {
    const [one, other] = offer.split(" ");
    assert.equal(accepts(ACCEPTED, one), true);
    assert.equal(accepts(ACCEPTED, other), true);
  }
});

check("splits are ranked on the rarer half, commonest first", () => {
  const { joined } = RUN_ON;
  const split = suggest(joined, advice({ limit: 200 })).filter((offer) => offer.includes(" "));
  const scores = split.map((offer) => Math.min(...offer.split(" ").map(freq)));
  assert.deepEqual(scores, [...scores].sort((one, other) => other - one), scores.join(","));
});

check("splits are ranked after every single-word offer", () => {
  const { joined } = RUN_ON;
  const offers = suggest(joined, advice({ limit: 200 }));
  const first = offers.findIndex((offer) => offer.includes(" "));
  if (first >= 0) {
    assert.ok(offers.slice(first).every((offer) => offer.includes(" ")));
  }
});

const [ONE, TWO, THREE] = [UNION[100], UNION[200], UNION[300]];
const PROSE = `${ONE} ${TWO} ${ONE} and ${ONE}${DOT}${THREE}`;

check("the numbered occurrence of a word is the one replaced", () => {
  assert.equal(tokens(PROSE).filter((hit) => hit.word === ONE).length, 3);
  const first = replaceOccurrence(PROSE, ONE, 0, TWO);
  const middle = replaceOccurrence(PROSE, ONE, 1, TWO);
  const last = replaceOccurrence(PROSE, ONE, 2, TWO);
  assert.equal(first, `${TWO} ${TWO} ${ONE} and ${ONE}${DOT}${THREE}`);
  assert.equal(middle, `${ONE} ${TWO} ${TWO} and ${ONE}${DOT}${THREE}`);
  assert.equal(last, `${ONE} ${TWO} ${ONE} and ${TWO}${DOT}${THREE}`);
  assert.notEqual(first, middle);
});

check("a replacement holding a space splices in whole", () => {
  const fixed = replaceOccurrence(PROSE, ONE, 1, `${TWO} ${THREE}`);
  assert.equal(fixed, `${ONE} ${TWO} ${TWO} ${THREE} and ${ONE}${DOT}${THREE}`);
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
  const swept = replaceOccurrences(PROSE, ONE, [0, 2], TWO);
  assert.equal(swept, `${TWO} ${TWO} ${ONE} and ${TWO}${DOT}${THREE}`);
  assert.equal(replaceOccurrences(PROSE, ONE, [2, 0], TWO), swept, "order does not matter");
  assert.equal(replaceOccurrences(PROSE, ONE, [1, 1], TWO), replaceOccurrence(PROSE, ONE, 1, TWO));
  assert.equal(
    replaceOccurrences(PROSE, ONE, [0, 1, 2], TWO),
    `${TWO} ${TWO} ${TWO} and ${TWO}${DOT}${THREE}`,
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
