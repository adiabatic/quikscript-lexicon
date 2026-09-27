const assert = require("node:assert/strict");
const { test } = require("node:test");
const data = require("../payload.json");
const { parseSpellingsByLatin } = require("../lib/lookup.js");
const { completions, latinWordAt, lookupSpellings } = require("../lib/complete.js");

const SPELLINGS_BY_LATIN = parseSpellingsByLatin(data);
const READ_EAT = "\uE668\uE671\uE653";
const READ_ET = "\uE668\uE672\uE653";
const COULDNT = "\uE654\uE67D\uE653\uE666\uE652";
const COULDNT_JUNIOR = "\uE654\uE67D\uE653\uE67A\uE666\uE652";

const READ_ITEMS = [
  { label: READ_EAT, detail: "singular noun, verb, infinitive", sortText: "0000" },
  { label: READ_ET, detail: "past-tense verb, past participle", sortText: "0001" },
];

test("a latin word completes to its spellings, most frequent first", () => {
  assert.deepEqual(completions("I will read this", 11, SPELLINGS_BY_LATIN), {
    word: "read",
    start: 7,
    end: 11,
    items: READ_ITEMS,
  });
});

test("the caret anywhere in the word completes the whole word", () => {
  for (const offset of [7, 9, 11]) {
    const found = completions("I will read this", offset, SPELLINGS_BY_LATIN);
    assert.ok(found);
    assert.deepEqual([found.word, found.start, found.end], ["read", 7, 11]);
  }
});

test("lookup ignores case and keeps the typed word for filtering", () => {
  const found = completions("Read", 4, SPELLINGS_BY_LATIN);
  assert.ok(found);
  assert.equal(found.word, "Read");
  assert.deepEqual(found.items, READ_ITEMS);
});

test("a curly apostrophe finds the straight key", () => {
  const found = completions("couldn’t", 8, SPELLINGS_BY_LATIN);
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
  const found = completions("the dogs' dinner", 8, SPELLINGS_BY_LATIN);
  assert.ok(found);
  assert.deepEqual([found.word, found.start, found.end], ["dogs", 4, 8]);
});

test("an unknown compound completes the part after its last hyphen", () => {
  const found = completions("zzq-read", 8, SPELLINGS_BY_LATIN);
  assert.ok(found);
  assert.deepEqual([found.word, found.start, found.end], ["read", 4, 8]);
  assert.deepEqual(found.items, READ_ITEMS);
});

test("a range that no longer contains the caret gets no completion", () => {
  assert.equal(completions("the dogs' dinner", 9, SPELLINGS_BY_LATIN), null);
  assert.equal(completions("zzq-read", 1, SPELLINGS_BY_LATIN), null);
  assert.equal(completions("read", 99, SPELLINGS_BY_LATIN), null);
});

test("a listed compound keeps its whole range", () => {
  const found = completions("well-read", 9, SPELLINGS_BY_LATIN);
  assert.ok(found);
  assert.deepEqual([found.word, found.start, found.end], ["well-read", 0, 9]);
  assert.equal(found.items.length, 1);
});

test("an unknown word gets no completion, and a caret outside any word finds no word", () => {
  assert.equal(completions("zzqqxx", 6, SPELLINGS_BY_LATIN), null);
  assert.equal(completions("a  b", 2, SPELLINGS_BY_LATIN), null);
  assert.equal(latinWordAt("  ", 1), null);
  assert.equal(latinWordAt("''", 1), null);
});

test("a latin phrase is written word by word, with the unknown left empty", () => {
  assert.deepEqual(lookupSpellings("Read, dogs' zzxq", SPELLINGS_BY_LATIN), [
    { latin: "read", items: READ_ITEMS },
    { latin: "dogs", items: lookupSpellings("dogs", SPELLINGS_BY_LATIN)[0].items },
    { latin: "zzxq", items: [] },
  ]);
  assert.ok(lookupSpellings("dogs", SPELLINGS_BY_LATIN)[0].items.length > 0);
  assert.deepEqual(lookupSpellings("  , - ''", SPELLINGS_BY_LATIN), []);
});

test("an unlisted hyphenation is written piece by piece", () => {
  const found = lookupSpellings("read-zzxq", SPELLINGS_BY_LATIN);
  assert.deepEqual(
    found.map((word) => [word.latin, word.items.length > 0]),
    [
      ["read", true],
      ["zzxq", false],
    ],
  );
});
