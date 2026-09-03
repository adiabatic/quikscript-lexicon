const assert = require("node:assert/strict");
const { test } = require("node:test");
const { resolved, rows, shell, shown } = require("../lib/panel.js");

/** @typedef {import("../lib/panel.js").Fixed} Fixed */
/** @typedef {import("../lib/panel.js").Held} Held */
/** @typedef {import("../lib/panel.js").Span} Span */

const URI = "file:///draft/letter.md";
const BAD = "\uE651\uE657\uE65A";
const GOOD = "\uE651\uE657\uE65B";
const OTHER = "\uE66A\uE657";
const MUTE = "\uE65C\uE664\uE652";
const CSP = "vscode-webview://host";

/**
 * @param {number} line
 * @param {number} from
 * @param {number} to
 * @returns {Span}
 */
function span(line, from, to) {
  return { start: { line, character: from }, end: { line, character: to } };
}

/**
 * @param {string} fix
 * @param {string} gloss
 * @param {Span} range
 */
function offered(fix, gloss, range) {
  return { fix, gloss, edit: { changes: { [URI]: [{ range, newText: fix }] } } };
}

/**
 * @param {string} word
 * @param {number} occurrence
 * @param {boolean} directory
 * @param {boolean} project
 */
function ignored(word, occurrence, directory, project) {
  return {
    occurrence: {
      command: "quikscript.ignore.occurrence",
      arguments: [{ uri: URI, word, occurrence }],
    },
    directory: directory
      ? { command: "quikscript.ignore.directory", arguments: [{ uri: URI, word }] }
      : null,
    project: project
      ? { command: "quikscript.ignore.project", arguments: [{ uri: URI, word }] }
      : null,
    user: { command: "quikscript.ignore.user", arguments: [{ word }] },
  };
}

const HERE = span(0, 4, 7);
const AGAIN = span(2, 0, 3);
const THIRD = span(5, 8, 11);
const LONE = span(3, 2, 4);
const EVERYWHERE = [HERE, AGAIN, THIRD];

/** @type {Fixed[]} */
const FLAGS = [
  {
    word: BAD,
    occurrence: 0,
    range: HERE,
    spans: EVERYWHERE,
    fixes: [offered(GOOD, "good", HERE), offered(OTHER, "", HERE)],
    ignore: ignored(BAD, 0, true, true),
  },
  {
    word: MUTE,
    occurrence: 0,
    range: LONE,
    spans: [LONE],
    fixes: [],
    ignore: ignored(MUTE, 0, false, false),
  },
  {
    word: BAD,
    occurrence: 1,
    range: AGAIN,
    spans: EVERYWHERE,
    fixes: [offered(GOOD, "good", AGAIN), offered(OTHER, "", AGAIN)],
    ignore: ignored(BAD, 1, true, true),
  },
];

/** @type {Held} */
const HELD = { uri: URI, flags: FLAGS };

test("each flag heads its own card, its offers ahead of the ignore tiers", () => {
  const out = rows(FLAGS);
  assert.deepEqual(
    out.map((row) => row.kind),
    [
      "word",
      "offer",
      "offer",
      "ignore",
      "ignore",
      "ignore",
      "ignore",
      "word",
      "none",
      "ignore",
      "ignore",
      "word",
      "offer",
      "offer",
      "ignore",
      "ignore",
      "ignore",
      "ignore",
    ],
  );
  assert.deepEqual(out[0], {
    kind: "word",
    flag: 0,
    word: BAD,
    occurrence: 0,
    others: 2,
    line: 0,
    character: 4,
  });
  assert.deepEqual(out[1], { kind: "offer", flag: 0, at: 0, fix: GOOD, gloss: "good", others: 2 });
  assert.deepEqual(out[2], { kind: "offer", flag: 0, at: 1, fix: OTHER, gloss: "", others: 2 });
  assert.deepEqual(out[11], {
    kind: "word",
    flag: 2,
    word: BAD,
    occurrence: 1,
    others: 2,
    line: 2,
    character: 0,
  });
});

test("a word with nothing to offer says none, and a rootless document has no project tier", () => {
  assert.deepEqual(rows([FLAGS[1]]), [
    { kind: "word", flag: 0, word: MUTE, occurrence: 0, others: 0, line: 3, character: 2 },
    { kind: "none" },
    { kind: "ignore", flag: 0, tier: "occurrence", label: "Ignore this occurrence" },
    { kind: "ignore", flag: 0, tier: "user", label: "Ignore everywhere" },
  ]);
});

test("a lone occurrence leaves no others to sweep", () => {
  const lone = { ...FLAGS[0], spans: [HERE] };
  assert.deepEqual(rows([lone])[1], {
    kind: "offer",
    flag: 0,
    at: 0,
    fix: GOOD,
    gloss: "good",
    others: 0,
  });
});

test("a plain fix hands back the offer's own edit", () => {
  assert.deepEqual(resolved(HELD, { type: "fix", flag: 0, at: 1, sweep: false }), {
    edit: { changes: { [URI]: [{ range: HERE, newText: OTHER }] } },
  });
});

test("a sweep rewrites every occurrence the flag knows of", () => {
  assert.deepEqual(resolved(HELD, { type: "fix", flag: 2, at: 0, sweep: true }), {
    edit: { changes: { [URI]: EVERYWHERE.map((range) => ({ range, newText: GOOD })) } },
  });
});

test("a typed spelling rewrites the flag alone or every occurrence", () => {
  assert.deepEqual(resolved(HELD, { type: "typed", flag: 2, fix: OTHER, sweep: false }), {
    edit: { changes: { [URI]: [{ range: AGAIN, newText: OTHER }] } },
  });
  assert.deepEqual(resolved(HELD, { type: "typed", flag: 0, fix: OTHER, sweep: true }), {
    edit: { changes: { [URI]: EVERYWHERE.map((range) => ({ range, newText: OTHER })) } },
  });
  assert.equal(resolved(HELD, { type: "typed", flag: 0, fix: "", sweep: false }), null);
  assert.equal(resolved(HELD, { type: "typed", flag: 7, fix: OTHER, sweep: false }), null);
});

test("each ignore tier hands back the server's own command", () => {
  assert.deepEqual(resolved(HELD, { type: "ignore", flag: 0, tier: "occurrence" }), {
    order: {
      command: "quikscript.ignore.occurrence",
      arguments: [{ uri: URI, word: BAD, occurrence: 0 }],
    },
  });
  assert.deepEqual(resolved(HELD, { type: "ignore", flag: 0, tier: "directory" }), {
    order: { command: "quikscript.ignore.directory", arguments: [{ uri: URI, word: BAD }] },
  });
  assert.deepEqual(resolved(HELD, { type: "ignore", flag: 0, tier: "project" }), {
    order: { command: "quikscript.ignore.project", arguments: [{ uri: URI, word: BAD }] },
  });
  assert.deepEqual(resolved(HELD, { type: "ignore", flag: 0, tier: "user" }), {
    order: { command: "quikscript.ignore.user", arguments: [{ word: BAD }] },
  });
  assert.equal(resolved(HELD, { type: "ignore", flag: 1, tier: "directory" }), null);
  assert.equal(resolved(HELD, { type: "ignore", flag: 1, tier: "project" }), null);
});

test("a document in its project's root has no directory tier", () => {
  const rooted = { ...FLAGS[0], ignore: ignored(BAD, 0, false, true) };
  assert.deepEqual(rows([rooted]), [
    { kind: "word", flag: 0, word: BAD, occurrence: 0, others: 2, line: 0, character: 4 },
    { kind: "offer", flag: 0, at: 0, fix: GOOD, gloss: "good", others: 2 },
    { kind: "offer", flag: 0, at: 1, fix: OTHER, gloss: "", others: 2 },
    { kind: "ignore", flag: 0, tier: "occurrence", label: "Ignore this occurrence" },
    { kind: "ignore", flag: 0, tier: "project", label: "Ignore in this project" },
    { kind: "ignore", flag: 0, tier: "user", label: "Ignore everywhere" },
  ]);
});

test("a reveal answers with the flagged range", () => {
  assert.deepEqual(resolved(HELD, { type: "reveal", flag: 2 }), { range: AGAIN });
});

test("a stale flag or a vanished offer answers nothing", () => {
  assert.equal(resolved(HELD, { type: "reveal", flag: 9 }), null);
  assert.equal(resolved(HELD, { type: "fix", flag: 1, at: 0, sweep: false }), null);
  assert.equal(resolved(HELD, { type: "fix", flag: 0, at: 5, sweep: true }), null);
  assert.equal(resolved(HELD, { type: "ignore", flag: 4, tier: "user" }), null);
});

test("a written word shows each form under its gloss, a phrase its whole line first", () => {
  const read = { latin: "read", items: [{ label: GOOD, detail: "verb" }, { label: OTHER, detail: "noun" }] };
  const this_ = { latin: "this", items: [{ label: MUTE, detail: "determiner" }] };
  const none = { latin: "zzxq", items: [] };
  assert.deepEqual(shown([read]), [
    { kind: "form", fix: GOOD, gloss: "verb" },
    { kind: "form", fix: OTHER, gloss: "noun" },
  ]);
  assert.deepEqual(shown([read, this_]), [
    { kind: "phrase", fix: `${GOOD} ${MUTE}` },
    { kind: "form", fix: GOOD, gloss: "read — verb" },
    { kind: "form", fix: OTHER, gloss: "read — noun" },
    { kind: "form", fix: MUTE, gloss: "this — determiner" },
  ]);
  assert.deepEqual(shown([read, none]), [
    { kind: "form", fix: GOOD, gloss: "read — verb" },
    { kind: "form", fix: OTHER, gloss: "read — noun" },
    { kind: "missing", latin: "zzxq" },
  ]);
  assert.deepEqual(shown([]), []);
});

test("the shell lets fonts in as data and names every file it was handed", () => {
  const html = shell({ csp: CSP, styles: ["one.css", "two.css"], script: "panel.js" });
  assert.match(html, /^<!doctype html>\n/);
  assert.ok(html.includes('<meta charset="utf-8">'));
  assert.ok(
    html.includes(
      `content="default-src 'none'; font-src ${CSP} data:; style-src ${CSP}; script-src ${CSP};"`,
    ),
  );
  assert.ok(html.includes('<link rel="stylesheet" href="one.css">'));
  assert.ok(html.includes('<link rel="stylesheet" href="two.css">'));
  assert.ok(html.indexOf("one.css") < html.indexOf("two.css"));
  assert.ok(html.includes("<main></main>"));
  assert.ok(html.includes('<script src="panel.js"></script>'));
});
