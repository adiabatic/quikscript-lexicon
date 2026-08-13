const assert = require("node:assert/strict");
const { test } = require("node:test");
const data = require("../payload.json");
const { lexicon } = require("../lib/lexicon.js");
const { diagnostics } = require("../lib/check.js");

const WORDS = lexicon(data);
const GOOD = data.words.split("\n", 1)[0].split("\t", 1)[0];
const BAD = "\uE650".repeat(9);

test("the fixtures hold: one word the lexicon spells, one it does not", () => {
  assert.equal(WORDS.active.size, 75651);
  assert.ok(WORDS.active.has(GOOD));
  assert.ok(!WORDS.active.has(BAD));
});

test("a clean document publishes nothing", () => {
  assert.deepEqual(diagnostics("", "plaintext", WORDS.active), []);
  assert.deepEqual(diagnostics(`latin and ${GOOD}\n`, "plaintext", WORDS.active), []);
  assert.deepEqual(diagnostics(`${GOOD}-${GOOD}\n`, "plaintext", WORDS.active), []);
});

test("an unknown spelling is flagged over its full range", () => {
  const found = diagnostics(`one ${BAD} two\n`, "plaintext", WORDS.active);
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
  const found = diagnostics(`${GOOD}\nab ${BAD}\n`, "plaintext", WORDS.active);
  assert.equal(found.length, 1);
  assert.deepEqual(found[0].range.start, { line: 1, character: 3 });
});

test("every line ending style delimits lines", () => {
  for (const ending of ["\n", "\r", "\r\n"]) {
    const found = diagnostics(
      `${GOOD}${ending}${ending}${BAD}${ending}`,
      "plaintext",
      WORDS.active,
    );
    assert.equal(found.length, 1);
    assert.deepEqual(found[0].range.start, { line: 2, character: 0 });
  }
});

test("markdown skips front matter, fences, and code spans", () => {
  const text = `---\nqs: ${BAD}\n---\n\n${GOOD} ${BAD}\n\n\`${BAD}\`\n\n\`\`\`\n${BAD}\n\`\`\`\n`;
  const found = diagnostics(text, "markdown", WORDS.active);
  assert.equal(found.length, 1);
  assert.deepEqual(found[0].range.start, { line: 4, character: GOOD.length + 1 });
});

test("any other language id is checked as plain text", () => {
  const text = `\`${BAD}\`\n`;
  for (const languageId of ["plaintext", "latex", "org", ""]) {
    assert.equal(diagnostics(text, languageId, WORDS.active).length, 1);
  }
  assert.equal(diagnostics(text, "markdown", WORDS.active).length, 0);
  assert.equal(diagnostics(text, "Markdown", WORDS.active).length, 0);
});

test("a pathological document is capped at five hundred diagnostics", () => {
  const text = `${BAD}\n`.repeat(501);
  assert.equal(diagnostics(text, "plaintext", WORDS.active).length, 500);
});
