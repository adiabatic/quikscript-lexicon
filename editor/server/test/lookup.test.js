const assert = require("node:assert/strict");
const { test } = require("node:test");
const data = require("../payload.json");
const {
  label,
  parseLatinBySpelling,
  parseSpellingsByLatin,
  spellingIn,
} = require("../lib/lookup.js");

const LATIN_BY_SPELLING = parseLatinBySpelling(data);
const SPELLINGS_BY_LATIN = parseSpellingsByLatin(data);

test("latinBySpelling has one key per union spelling and spellingsByLatin one per latin word", () => {
  assert.equal(LATIN_BY_SPELLING.size, data.words.split("\n").length);
  assert.equal(SPELLINGS_BY_LATIN.size, 77561);
});

test("a latin entry lists its row and the column the spelling is in", () => {
  const entries = LATIN_BY_SPELLING.get("\uE668\uE671\uE653");
  assert.deepEqual(entries, [
    { latin: "read", pos: "NN1", column: "senior" },
    { latin: "read", pos: "VVB", column: "senior" },
    { latin: "read", pos: "VVI", column: "senior" },
    { latin: "reade", pos: "NP0", column: "senior" },
    { latin: "reed", pos: "NN1", column: "senior" },
  ]);
});

test("a spelling entry has its tag, frequency and three columns", () => {
  const rows = SPELLINGS_BY_LATIN.get("couldn't");
  assert.deepEqual(rows, [
    {
      pos: "VM0+XX0",
      frequency: 0,
      senior: "\uE654\uE67D\uE653\uE666\uE652",
      junior: "\uE654\uE67D\uE653\uE67A\uE666\uE652",
      x: "",
    },
  ]);
  assert.equal(spellingIn(rows[0], "senior"), rows[0].senior);
  assert.equal(spellingIn(rows[0], "junior"), rows[0].junior);
  assert.equal(spellingIn(rows[0], "x"), "");
});

test("labels name the obvious tags and pass the rest through raw", () => {
  assert.equal(label("NN1"), "singular noun");
  assert.equal(label("ITJ"), "interjection");
  assert.equal(label("VVD"), "past-tense verb");
  assert.equal(label("VM0+XX0"), "modal verb + not");
  assert.equal(label("PRE"), "PRE");
  assert.equal(label("UNC"), "UNC");
});
