const assert = require("node:assert/strict");
const { test } = require("node:test");
const data = require("../payload.json");
const { writings } = require("../lib/lookup.js");
const { completions, worded, written } = require("../lib/complete.js");

const WRITE = writings(data);
const READ_EAT = "\uE668\uE671\uE653";
const READ_ET = "\uE668\uE672\uE653";
const COULDNT = "\uE654\uE67D\uE653\uE666\uE652";
const COULDNT_JUNIOR = "\uE654\uE67D\uE653\uE67A\uE666\uE652";

const READ_ITEMS = [
  { label: READ_EAT, detail: "singular noun, verb, infinitive", sortText: "0000" },
  { label: READ_ET, detail: "past-tense verb, past participle", sortText: "0001" },
];

test("a latin word completes to its spellings, commonest first", () => {
  assert.deepEqual(completions("I will read this", 11, WRITE), {
    word: "read",
    start: 7,
    end: 11,
    items: READ_ITEMS,
  });
});

test("the caret anywhere in the word completes the whole word", () => {
  for (const offset of [7, 9, 11]) {
    const found = completions("I will read this", offset, WRITE);
    assert.ok(found);
    assert.deepEqual([found.word, found.start, found.end], ["read", 7, 11]);
  }
});

test("capitalization is looked through and kept for filtering", () => {
  const found = completions("Read", 4, WRITE);
  assert.ok(found);
  assert.equal(found.word, "Read");
  assert.deepEqual(found.items, READ_ITEMS);
});

test("a curly apostrophe finds the straight key", () => {
  const found = completions("couldn’t", 8, WRITE);
  assert.ok(found);
  assert.equal(found.word, "couldn’t");
  assert.deepEqual(found.items, [
    { label: COULDNT, detail: "modal verb + not", sortText: "0000" },
    {
      label: COULDNT_JUNIOR,
      detail: "modal verb + not — Junior form",
      sortText: "0001",
    },
  ]);
});

test("a trailing apostrophe is left out of the word", () => {
  const found = completions("the dogs' dinner", 8, WRITE);
  assert.ok(found);
  assert.deepEqual([found.word, found.start, found.end], ["dogs", 4, 8]);
});

test("an unknown compound falls back past its hyphens", () => {
  const found = completions("zzq-read", 8, WRITE);
  assert.ok(found);
  assert.deepEqual([found.word, found.start, found.end], ["read", 4, 8]);
  assert.deepEqual(found.items, READ_ITEMS);
});

test("a range that no longer holds the caret is never offered", () => {
  assert.equal(completions("the dogs' dinner", 9, WRITE), null);
  assert.equal(completions("zzq-read", 1, WRITE), null);
  assert.equal(completions("read", 99, WRITE), null);
});

test("a listed compound keeps its whole range", () => {
  const found = completions("well-read", 9, WRITE);
  assert.ok(found);
  assert.deepEqual([found.word, found.start, found.end], ["well-read", 0, 9]);
  assert.equal(found.items.length, 1);
});

test("no word, no answer", () => {
  assert.equal(completions("zzqqxx", 6, WRITE), null);
  assert.equal(completions("a  b", 2, WRITE), null);
  assert.equal(worded("  ", 1), null);
  assert.equal(worded("''", 1), null);
});

test("a latin phrase is written word by word, with the unknown left empty", () => {
  assert.deepEqual(written("Read, dogs' zzxq", WRITE), [
    { latin: "read", items: READ_ITEMS },
    { latin: "dogs", items: written("dogs", WRITE)[0].items },
    { latin: "zzxq", items: [] },
  ]);
  assert.ok(written("dogs", WRITE)[0].items.length > 0);
  assert.deepEqual(written("  , - ''", WRITE), []);
});

test("an unlisted hyphenation is written piece by piece", () => {
  const found = written("read-zzxq", WRITE);
  assert.deepEqual(
    found.map((word) => [word.latin, word.items.length > 0]),
    [
      ["read", true],
      ["zzxq", false],
    ],
  );
});
