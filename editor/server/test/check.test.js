const assert = require("node:assert/strict");
const { test } = require("node:test");
const data = require("../payload.json");
const { lexicon } = require("../lib/lexicon.js");
const { diagnostics, flagged, spot } = require("../lib/check.js");

const WORDS = lexicon(data);
const GOOD = data.words.split("\n", 1)[0].split("\t", 1)[0];
const BAD = "\uE650".repeat(9);
const WORSE = "\uE651".repeat(9);

/**
 * @param {string} text
 * @param {string} languageId
 * @param {Set<string>} [excused]
 * @param {Set<string>} [overlooked]
 */
function published(text, languageId, excused, overlooked) {
  return diagnostics(text, flagged(text, languageId, WORDS.active, excused, overlooked));
}

test("the fixtures hold: one word the lexicon spells, two it does not", () => {
  assert.equal(WORDS.active.size, 75651);
  assert.ok(WORDS.active.has(GOOD));
  assert.ok(!WORDS.active.has(BAD));
  assert.ok(!WORDS.active.has(WORSE));
});

test("a clean document publishes nothing", () => {
  assert.deepEqual(published("", "plaintext"), []);
  assert.deepEqual(published(`latin and ${GOOD}\n`, "plaintext"), []);
  assert.deepEqual(published(`${GOOD}-${GOOD}\n`, "plaintext"), []);
});

test("an unknown spelling is flagged over its full range", () => {
  const found = published(`one ${BAD} two\n`, "plaintext");
  assert.deepEqual(found, [
    {
      range: {
        start: { line: 0, character: 4 },
        end: { line: 0, character: 4 + BAD.length },
      },
      severity: 3,
      source: "quikscript",
      code: "unknown-word",
      message: `Unknown Quikscript spelling: ${BAD}`,
    },
  ]);
});

test("positions are utf-16 line and character offsets", () => {
  const found = published(`${GOOD}\nab ${BAD}\n`, "plaintext");
  assert.equal(found.length, 1);
  assert.deepEqual(found[0].range.start, { line: 1, character: 3 });
});

test("every line ending style delimits lines", () => {
  for (const ending of ["\n", "\r", "\r\n"]) {
    const found = published(`${GOOD}${ending}${ending}${BAD}${ending}`, "plaintext");
    assert.equal(found.length, 1);
    assert.deepEqual(found[0].range.start, { line: 2, character: 0 });
  }
});

test("markdown skips front matter, fences, and code spans", () => {
  const text = `---\nqs: ${BAD}\n---\n\n${GOOD} ${BAD}\n\n\`${BAD}\`\n\n\`\`\`\n${BAD}\n\`\`\`\n`;
  const found = published(text, "markdown");
  assert.equal(found.length, 1);
  assert.deepEqual(found[0].range.start, { line: 4, character: GOOD.length + 1 });
});

test("any other language id is checked as plain text", () => {
  const text = `\`${BAD}\`\n`;
  for (const languageId of ["plaintext", "latex", "org", ""]) {
    assert.equal(published(text, languageId).length, 1);
  }
  assert.equal(published(text, "markdown").length, 0);
  assert.equal(published(text, "Markdown").length, 0);
});

test("occurrences are numbered per word across the whole document", () => {
  const hits = flagged(`${BAD} ${GOOD} ${BAD}\n${WORSE} ${BAD}\n`, "plaintext", WORDS.active);
  assert.deepEqual(
    hits.map((hit) => [hit.word, hit.occurrence]),
    [
      [BAD, 0],
      [BAD, 1],
      [WORSE, 0],
      [BAD, 2],
    ],
  );
});

test("an excused spelling is passed over by exact match alone", () => {
  const excused = new Set([BAD]);
  assert.equal(flagged(`${BAD} ${WORSE}\n`, "plaintext", WORDS.active, excused).length, 1);
  assert.equal(flagged(`${BAD}-${BAD}\n`, "plaintext", WORDS.active, excused).length, 1);
});

test("a session ignore is keyed to one occurrence and survives unrelated edits", () => {
  const overlooked = new Set([spot(BAD, 1)]);
  const before = flagged(`${BAD} ${BAD}\n`, "plaintext", WORDS.active, new Set(), overlooked);
  assert.deepEqual(
    before.map((hit) => hit.occurrence),
    [0],
  );
  const after = flagged(
    `${GOOD} ${BAD} ${WORSE} ${BAD}\n`,
    "plaintext",
    WORDS.active,
    new Set(),
    overlooked,
  );
  assert.deepEqual(
    after.map((hit) => [hit.word, hit.occurrence]),
    [
      [BAD, 0],
      [WORSE, 0],
    ],
  );
});

test("a pathological document is capped at five hundred diagnostics", () => {
  const text = `${BAD}\n`.repeat(501);
  assert.equal(published(text, "plaintext").length, 500);
});
