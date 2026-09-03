const assert = require("node:assert/strict");
const { test } = require("node:test");
const data = require("../payload.json");
const { lexicon } = require("../lib/lexicon.js");
const { diagnostics, flagged, lineStarts, offsetAt, spot } = require("../lib/check.js");

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
  assert.equal(WORDS.active.size, 75652);
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

test("a single letter after a namer dot is not checked", () => {
  const letter = BAD[0];
  assert.deepEqual(published(`\u00b7${letter} and \u00b7${letter}\u00b7${letter}\n`, "plaintext"), []);
  assert.equal(published(`\u00b7${BAD}\n`, "plaintext").length, 1);
});

test("an invisible mark inside a run does not end the word", () => {
  const joined = BAD.slice(0, 4) + "\u200c" + BAD.slice(4);
  const found = published(`\u201c${joined}\u201d\n`, "plaintext");
  assert.equal(found.length, 1);
  assert.deepEqual(found[0].range, {
    start: { line: 0, character: 1 },
    end: { line: 0, character: 1 + joined.length },
  });
  assert.equal(found[0].message, `Unknown Quikscript spelling: ${BAD}`);
  assert.deepEqual(published(`${GOOD.slice(0, 1)}\ufe00${GOOD.slice(1)}\n`, "plaintext"), []);
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

test("a position past the line end stays on its line", () => {
  const text = "ab\r\ncd\r\n";
  const starts = lineStarts(text);
  assert.equal(offsetAt(starts, text, { line: 0, character: 1 }), 1);
  assert.equal(offsetAt(starts, text, { line: 0, character: 99 }), 2);
  assert.equal(offsetAt(starts, text, { line: 1, character: 99 }), 6);
  assert.equal(offsetAt(starts, text, { line: 9, character: 0 }), text.length);
});

test("a pathological document is capped at five hundred diagnostics", () => {
  const text = `${BAD}\n`.repeat(501);
  assert.equal(published(text, "plaintext").length, 500);
});
