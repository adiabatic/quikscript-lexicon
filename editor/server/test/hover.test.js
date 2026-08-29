const assert = require("node:assert/strict");
const { test } = require("node:test");
const data = require("../payload.json");
const { lexicon } = require("../lib/lexicon.js");
const { readings, writings } = require("../lib/lookup.js");
const { advised, described, glossed, hovered } = require("../lib/hover.js");
const { accepts, suggest } = require("../../../src/qslex/web/core.js");

const READ = readings(data);
const WRITE = writings(data);
const WORDS = lexicon(data);
const READ_EAT = "";
const READ_ET = "";
const COULDNT = "";
const COULDNT_JUNIOR = "";
const EXPECT = "";
const EXPECT_X = "";
const PERHAPS = "";
const PERHAPS_OUT = "";
const BAD = "".repeat(9);

/**
 * @param {string[]} lines
 * @returns {string}
 */
function fence(...lines) {
  return ["```plaintext", ...lines, "```"].join("\n");
}

/**
 * @param {string} value
 * @param {boolean} within
 * @returns {string[]}
 */
function sifted(value, within) {
  let inside = false;
  /** @type {string[]} */
  const out = [];
  for (const line of value.split("\n")) {
    if (line.trim().startsWith("```")) {
      inside = !inside;
      continue;
    }
    if (inside === within) out.push(line);
  }
  return out;
}

/**
 * @param {string} value
 * @returns {boolean}
 */
function spelled(value) {
  return [...value].some((mark) => {
    const at = mark.codePointAt(0) || 0;
    return (at >= 0xe650 && at <= 0xe66c) || (at >= 0xe670 && at <= 0xe67e);
  });
}

/**
 * @param {string} seed
 * @returns {string}
 */
function misspelled(seed) {
  for (let code = 0xe650; code <= 0xe66c; code += 1) {
    const word = seed + String.fromCharCode(code);
    if (!accepts(WORDS.active, word)) return word;
  }
  throw new Error("every extension of the seed is spelled");
}

function advice() {
  return {
    active: WORDS.active,
    freq: WORDS.counts,
    groups: WORDS.groups,
    letters: WORDS.letters,
    rep: WORDS.rep,
  };
}

const READ_TOLD =
  `${fence(READ_EAT)}\n\n` +
  "**read** — singular noun, verb, infinitive\n\n" +
  "**reade** — proper noun\n\n" +
  "**reed** — singular noun";

test("a spelling names every word it writes", () => {
  assert.equal(described(READ_EAT, READ, WRITE), READ_TOLD);
});

test("a heteronym's other face reads apart", () => {
  assert.equal(
    described(READ_ET, READ, WRITE),
    `${fence(READ_ET)}\n\n` +
      "**read** — past-tense verb, past participle\n\n" +
      "**red** — adjective, singular noun",
  );
});

test("a junior form and its senior name each other", () => {
  assert.equal(
    described(COULDNT_JUNIOR, READ, WRITE),
    `${fence(COULDNT_JUNIOR)}\n\n**couldn't** — modal verb + not  \n` +
      `Junior form:  \n${fence(`Senior: ${COULDNT}`)}`,
  );
  assert.equal(
    described(COULDNT, READ, WRITE),
    `${fence(COULDNT)}\n\n**couldn't** — modal verb + not  \n` +
      `Senior form:  \n${fence(`Junior: ${COULDNT_JUNIOR}`)}`,
  );
});

test("an x-letter form and its senior name each other", () => {
  assert.equal(
    described(EXPECT_X, READ, WRITE),
    `${fence(EXPECT_X)}\n\n**expect** — verb, infinitive  \n` +
      `X-letter form:  \n${fence(`Senior: ${EXPECT}`)}`,
  );
  assert.equal(
    described(EXPECT, READ, WRITE),
    `${fence(EXPECT)}\n\n**expect** — verb, infinitive  \n` +
      `Senior form:  \n${fence(`X-letter: ${EXPECT_X}`)}`,
  );
});

test("a §III contraction is read out and written out", () => {
  assert.equal(
    described(PERHAPS, READ, WRITE),
    `${fence(PERHAPS)}\n\n**perhaps** — adverb  \n` +
      `Senior contraction — written out:  \n${fence(PERHAPS_OUT)}`,
  );
});

test("a hyphenated compound falls back to the pieces it knows", () => {
  const both = described(`${READ_EAT}-${READ_ET}`, READ, WRITE);
  assert.ok(both);
  assert.ok(both.includes("past-tense verb"));
  assert.ok(both.includes(READ_TOLD));
  assert.equal(described(`${BAD}-${READ_EAT}`, READ, WRITE), READ_TOLD);
  assert.equal(described(`${BAD}-${BAD}`, READ, WRITE), null);
});

test("an unknown spelling stays silent", () => {
  assert.equal(described(BAD, READ, WRITE), null);
});

test("the hover attaches to the token at or just behind the position", () => {
  const text = `on ${READ_EAT}\n`;
  for (const offset of [3, 4, 6]) {
    assert.deepEqual(hovered(text, offset, READ, WRITE), {
      value: READ_TOLD,
      start: 3,
      end: 6,
    });
  }
  assert.equal(hovered(text, 1, READ, WRITE), null);
  assert.equal(hovered(text, 7, READ, WRITE), null);
});

test("no spelling in a hover renders outside a fence", () => {
  const spellings = data.words.split("\n").map((line) => line.split("\t", 1)[0]);
  let seen = 0;
  for (let at = 0; at < spellings.length; at += 97) {
    const told = described(spellings[at], READ, WRITE);
    if (!told) continue;
    seen += 1;
    assert.ok(!spelled(sifted(told, false).join("\n")), `unfenced spelling in ${spellings[at]}`);
  }
  assert.ok(seen > 500);
  const fixes = advised(suggest(misspelled(READ_EAT), advice()), READ);
  assert.ok(!spelled(sifted(fixes, false).join("\n")));
});

test("a misspelling is told its fixes, in order and glossed", () => {
  const offers = suggest(misspelled(READ_EAT), advice());
  assert.ok(offers.length > 0);
  const told = advised(offers, READ);
  assert.ok(told.startsWith("Unknown Quikscript spelling.\n\n"));
  const lines = sifted(told, true);
  assert.equal(lines.length, offers.length);
  for (const [at, fix] of offers.entries()) assert.ok(lines[at].startsWith(fix));
  assert.ok(lines.some((line) => line.includes(" — ")));
});

test("a misspelling with nothing to offer says so", () => {
  assert.equal(advised([], READ), "Unknown Quikscript spelling. No suggestions.");
});

test("a fix outside the senior column names its face", () => {
  assert.equal(glossed(COULDNT_JUNIOR, READ), "couldn't — modal verb + not (Junior)");
  assert.equal(glossed(EXPECT_X, READ), "expect — verb, infinitive (X-letter)");
  assert.equal(glossed(PERHAPS, READ), "perhaps — adverb (Senior contraction)");
});

test("a fix the lexicon does not carry whole is glossed from its pieces", () => {
  assert.equal(glossed(`${READ_EAT}-${READ_ET}`, READ), "read/reade/reed-read/red");
  assert.equal(glossed(`${READ_EAT} ${READ_ET}`, READ), "read/reade/reed read/red");
  assert.equal(glossed(`${BAD}-${READ_ET}`, READ), "read/red");
  assert.equal(glossed(BAD, READ), "");
});
