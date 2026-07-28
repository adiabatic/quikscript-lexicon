const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const [CORE, PAGE] = process.argv.slice(2);
assert.ok(CORE && PAGE, "usage: node playground_core.js <core.js> <index.html>");

const { TOKEN, tokens, accepts, suggest, replaceOccurrence } = require(path.resolve(CORE));
const page = fs.readFileSync(PAGE, "utf8");

const OPEN = "<script>const QS = ";
const at = page.indexOf(OPEN);
assert.ok(at > 0, "the page carries its data script");
const QS = JSON.parse(page.slice(at + OPEN.length, page.indexOf(";</script>", at)));
assert.deepEqual(Object.keys(QS).sort(), [
  "junior_only",
  "pairs",
  "rep",
  "senior_only",
  "try_order",
  "words",
]);

const counts = new Map();
for (const line of QS.words.split("\n")) {
  const tab = line.indexOf("\t");
  if (tab < 0) counts.set(line, 0);
  else counts.set(line.slice(0, tab), Number(line.slice(tab + 1)));
}
const UNION = [...counts.keys()];
const JUNIOR = new Set(UNION);
for (const word of QS.senior_only) JUNIOR.delete(word);
const SENIOR = new Set(UNION);
for (const word of QS.junior_only) SENIOR.delete(word);

const junior = (extra) =>
  Object.assign(
    {
      active: JUNIOR,
      freq: counts,
      letters: QS.try_order,
      pairs: QS.pairs,
      rep: QS.rep,
      senior: false,
    },
    extra,
  );
const senior = (extra) => Object.assign(junior(extra), { active: SENIOR, senior: true });

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
  assert.equal(UNION.length, 75636);
  assert.equal(QS.try_order.length, 44);
  assert.equal(QS.rep.length, 4);
  assert.equal(QS.pairs.length, 77);
  assert.equal(QS.senior_only.length, 73);
  assert.equal(QS.junior_only.length, 4);
});

const [A, B, C] = [...QS.try_order];
const DOT = "·";
const NAMER = "⸱";
const APOSTROPHE = "’";

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

const SHORT = UNION.find((word) => JUNIOR.has(word) && word.length === 3);
const HYPHENATED = UNION.filter((word) => word.includes("-") && word.length > 3);

check("a listed spelling is accepted and a doctored one is not", () => {
  const word = UNION[1000];
  assert.equal(accepts(JUNIOR, word), true);
  assert.equal(accepts(JUNIOR, word + word), false);
  assert.equal(accepts(JUNIOR, ""), false);
});

check("an unlisted compound passes when every hyphen piece is listed", () => {
  const left = SHORT;
  const right = UNION[2000];
  const joined = `${left}-${right}`;
  assert.equal(JUNIOR.has(joined), false, show(joined));
  assert.equal(accepts(JUNIOR, joined), true);
  assert.equal(accepts(JUNIOR, `${left}-${right}-${left}`), true);
  assert.equal(accepts(JUNIOR, `${left}-${right}${A}${B}${C}${A}${B}${C}`), false);
});

check("an edge hyphen leaves an empty piece, which passes", () => {
  const word = UNION[3000];
  assert.equal(JUNIOR.has(`-${word}`), false);
  assert.equal(accepts(JUNIOR, `-${word}`), true);
  assert.equal(accepts(JUNIOR, `${word}-`), true);
  assert.equal(accepts(JUNIOR, `-${word}-`), true);
  assert.equal(accepts(JUNIOR, "-"), true);
  assert.equal(accepts(JUNIOR, "--"), true);
});

check("hyphenated entries the lexicon lists are accepted whole", () => {
  assert.ok(HYPHENATED.length > 100, `${HYPHENATED.length} hyphenated entries`);
  for (const word of HYPHENATED.slice(0, 50)) assert.equal(accepts(JUNIOR, word), true);
});

const LIGATURED = QS.rep
  .filter(([written, meant]) => written.length === 1 && meant.length === 2)
  .flatMap(([ligature, pair]) =>
    UNION.filter((word) => word.includes(ligature)).map((word) => ({
      spelt: word,
      spelt_out: word.split(ligature).join(pair),
    })),
  )
  .filter((entry) => !JUNIOR.has(entry.spelt_out));

check("a ligature word spelt out is bridged back by the rep table first", () => {
  assert.ok(LIGATURED.length > 0, "some ligature word has an unlisted spelt-out form");
  const { spelt, spelt_out } = LIGATURED[0];
  assert.equal(accepts(JUNIOR, spelt_out), false);
  const offers = suggest(spelt_out, junior());
  assert.equal(offers[0], spelt, `${show(offers[0])} != ${show(spelt)}`);
});

check("the rep table bridges the other way too", () => {
  const { spelt, spelt_out } = LIGATURED[0];
  const offers = suggest(spelt, junior());
  assert.ok(!accepts(JUNIOR, spelt_out));
  assert.ok(!offers.includes(spelt_out), "an unlisted spelling is never offered");
  const listed = QS.rep
    .filter(([written, meant]) => written.length === 2 && meant.length === 1)
    .flatMap(([pair, ligature]) =>
      UNION.filter((word) => word.includes(pair)).map((word) =>
        word.split(pair).join(ligature),
      ),
    )
    .filter((word) => JUNIOR.has(word));
  assert.ok(listed.length > 0, "the spelt-out to ligature direction has listed targets");
});

check("a senior-only spelling is offered its junior counterpart in junior mode", () => {
  for (const word of QS.senior_only) {
    assert.equal(accepts(JUNIOR, word), false, show(word));
    assert.equal(accepts(SENIOR, word), true, show(word));
    const mate = QS.pairs.filter(([older]) => older === word).map(([, younger]) => younger);
    assert.equal(mate.length, 1, show(word));
    const offers = suggest(word, junior());
    assert.equal(offers[0], mate[0], `${show(word)}: ${show(offers[0])}`);
    assert.ok(!suggest(word, senior()).includes(mate[0]) || SENIOR.has(mate[0]));
  }
});

const CONTRACTION = "\uE665\uE654";
const FULL = "\uE665\uE673\uE654";

check("a senior contraction is Senior writing and is not Junior writing", () => {
  assert.equal(accepts(SENIOR, CONTRACTION), true, show(CONTRACTION));
  assert.equal(accepts(JUNIOR, CONTRACTION), false, show(CONTRACTION));
  assert.ok(QS.senior_only.includes(CONTRACTION), show(CONTRACTION));
  assert.equal(accepts(JUNIOR, FULL), true, show(FULL));
  assert.equal(accepts(SENIOR, FULL), true, show(FULL));
});

check("a senior contraction is offered the full spelling first in junior mode", () => {
  const offers = suggest(CONTRACTION, junior());
  assert.equal(offers[0], FULL, `${show(offers[0])} != ${show(FULL)}`);
  assert.equal(freq(CONTRACTION), freq(FULL), "it is as common as the word it writes");
});

check("a junior-only spelling is offered its senior counterpart in senior mode", () => {
  for (const word of QS.junior_only) {
    assert.equal(accepts(SENIOR, word), false, show(word));
    assert.equal(accepts(JUNIOR, word), true, show(word));
    const mate = QS.pairs.filter(([, younger]) => younger === word).map(([older]) => older);
    assert.equal(mate.length, 1, show(word));
    const offers = suggest(word, senior());
    assert.equal(offers[0], mate[0], `${show(word)}: ${show(offers[0])}`);
  }
});

const SAMPLE = page.slice(page.indexOf("<textarea"), page.indexOf("</textarea>"));
const SAMPLE_WORDS = tokens(SAMPLE).map((hit) => hit.word);
const WRONG = SAMPLE_WORDS.filter((word) => !accepts(JUNIOR, word));

check("the sample opens with exactly one word the lexicon does not carry", () => {
  assert.equal(SAMPLE_WORDS.length, 5);
  assert.equal(WRONG.length, 1);
});

check("the sample's misspelling is an edit away from the word it was made from", () => {
  const offers = suggest(WRONG[0], junior());
  assert.ok(offers.length > 0);
  assert.ok(offers.length <= 8);
  const meant = SAMPLE_WORDS[0];
  assert.ok(offers.includes(meant), `${show(meant)} not in ${offers.map(show).join(" | ")}`);
});

check("edit-distance offers come commonest first", () => {
  const offers = suggest(WRONG[0], junior());
  const single = offers.filter((offer) => !offer.includes(" "));
  const bridged = QS.rep.some(([written]) => WRONG[0].includes(written));
  const crossed = QS.pairs.some((pair) => pair.includes(WRONG[0]));
  assert.equal(bridged, false);
  assert.equal(crossed, false);
  const scores = single.map(freq);
  assert.deepEqual(scores, [...scores].sort((one, other) => other - one), scores.join(","));
  assert.ok(scores[0] > 0);
});

check("every offer is a spelling the active set takes, and never the word itself", () => {
  const sampled = [WRONG[0], ...QS.senior_only, ...QS.junior_only, ...UNION.slice(0, 40)];
  for (const word of sampled) {
    for (const ctx of [junior(), senior()]) {
      const offers = suggest(word, ctx);
      assert.ok(offers.length <= 8);
      assert.equal(new Set(offers).size, offers.length, show(word));
      for (const offer of offers) {
        assert.notEqual(offer, word);
        for (const piece of offer.split(" ")) {
          assert.equal(accepts(ctx.active, piece), true, `${show(word)} -> ${show(offer)}`);
        }
      }
    }
  }
});

const COMMON = UNION.filter(
  (word) => JUNIOR.has(word) && freq(word) > 5000 && !word.includes("-"),
);
const RUN_ON = (() => {
  for (const left of COMMON) {
    for (const right of COMMON) {
      const joined = left + right;
      if (!JUNIOR.has(joined)) return { left, right, joined };
    }
  }
  return null;
})();

check("a run-together pair of words is offered split", () => {
  assert.ok(RUN_ON, "some pair of common words runs together into an unlisted string");
  const { left, right, joined } = RUN_ON;
  assert.equal(accepts(JUNIOR, joined), false);
  const offers = suggest(joined, junior({ limit: 200 }));
  const split = offers.filter((offer) => offer.includes(" "));
  assert.ok(split.length > 0, show(joined));
  assert.ok(
    offers.includes(`${left} ${right}`),
    `${show(left)} ${show(right)} not in ${split.map(show).join(" | ")}`,
  );
  for (const offer of split) {
    const [one, other] = offer.split(" ");
    assert.equal(accepts(JUNIOR, one), true);
    assert.equal(accepts(JUNIOR, other), true);
  }
});

check("splits are ranked on the rarer half, commonest first", () => {
  const { joined } = RUN_ON;
  const split = suggest(joined, junior({ limit: 200 })).filter((offer) => offer.includes(" "));
  const scores = split.map((offer) => Math.min(...offer.split(" ").map(freq)));
  assert.deepEqual(scores, [...scores].sort((one, other) => other - one), scores.join(","));
});

check("splits are ranked after every single-word offer", () => {
  const { joined } = RUN_ON;
  const offers = suggest(joined, junior({ limit: 200 }));
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

check("a hyphenated token is replaced whole, not piecewise", () => {
  const compound = `${ONE}-${TWO}`;
  const written = `here ${compound} ends`;
  assert.equal(replaceOccurrence(written, compound, 0, THREE), `here ${THREE} ends`);
  assert.equal(replaceOccurrence(written, ONE, 0, THREE), written);
});

for (const each of done) console.log(`ok    ${each}`);
console.log(`\n${done.length} checks passed`);
