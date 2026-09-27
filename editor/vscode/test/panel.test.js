const assert = require("node:assert/strict");
const { test } = require("node:test");
const { lookupRows, resolveMessage, rows, shell } = require("../lib/panel.js");

/** @typedef {import("../lib/panel.js").DocumentFlags} DocumentFlags */
/** @typedef {import("../lib/panel.js").Flag} Flag */
/** @typedef {import("../lib/panel.js").Span} Span */

const URI = "file:///draft/letter.md";
const BAD = "\uE651\uE657\uE65A";
const GOOD = "\uE651\uE657\uE65B";
const OTHER = "\uE66A\uE657";
const NO_SUGGESTIONS = "\uE65C\uE664\uE652";
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
function suggestion(fix, gloss, range) {
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

const FIRST = span(0, 4, 7);
const SECOND = span(2, 0, 3);
const THIRD = span(5, 8, 11);
const LONE = span(3, 2, 4);
const EVERYWHERE = [FIRST, SECOND, THIRD];

/** @type {Flag[]} */
const FLAGS = [
  {
    word: BAD,
    occurrence: 0,
    range: FIRST,
    spans: EVERYWHERE,
    fixes: [suggestion(GOOD, "good", FIRST), suggestion(OTHER, "", FIRST)],
    ignore: ignored(BAD, 0, true, true),
  },
  {
    word: NO_SUGGESTIONS,
    occurrence: 0,
    range: LONE,
    spans: [LONE],
    fixes: [],
    ignore: ignored(NO_SUGGESTIONS, 0, false, false),
  },
  {
    word: BAD,
    occurrence: 1,
    range: SECOND,
    spans: EVERYWHERE,
    fixes: [suggestion(GOOD, "good", SECOND), suggestion(OTHER, "", SECOND)],
    ignore: ignored(BAD, 1, true, true),
  },
];

/** @type {DocumentFlags} */
const DOCUMENT_FLAGS = { uri: URI, flags: FLAGS };

test("each flag starts its own section, with suggestions before the ignore scopes", () => {
  const out = rows(FLAGS);
  assert.deepEqual(
    out.map((row) => row.kind),
    [
      "word",
      "suggestion",
      "suggestion",
      "ignore",
      "ignore",
      "ignore",
      "ignore",
      "word",
      "none",
      "ignore",
      "ignore",
      "word",
      "suggestion",
      "suggestion",
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
  assert.deepEqual(out[1], {
    kind: "suggestion",
    flag: 0,
    at: 0,
    fix: GOOD,
    gloss: "good",
    others: 2,
  });
  assert.deepEqual(out[2], {
    kind: "suggestion",
    flag: 0,
    at: 1,
    fix: OTHER,
    gloss: "",
    others: 2,
  });
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

test("a word with no suggestions shows a none row, and a document with no root has no project scope", () => {
  assert.deepEqual(rows([FLAGS[1]]), [
    { kind: "word", flag: 0, word: NO_SUGGESTIONS, occurrence: 0, others: 0, line: 3, character: 2 },
    { kind: "none" },
    { kind: "ignore", flag: 0, scope: "occurrence", label: "Ignore this occurrence" },
    { kind: "ignore", flag: 0, scope: "user", label: "Ignore everywhere" },
  ]);
});

test("a lone occurrence's suggestion row counts zero others", () => {
  const lone = { ...FLAGS[0], spans: [FIRST] };
  assert.deepEqual(rows([lone])[1], {
    kind: "suggestion",
    flag: 0,
    at: 0,
    fix: GOOD,
    gloss: "good",
    others: 0,
  });
});

test("a plain fix returns the suggestion's edit", () => {
  assert.deepEqual(resolveMessage(DOCUMENT_FLAGS, { type: "fix", flag: 0, at: 1, all: false }), {
    edit: { changes: { [URI]: [{ range: FIRST, newText: OTHER }] } },
  });
});

test("fix all rewrites every occurrence of the flagged word", () => {
  assert.deepEqual(resolveMessage(DOCUMENT_FLAGS, { type: "fix", flag: 2, at: 0, all: true }), {
    edit: { changes: { [URI]: EVERYWHERE.map((range) => ({ range, newText: GOOD })) } },
  });
});

test("a typed spelling rewrites the flag alone or every occurrence", () => {
  assert.deepEqual(
    resolveMessage(DOCUMENT_FLAGS, { type: "typed", flag: 2, fix: OTHER, all: false }),
    {
      edit: { changes: { [URI]: [{ range: SECOND, newText: OTHER }] } },
    },
  );
  assert.deepEqual(
    resolveMessage(DOCUMENT_FLAGS, { type: "typed", flag: 0, fix: OTHER, all: true }),
    {
      edit: { changes: { [URI]: EVERYWHERE.map((range) => ({ range, newText: OTHER })) } },
    },
  );
  assert.equal(
    resolveMessage(DOCUMENT_FLAGS, { type: "typed", flag: 0, fix: "", all: false }),
    null,
  );
  assert.equal(
    resolveMessage(DOCUMENT_FLAGS, { type: "typed", flag: 7, fix: OTHER, all: false }),
    null,
  );
});

test("each ignore scope returns the server's command", () => {
  assert.deepEqual(
    resolveMessage(DOCUMENT_FLAGS, { type: "ignore", flag: 0, scope: "occurrence" }),
    {
      command: {
        command: "quikscript.ignore.occurrence",
        arguments: [{ uri: URI, word: BAD, occurrence: 0 }],
      },
    },
  );
  assert.deepEqual(
    resolveMessage(DOCUMENT_FLAGS, { type: "ignore", flag: 0, scope: "directory" }),
    {
      command: { command: "quikscript.ignore.directory", arguments: [{ uri: URI, word: BAD }] },
    },
  );
  assert.deepEqual(resolveMessage(DOCUMENT_FLAGS, { type: "ignore", flag: 0, scope: "project" }), {
    command: { command: "quikscript.ignore.project", arguments: [{ uri: URI, word: BAD }] },
  });
  assert.deepEqual(resolveMessage(DOCUMENT_FLAGS, { type: "ignore", flag: 0, scope: "user" }), {
    command: { command: "quikscript.ignore.user", arguments: [{ word: BAD }] },
  });
  assert.equal(
    resolveMessage(DOCUMENT_FLAGS, { type: "ignore", flag: 1, scope: "directory" }),
    null,
  );
  assert.equal(resolveMessage(DOCUMENT_FLAGS, { type: "ignore", flag: 1, scope: "project" }), null);
});

test("a document in its project's root has no directory scope", () => {
  const rooted = { ...FLAGS[0], ignore: ignored(BAD, 0, false, true) };
  assert.deepEqual(rows([rooted]), [
    { kind: "word", flag: 0, word: BAD, occurrence: 0, others: 2, line: 0, character: 4 },
    { kind: "suggestion", flag: 0, at: 0, fix: GOOD, gloss: "good", others: 2 },
    { kind: "suggestion", flag: 0, at: 1, fix: OTHER, gloss: "", others: 2 },
    { kind: "ignore", flag: 0, scope: "occurrence", label: "Ignore this occurrence" },
    { kind: "ignore", flag: 0, scope: "project", label: "Ignore in this project" },
    { kind: "ignore", flag: 0, scope: "user", label: "Ignore everywhere" },
  ]);
});

test("a reveal returns the flagged range", () => {
  assert.deepEqual(resolveMessage(DOCUMENT_FLAGS, { type: "reveal", flag: 2 }), { range: SECOND });
});

test("an out-of-range flag or suggestion index returns null", () => {
  assert.equal(resolveMessage(DOCUMENT_FLAGS, { type: "reveal", flag: 9 }), null);
  assert.equal(resolveMessage(DOCUMENT_FLAGS, { type: "fix", flag: 1, at: 0, all: false }), null);
  assert.equal(resolveMessage(DOCUMENT_FLAGS, { type: "fix", flag: 0, at: 5, all: true }), null);
  assert.equal(resolveMessage(DOCUMENT_FLAGS, { type: "ignore", flag: 4, scope: "user" }), null);
});

test("a written word shows each form under its gloss, a phrase its whole line first", () => {
  const read = { latin: "read", items: [{ label: GOOD, detail: "verb" }, { label: OTHER, detail: "noun" }] };
  const this_ = { latin: "this", items: [{ label: NO_SUGGESTIONS, detail: "determiner" }] };
  const none = { latin: "zzxq", items: [] };
  assert.deepEqual(lookupRows([read]), [
    { kind: "form", fix: GOOD, gloss: "verb" },
    { kind: "form", fix: OTHER, gloss: "noun" },
  ]);
  assert.deepEqual(lookupRows([read, this_]), [
    { kind: "phrase", fix: `${GOOD} ${NO_SUGGESTIONS}` },
    { kind: "form", fix: GOOD, gloss: "read — verb" },
    { kind: "form", fix: OTHER, gloss: "read — noun" },
    { kind: "form", fix: NO_SUGGESTIONS, gloss: "this — determiner" },
  ]);
  assert.deepEqual(lookupRows([read, none]), [
    { kind: "form", fix: GOOD, gloss: "read — verb" },
    { kind: "form", fix: OTHER, gloss: "read — noun" },
    { kind: "missing", latin: "zzxq" },
  ]);
  assert.deepEqual(lookupRows([]), []);
});

test("the webview CSP allows data: fonts and the page links every stylesheet it is given", () => {
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
