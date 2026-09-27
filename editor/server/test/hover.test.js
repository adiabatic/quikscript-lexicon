const assert = require("node:assert/strict");
const { test } = require("node:test");
const data = require("../payload.json");
const { lexicon } = require("../lib/lexicon.js");
const { parseLatinBySpelling, parseSpellingsByLatin } = require("../lib/lookup.js");
const { glossed, hoverAt, hoverMarkdown, listed } = require("../lib/hover.js");
const { accepts, suggest } = require("../../../src/qslex/web/core.js");

const LATIN_BY_SPELLING = parseLatinBySpelling(data);
const SPELLINGS_BY_LATIN = parseSpellingsByLatin(data);
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
function linesByFence(value, within) {
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
function hasQuikscript(value) {
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

function suggestContext() {
  return {
    active: WORDS.active,
    freq: WORDS.counts,
    groups: WORDS.groups,
    letters: WORDS.letters,
    rep: WORDS.rep,
  };
}

const READ_HOVER =
  `${fence(READ_EAT)}\n\n` +
  "**read** — singular noun, verb, infinitive\n\n" +
  "**reade** — proper noun\n\n" +
  "**reed** — singular noun";

test("a spelling's hover lists every word it spells", () => {
  assert.equal(hoverMarkdown(READ_EAT, LATIN_BY_SPELLING, SPELLINGS_BY_LATIN), READ_HOVER);
});

test("the other spelling of a heteronym lists only its own senses", () => {
  assert.equal(
    hoverMarkdown(READ_ET, LATIN_BY_SPELLING, SPELLINGS_BY_LATIN),
    `${fence(READ_ET)}\n\n` +
      "**read** — past-tense verb, past participle\n\n" +
      "**red** — adjective, singular noun",
  );
});

test("the hovers of a junior form and its senior form list each other", () => {
  assert.equal(
    hoverMarkdown(COULDNT_JUNIOR, LATIN_BY_SPELLING, SPELLINGS_BY_LATIN),
    `${fence(COULDNT_JUNIOR)}\n\n**couldn't** — modal verb + not  \n` +
      `Junior form:  \n${fence(`Senior: ${COULDNT}`)}`,
  );
  assert.equal(
    hoverMarkdown(COULDNT, LATIN_BY_SPELLING, SPELLINGS_BY_LATIN),
    `${fence(COULDNT)}\n\n**couldn't** — modal verb + not  \n` +
      `Senior form:  \n${fence(`Junior: ${COULDNT_JUNIOR}`)}`,
  );
});

test("the hovers of an X-letter form and its senior form list each other", () => {
  assert.equal(
    hoverMarkdown(EXPECT_X, LATIN_BY_SPELLING, SPELLINGS_BY_LATIN),
    `${fence(EXPECT_X)}\n\n**expect** — verb, infinitive  \n` +
      `X-letter form:  \n${fence(`Senior: ${EXPECT}`)}`,
  );
  assert.equal(
    hoverMarkdown(EXPECT, LATIN_BY_SPELLING, SPELLINGS_BY_LATIN),
    `${fence(EXPECT)}\n\n**expect** — verb, infinitive  \n` +
      `Senior form:  \n${fence(`X-letter: ${EXPECT_X}`)}`,
  );
});

test("a §III contraction's hover shows the word and its full spelling", () => {
  assert.equal(
    hoverMarkdown(PERHAPS, LATIN_BY_SPELLING, SPELLINGS_BY_LATIN),
    `${fence(PERHAPS)}\n\n**perhaps** — adverb  \n` +
      `Senior contraction — written out:  \n${fence(PERHAPS_OUT)}`,
  );
});

test("a hyphenated compound's hover shows each piece the lexicon lists", () => {
  const both = hoverMarkdown(`${READ_EAT}-${READ_ET}`, LATIN_BY_SPELLING, SPELLINGS_BY_LATIN);
  assert.ok(both);
  assert.ok(both.includes("past-tense verb"));
  assert.ok(both.includes(READ_HOVER));
  assert.equal(
    hoverMarkdown(`${BAD}-${READ_EAT}`, LATIN_BY_SPELLING, SPELLINGS_BY_LATIN),
    READ_HOVER,
  );
  assert.equal(hoverMarkdown(`${BAD}-${BAD}`, LATIN_BY_SPELLING, SPELLINGS_BY_LATIN), null);
});

test("an unknown spelling has no hover", () => {
  assert.equal(hoverMarkdown(BAD, LATIN_BY_SPELLING, SPELLINGS_BY_LATIN), null);
});

test("hoverAt finds the token that contains the position or ends at it", () => {
  const text = `on ${READ_EAT}\n`;
  for (const offset of [3, 4, 6]) {
    assert.deepEqual(hoverAt(text, offset, LATIN_BY_SPELLING, SPELLINGS_BY_LATIN), {
      value: READ_HOVER,
      start: 3,
      end: 6,
    });
  }
  assert.equal(hoverAt(text, 1, LATIN_BY_SPELLING, SPELLINGS_BY_LATIN), null);
  assert.equal(hoverAt(text, 7, LATIN_BY_SPELLING, SPELLINGS_BY_LATIN), null);
});

test("no spelling in a hover renders outside a fence", () => {
  const spellings = data.words.split("\n").map((line) => line.split("\t", 1)[0]);
  let seen = 0;
  for (let at = 0; at < spellings.length; at += 97) {
    const hoverText = hoverMarkdown(spellings[at], LATIN_BY_SPELLING, SPELLINGS_BY_LATIN);
    if (!hoverText) continue;
    seen += 1;
    assert.ok(
      !hasQuikscript(linesByFence(hoverText, false).join("\n")),
      `unfenced spelling in ${spellings[at]}`,
    );
  }
  assert.ok(seen > 500);
});

test("suggestions are listed in the order suggest() returns, each glossed", () => {
  const suggestions = suggest(misspelled(READ_EAT), suggestContext());
  assert.ok(suggestions.length > 0);
  const lines = listed(suggestions, LATIN_BY_SPELLING);
  assert.equal(lines.length, suggestions.length);
  for (const [at, suggestion] of suggestions.entries()) assert.ok(lines[at].startsWith(suggestion));
  assert.ok(lines.some((line) => line.includes(" — ")));
});

test("a misspelling with no suggestions lists none", () => {
  assert.deepEqual(listed([], LATIN_BY_SPELLING), []);
});

test("a suggestion outside the senior column names its column", () => {
  assert.equal(
    glossed(COULDNT_JUNIOR, LATIN_BY_SPELLING),
    "couldn't — modal verb + not (Junior)",
  );
  assert.equal(glossed(EXPECT_X, LATIN_BY_SPELLING), "expect — verb, infinitive (X-letter)");
  assert.equal(glossed(PERHAPS, LATIN_BY_SPELLING), "perhaps — adverb (Senior contraction)");
});

test("a suggestion the lexicon does not list is glossed from its pieces", () => {
  assert.equal(glossed(`${READ_EAT}-${READ_ET}`, LATIN_BY_SPELLING), "read/reade/reed-read/red");
  assert.equal(glossed(`${READ_EAT} ${READ_ET}`, LATIN_BY_SPELLING), "read/reade/reed read/red");
  assert.equal(glossed(`${BAD}-${READ_ET}`, LATIN_BY_SPELLING), "read/red");
  assert.equal(glossed(BAD, LATIN_BY_SPELLING), "");
});
