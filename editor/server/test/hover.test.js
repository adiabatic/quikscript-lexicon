const assert = require("node:assert/strict");
const { test } = require("node:test");
const data = require("../payload.json");
const { readings, writings } = require("../lib/lookup.js");
const { described, hovered } = require("../lib/hover.js");

const READ = readings(data);
const WRITE = writings(data);
const READ_EAT = "\uE668\uE671\uE653";
const READ_ET = "\uE668\uE672\uE653";
const COULDNT = "\uE654\uE67D\uE653\uE666\uE652";
const COULDNT_JUNIOR = "\uE654\uE67D\uE653\uE67A\uE666\uE652";
const EXPECT = "\uE670\uE654\uE65A\uE650\uE672\uE654\uE652";
const EXPECT_X = "\uE672\uE66B\uE650\uE672\uE654\uE652";
const PERHAPS = "\uE650\uE650\uE65A";
const BAD = "\uE650".repeat(9);

const READ_TOLD =
  `${READ_EAT}\n\n` +
  "**read** — singular noun, verb, infinitive\n\n" +
  "**reade** — proper noun\n\n" +
  "**reed** — singular noun";

test("a spelling names every word it writes", () => {
  assert.equal(described(READ_EAT, READ, WRITE), READ_TOLD);
});

test("a heteronym's other face reads apart", () => {
  assert.equal(
    described(READ_ET, READ, WRITE),
    `${READ_ET}\n\n` +
      "**read** — past-tense verb, past participle\n\n" +
      "**red** — adjective, singular noun",
  );
});

test("a junior form and its senior name each other", () => {
  assert.equal(
    described(COULDNT_JUNIOR, READ, WRITE),
    `${COULDNT_JUNIOR}\n\n**couldn't** — modal verb + not  \nJunior form — Senior: ${COULDNT}`,
  );
  assert.equal(
    described(COULDNT, READ, WRITE),
    `${COULDNT}\n\n**couldn't** — modal verb + not  \nSenior form — Junior: ${COULDNT_JUNIOR}`,
  );
});

test("an x-letter form and its senior name each other", () => {
  assert.equal(
    described(EXPECT_X, READ, WRITE),
    `${EXPECT_X}\n\n**expect** — verb, infinitive  \nX-letter form — Senior: ${EXPECT}`,
  );
  assert.equal(
    described(EXPECT, READ, WRITE),
    `${EXPECT}\n\n**expect** — verb, infinitive  \nSenior form — X-letter: ${EXPECT_X}`,
  );
});

test("a §III contraction is read out and written out", () => {
  assert.equal(
    described(PERHAPS, READ, WRITE),
    `${PERHAPS}\n\n**perhaps** — adverb  \nSenior contraction — written out ` +
      "\uE650\uE67A\uE668\uE662\uE674\uE650\uE65A",
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
