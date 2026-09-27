const assert = require("node:assert/strict");
const { test, before, after } = require("node:test");
const { spawn } = require("node:child_process");
const {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  readdirSync,
  rmSync,
  statSync,
} = require("node:fs");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { bundle } = require("../bundle.js");
const data = require("../payload.json");
const { lexicon } = require("../lib/lexicon.js");
const { parseLatinBySpelling } = require("../lib/lookup.js");
const { glossed } = require("../lib/hover.js");
const core = require("../../../src/qslex/web/core.js");

const WORDS = lexicon(data);
const GOOD = data.words.split("\n", 1)[0].split("\t", 1)[0];
const BAD = "\uE650".repeat(9);
const PUBLISHED = "textDocument/publishDiagnostics";
const INLINE = { textDocument: { publishDiagnostics: { codeActionsInline: 1 } } };
const READ_EAT = "\uE668\uE671\uE653";
const READ_ET = "\uE668\uE672\uE653";
const READ_HOVER =
  "```plaintext\n" +
  `${READ_EAT}\n` +
  "```\n\n" +
  "**read** \u2014 singular noun, verb, infinitive\n\n" +
  "**reade** \u2014 proper noun\n\n" +
  "**reed** \u2014 singular noun";

const ROOT = path.join(__dirname, "..", "..", "..");
let scratch = "";
let target = "";
/** @type {Client[]} */
const spawned = [];

/** @param {string} seed */
function misspelled(seed) {
  for (let code = 0xe650; code <= 0xe66c; code += 1) {
    const word = seed + String.fromCharCode(code);
    if (!core.accepts(WORDS.active, word)) return word;
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

/** @param {string} word */
function unknownMessage(word) {
  return `Unknown Quikscript spelling: ${word}`;
}

/** @param {any[]} flags */
function firstMessageLines(flags) {
  return flags.map((flag) => flag.message.split("\n", 1)[0]);
}

/** @param {any[]} actions */
function titles(actions) {
  return actions.map((action) => action.title);
}

class Client {
  /** @param {string} launched */
  constructor(launched) {
    this.child = spawn(process.execPath, [launched, "--stdio"], {
      env: { ...process.env, XDG_CONFIG_HOME: path.join(scratch, "xdg") },
    });
    this.leftover = Buffer.alloc(0);
    /** @type {any[]} */
    this.inbox = [];
    /** @type {{match: (message: any) => boolean, resolve: (message: any) => void}[]} */
    this.waiting = [];
    this.stderr = "";
    this.id = 0;
    /** @type {Promise<number | null>} */
    this.exited = new Promise((resolve) => {
      this.child.on("exit", (code) => resolve(code));
    });
    this.child.stdin.on("error", () => {});
    this.child.stdout.on("data", (chunk) => this.feed(chunk));
    this.child.stderr.on("data", (chunk) => {
      this.stderr += chunk.toString("utf8");
    });
    spawned.push(this);
  }

  /** @param {Buffer} chunk */
  feed(chunk) {
    this.leftover = Buffer.concat([this.leftover, chunk]);
    for (;;) {
      const headerEnd = this.leftover.indexOf("\r\n\r\n");
      if (headerEnd < 0) return;
      const headers = this.leftover.subarray(0, headerEnd).toString("ascii");
      const counted = headers.match(/Content-Length: (\d+)/i);
      assert.ok(counted, `framing headers include a Content-Length: ${headers}`);
      const length = Number(counted[1]);
      if (this.leftover.length < headerEnd + 4 + length) return;
      const body = this.leftover.subarray(headerEnd + 4, headerEnd + 4 + length);
      this.leftover = this.leftover.subarray(headerEnd + 4 + length);
      const message = JSON.parse(body.toString("utf8"));
      const at = this.waiting.findIndex((waiter) => waiter.match(message));
      if (at >= 0) this.waiting.splice(at, 1)[0].resolve(message);
      else this.inbox.push(message);
    }
  }

  /** @param {object} message */
  send(message) {
    const body = Buffer.from(JSON.stringify({ jsonrpc: "2.0", ...message }), "utf8");
    this.child.stdin.write(`Content-Length: ${body.length}\r\n\r\n`);
    this.child.stdin.write(body);
  }

  /**
   * @param {string} method
   * @param {unknown} params
   * @returns {Promise<any>}
   */
  request(method, params) {
    this.id += 1;
    const id = this.id;
    this.send({ id, method, params });
    return this.next((message) => message.id === id);
  }

  /**
   * @param {string} method
   * @param {unknown} params
   */
  notify(method, params) {
    this.send({ method, params });
  }

  /**
   * @param {(message: any) => boolean} match
   * @returns {Promise<any>}
   */
  next(match) {
    const at = this.inbox.findIndex(match);
    if (at >= 0) return Promise.resolve(this.inbox.splice(at, 1)[0]);
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        reject(new Error(`timed out waiting on the server; stderr:\n${this.stderr}`));
      }, 5000);
      this.waiting.push({
        match,
        resolve: (message) => {
          clearTimeout(timer);
          resolve(message);
        },
      });
    });
  }

  published() {
    return this.next((message) => message.method === PUBLISHED);
  }
}

/**
 * @param {Client} client
 * @param {number} ms
 * @returns {Promise<number | null>}
 */
function exitedWithin(client, ms) {
  return Promise.race([
    client.exited,
    new Promise((resolve) => setTimeout(resolve, ms, "lingered").unref()),
  ]).then((outcome) => {
    if (outcome === "lingered") {
      client.child.kill("SIGKILL");
      throw new Error(`server still running after ${ms} ms; stderr:\n${client.stderr}`);
    }
    return /** @type {number | null} */ (outcome);
  });
}

before(() => {
  mkdirSync(path.join(ROOT, "tmp"), { recursive: true });
  scratch = mkdtempSync(path.join(ROOT, "tmp", "quikscript-lsp-"));
  target = bundle(path.join(scratch, "quikscript-lsp"));
});

after(() => {
  for (const client of spawned) {
    if (client.child.exitCode === null) client.child.kill("SIGKILL");
  }
  rmSync(scratch, { recursive: true, force: true });
});

test("the bundle is one executable file with the payload inlined", () => {
  assert.ok(statSync(target).mode & 0o111);
  const written = readFileSync(target, "utf8");
  assert.ok(written.startsWith("#!/usr/bin/env node\n"));
  assert.ok(written.includes(GOOD));
});

test("the bundled server checks a markdown document end to end", async () => {
  const client = new Client(target);
  const uri = "file:///draft/letter.md";
  const opened = `---\ntitle: letter\n---\n\n${GOOD} ${BAD}\n\n\`${BAD}\`\n\n\`\`\`\n${BAD}\n\`\`\`\n`;

  const answer = await client.request("initialize", {
    processId: process.pid,
    rootUri: null,
    capabilities: {},
  });
  assert.deepEqual(answer.result.capabilities, {
    textDocumentSync: { openClose: true, change: 1 },
    codeActionProvider: { codeActionKinds: ["quickfix"] },
    executeCommandProvider: {
      commands: [
        "quikscript.ignore.occurrence",
        "quikscript.ignore.directory",
        "quikscript.ignore.project",
        "quikscript.ignore.user",
      ],
    },
    hoverProvider: true,
    completionProvider: {},
  });
  assert.equal(answer.result.serverInfo.name, "quikscript-lsp");
  client.notify("initialized", {});

  const logged = await client.next((message) => message.method === "window/logMessage");
  assert.match(logged.params.message, /75674 spellings/);

  client.notify("textDocument/didOpen", {
    textDocument: { uri, languageId: "markdown", version: 1, text: opened },
  });
  const first = await client.published();
  assert.equal(first.params.uri, uri);
  assert.equal(first.params.version, 1);
  for (const diagnostic of first.params.diagnostics) {
    assert.ok(!("codeActions" in diagnostic));
  }
  assert.deepEqual(first.params.diagnostics, [
    {
      range: {
        start: { line: 4, character: GOOD.length + 1 },
        end: { line: 4, character: GOOD.length + 1 + BAD.length },
      },
      severity: 3,
      source: "quikscript",
      code: "unknown-word",
      message: `Unknown Quikscript spelling: ${BAD}`,
    },
  ]);

  client.notify("textDocument/didChange", {
    textDocument: { uri, version: 2 },
    contentChanges: [{ text: `${GOOD} ${BAD}${BAD}\n` }],
  });
  client.notify("textDocument/didChange", {
    textDocument: { uri, version: 3 },
    contentChanges: [{ text: `${GOOD}\n` }],
  });
  const second = await client.next(
    (message) => message.method === PUBLISHED && message.params.version === 3,
  );
  assert.equal(second.params.uri, uri);
  assert.deepEqual(second.params.diagnostics, []);
  assert.ok(
    !client.inbox.some(
      (message) => message.method === PUBLISHED && message.params.version === 2,
    ),
  );

  client.notify("textDocument/didChange", {
    textDocument: { uri, version: 4 },
    contentChanges: [
      {
        range: { start: { line: 0, character: 0 }, end: { line: 0, character: 0 } },
        text: BAD,
      },
    ],
  });
  const warning = await client.next(
    (message) =>
      message.method === "window/logMessage" &&
      /ranged changes/.test(message.params.message),
  );
  assert.equal(warning.params.type, 2);
  client.notify("textDocument/didChange", {
    textDocument: { uri, version: 5 },
    contentChanges: [{ text: `${GOOD}\n` }],
  });
  const fifth = await client.next(
    (message) => message.method === PUBLISHED && message.params.version === 5,
  );
  assert.deepEqual(fifth.params.diagnostics, []);
  assert.ok(
    !client.inbox.some(
      (message) => message.method === PUBLISHED && message.params.version === 4,
    ),
  );

  const other = "file:///draft/notes.txt";
  client.notify("textDocument/didOpen", {
    textDocument: { uri: other, languageId: "plaintext", version: 1, text: `\`${BAD}\`\n` },
  });
  const third = await client.published();
  assert.equal(third.params.uri, other);
  assert.equal(third.params.diagnostics.length, 1);
  client.notify("textDocument/didClose", { textDocument: { uri: other } });
  const fourth = await client.published();
  assert.equal(fourth.params.uri, other);
  assert.deepEqual(fourth.params.diagnostics, []);

  const shutdownResponse = await client.request("shutdown", null);
  assert.equal(shutdownResponse.result, null);
  client.notify("exit", null);
  assert.equal(await exitedWithin(client, 2000), 0);
});

test("exit without shutdown is the failure the spec prescribes", async () => {
  const client = new Client(target);
  client.notify("exit", null);
  assert.equal(await exitedWithin(client, 2000), 1);
});

test("the server exits when stdin closes", async () => {
  const client = new Client(target);
  await client.request("initialize", {
    processId: process.pid,
    rootUri: null,
    capabilities: {},
  });
  client.child.stdin.end();
  assert.equal(await exitedWithin(client, 2000), 1);
});

test("quick fixes follow suggest() order, and the directory, project and user ignores each write their own file", async () => {
  const A = misspelled(GOOD);
  const B = misspelled(A);
  const C = misspelled(B);
  const D = misspelled(C);
  const ws = path.join(scratch, "ws");
  mkdirSync(path.join(ws, "deep"), { recursive: true });
  const uri = pathToFileURL(path.join(ws, "deep", "draft.md")).href;
  const other = pathToFileURL(path.join(ws, "notes.txt")).href;
  const opened = `${A} ${A} ${B} ${C} ${D}\n`;

  const client = new Client(target);
  await client.request("initialize", {
    processId: process.pid,
    rootUri: pathToFileURL(ws).href,
    capabilities: INLINE,
  });
  client.notify("initialized", {});
  client.notify("textDocument/didOpen", {
    textDocument: { uri, languageId: "markdown", version: 1, text: opened },
  });

  const first = await client.published();
  assert.equal(first.params.uri, uri);
  const diagnostics = first.params.diagnostics;
  assert.deepEqual(firstMessageLines(diagnostics), [A, A, B, C, D].map(unknownMessage));

  const suggestions = core.suggest(A, suggestContext());
  assert.ok(suggestions.length > 0);
  const expected = suggestions
    .flatMap((suggestion) => [suggestion, `${suggestion} — and the 1 other written the same way`])
    .concat([
      "Ignore this occurrence",
      "Ignore in this directory",
      "Ignore in this project",
      "Ignore everywhere",
    ]);
  assert.deepEqual(titles(diagnostics[0].codeActions), expected);
  for (const action of diagnostics[0].codeActions) {
    if (action.edit) {
      assert.ok(!("documentChanges" in action.edit));
      assert.deepEqual(Object.keys(action.edit.changes), [uri]);
    } else {
      assert.ok(action.command);
    }
  }
  assert.equal(diagnostics[0].codeActions[0].isPreferred, true);
  const keyed = diagnostics[1].codeActions.find(
    (/** @type {any} */ action) => action.title === "Ignore this occurrence",
  );
  assert.deepEqual(keyed.command.arguments, [{ uri, word: A, occurrence: 1 }]);

  const asked = await client.request("textDocument/codeAction", {
    textDocument: { uri },
    range: diagnostics[0].range,
    context: { diagnostics: [] },
  });
  assert.deepEqual(titles(asked.result), expected);
  assert.equal(asked.result[0].isPreferred, true);
  assert.deepEqual(asked.result[0].edit.changes, {
    [uri]: [{ range: diagnostics[0].range, newText: suggestions[0] }],
  });
  for (const action of asked.result) {
    if (action.edit) assert.ok(!("documentChanges" in action.edit));
  }

  const point = { line: 0, character: 1 };
  const pointed = await client.request("textDocument/codeAction", {
    textDocument: { uri },
    range: { start: point, end: point },
    context: { diagnostics: [], only: ["quickfix"] },
  });
  assert.deepEqual(titles(pointed.result), expected);
  const refused = await client.request("textDocument/codeAction", {
    textDocument: { uri },
    range: diagnostics[0].range,
    context: { diagnostics: [], only: ["source.fixAll"] },
  });
  assert.equal(refused.result, null);

  await client.request("workspace/executeCommand", {
    command: "quikscript.ignore.occurrence",
    arguments: [{ uri, word: A, occurrence: 0 }],
  });
  const second = await client.published();
  assert.equal(second.params.uri, uri);
  assert.deepEqual(firstMessageLines(second.params.diagnostics), [A, B, C, D].map(unknownMessage));
  assert.deepEqual(second.params.diagnostics[0].range, diagnostics[1].range);
  const afterIgnore = await client.request("textDocument/codeAction", {
    textDocument: { uri },
    range: second.params.diagnostics[0].range,
    context: { diagnostics: [] },
  });
  assert.deepEqual(
    titles(afterIgnore.result),
    suggestions.concat([
      "Ignore this occurrence",
      "Ignore in this directory",
      "Ignore in this project",
      "Ignore everywhere",
    ]),
  );

  await client.request("workspace/executeCommand", {
    command: "quikscript.ignore.project",
    arguments: [{ uri, word: B }],
  });
  const third = await client.published();
  assert.equal(third.params.uri, uri);
  assert.deepEqual(firstMessageLines(third.params.diagnostics), [A, C, D].map(unknownMessage));
  assert.equal(readFileSync(path.join(ws, ".quikscript-ignore"), "utf8"), `${B}\n`);

  await client.request("workspace/executeCommand", {
    command: "quikscript.ignore.directory",
    arguments: [{ uri, word: D }],
  });
  const fourth = await client.published();
  assert.equal(fourth.params.uri, uri);
  assert.deepEqual(firstMessageLines(fourth.params.diagnostics), [A, C].map(unknownMessage));
  assert.equal(readFileSync(path.join(ws, "deep", ".quikscript-ignore"), "utf8"), `${D}\n`);
  assert.equal(readFileSync(path.join(ws, ".quikscript-ignore"), "utf8"), `${B}\n`);

  client.notify("textDocument/didOpen", {
    textDocument: {
      uri: other,
      languageId: "plaintext",
      version: 1,
      text: `${A} ${B} ${C} ${D}\n`,
    },
  });
  const fifth = await client.published();
  assert.equal(fifth.params.uri, other);
  assert.deepEqual(firstMessageLines(fifth.params.diagnostics), [A, C, D].map(unknownMessage));
  const notesActions = await client.request("textDocument/codeAction", {
    textDocument: { uri: other },
    range: fifth.params.diagnostics[0].range,
    context: { diagnostics: [] },
  });
  assert.deepEqual(titles(notesActions.result).slice(-3), [
    "Ignore this occurrence",
    "Ignore in this project",
    "Ignore everywhere",
  ]);

  await client.request("workspace/executeCommand", {
    command: "quikscript.ignore.user",
    arguments: [{ word: C }],
  });
  const sixth = await client.next(
    (message) => message.method === PUBLISHED && message.params.uri === uri,
  );
  const seventh = await client.next(
    (message) => message.method === PUBLISHED && message.params.uri === other,
  );
  assert.deepEqual(firstMessageLines(sixth.params.diagnostics), [unknownMessage(A)]);
  assert.deepEqual(firstMessageLines(seventh.params.diagnostics), [A, D].map(unknownMessage));
  assert.equal(
    readFileSync(path.join(scratch, "xdg", "quikscript", "ignore"), "utf8"),
    `${C}\n`,
  );

  const shutdownResponse = await client.request("shutdown", null);
  assert.equal(shutdownResponse.result, null);
  client.notify("exit", null);
  assert.equal(await exitedWithin(client, 2000), 0);

  const restarted = new Client(target);
  await restarted.request("initialize", {
    processId: process.pid,
    rootUri: pathToFileURL(ws).href,
    capabilities: INLINE,
  });
  restarted.notify("initialized", {});
  restarted.notify("textDocument/didOpen", {
    textDocument: { uri, languageId: "markdown", version: 1, text: opened },
  });
  const eighth = await restarted.published();
  assert.equal(eighth.params.uri, uri);
  assert.deepEqual(firstMessageLines(eighth.params.diagnostics), [A, A].map(unknownMessage));
  const secondShutdown = await restarted.request("shutdown", null);
  assert.equal(secondShutdown.result, null);
  restarted.notify("exit", null);
  assert.equal(await exitedWithin(restarted, 2000), 0);
});

test("with no workspace root, a project ignore is written in the file's directory", async () => {
  const home = path.join(scratch, "lone");
  mkdirSync(home, { recursive: true });
  const uri = pathToFileURL(path.join(home, "notes.txt")).href;
  const D = misspelled(GOOD);

  const client = new Client(target);
  await client.request("initialize", {
    processId: process.pid,
    rootUri: null,
    capabilities: {},
  });
  client.notify("initialized", {});
  client.notify("textDocument/didOpen", {
    textDocument: { uri, languageId: "plaintext", version: 1, text: `${D}\n` },
  });
  const first = await client.published();
  assert.deepEqual(firstMessageLines(first.params.diagnostics), [unknownMessage(D)]);

  const answered = await client.request("quikscript/fixes", { textDocument: { uri } });
  assert.deepEqual(answered.result.flags[0].ignore, {
    occurrence: {
      command: "quikscript.ignore.occurrence",
      arguments: [{ uri, word: D, occurrence: 0 }],
    },
    directory: null,
    project: { command: "quikscript.ignore.project", arguments: [{ uri, word: D }] },
    user: { command: "quikscript.ignore.user", arguments: [{ word: D }] },
  });

  const refused = await client.request("workspace/executeCommand", {
    command: "quikscript.ignore.project",
    arguments: [{ uri, word: "nope" }],
  });
  assert.equal(refused.result, null);
  assert.ok(!existsSync(path.join(home, ".quikscript-ignore")));

  await client.request("workspace/executeCommand", {
    command: "quikscript.ignore.project",
    arguments: [{ uri, word: D }],
  });
  const second = await client.published();
  assert.equal(second.params.uri, uri);
  assert.deepEqual(second.params.diagnostics, []);
  assert.equal(readFileSync(path.join(home, ".quikscript-ignore"), "utf8"), `${D}\n`);

  const shutdownResponse = await client.request("shutdown", null);
  assert.equal(shutdownResponse.result, null);
  client.notify("exit", null);
  assert.equal(await exitedWithin(client, 2000), 0);
});

test("a misspelling's diagnostic lists its suggestions", async () => {
  const uri = "file:///draft/fixes.txt";
  const word = misspelled(READ_EAT);
  const client = new Client(target);
  await client.request("initialize", {
    processId: process.pid,
    rootUri: null,
    capabilities: {},
  });
  client.notify("initialized", {});
  client.notify("textDocument/didOpen", {
    textDocument: { uri, languageId: "plaintext", version: 1, text: `${word}\n` },
  });
  const first = await client.published();

  const suggestions = core.suggest(word, suggestContext());
  assert.ok(suggestions.length > 0);
  /** @type {string[]} */
  const lines = first.params.diagnostics[0].message.split("\n");
  assert.equal(lines[0], unknownMessage(word));
  assert.equal(lines.length, suggestions.length + 1);
  for (const [at, suggestion] of suggestions.entries()) {
    assert.ok(lines[at + 1].startsWith(suggestion), `suggestion ${at} out of suggest() order`);
  }
  assert.ok(lines.some((line) => line.includes(" \u2014 ")));

  await client.request("workspace/executeCommand", {
    command: "quikscript.ignore.occurrence",
    arguments: [{ uri, word, occurrence: 0 }],
  });
  const second = await client.published();
  assert.deepEqual(second.params.diagnostics, []);
});

test("a code action request whose only is the empty kind gets the quick fixes", async () => {
  const uri = "file:///draft/empty-kind.txt";
  const word = misspelled(READ_EAT);
  const client = new Client(target);
  await client.request("initialize", {
    processId: process.pid,
    rootUri: null,
    capabilities: {},
  });
  client.notify("initialized", {});
  client.notify("textDocument/didOpen", {
    textDocument: { uri, languageId: "plaintext", version: 1, text: `${word}\n` },
  });
  const first = await client.published();

  const asked = await client.request("textDocument/codeAction", {
    textDocument: { uri },
    range: first.params.diagnostics[0].range,
    context: { diagnostics: [], only: [""] },
  });
  assert.ok(Array.isArray(asked.result));
  assert.equal(asked.result[0].title, core.suggest(word, suggestContext())[0]);
});

test("hover names the word and completions replace the latin", async () => {
  const uri = "file:///draft/lookup.txt";
  const client = new Client(target);
  await client.request("initialize", {
    processId: process.pid,
    rootUri: null,
    capabilities: {},
    initializationOptions: { completions: "auto" },
  });
  client.notify("initialized", {});
  client.notify("textDocument/didOpen", {
    textDocument: { uri, languageId: "plaintext", version: 1, text: `read ${READ_EAT}\n` },
  });
  await client.published();

  const over = await client.request("textDocument/hover", {
    textDocument: { uri },
    position: { line: 0, character: 6 },
  });
  assert.deepEqual(over.result, {
    contents: { kind: "markdown", value: READ_HOVER },
    range: { start: { line: 0, character: 5 }, end: { line: 0, character: 8 } },
  });

  const missed = await client.request("textDocument/hover", {
    textDocument: { uri },
    position: { line: 0, character: 2 },
  });
  assert.equal(missed.result, null);

  const asked = await client.request("textDocument/completion", {
    textDocument: { uri },
    position: { line: 0, character: 4 },
    context: { triggerKind: 1 },
  });
  const range = { start: { line: 0, character: 0 }, end: { line: 0, character: 4 } };
  assert.deepEqual(asked.result, [
    {
      label: READ_EAT,
      detail: "singular noun, verb, infinitive",
      sortText: "0000",
      kind: 1,
      filterText: "read",
      textEdit: { range, newText: READ_EAT },
    },
    {
      label: READ_ET,
      detail: "past-tense verb, past participle",
      sortText: "0001",
      kind: 1,
      filterText: "read",
      textEdit: { range, newText: READ_ET },
    },
  ]);

  const fenced = "file:///draft/fenced.md";
  client.notify("textDocument/didOpen", {
    textDocument: {
      uri: fenced,
      languageId: "markdown",
      version: 1,
      text: "```\nread\n```\n",
    },
  });
  await client.published();
  const inFence = await client.request("textDocument/completion", {
    textDocument: { uri: fenced },
    position: { line: 1, character: 4 },
    context: { triggerKind: 1 },
  });
  assert.equal(inFence.result, null);

  const spellings = await client.request("quikscript/spellings", { text: "Read zzxq" });
  assert.deepEqual(spellings.result, {
    words: [
      {
        latin: "read",
        items: [
          { label: READ_EAT, detail: "singular noun, verb, infinitive", sortText: "0000" },
          { label: READ_ET, detail: "past-tense verb, past participle", sortText: "0001" },
        ],
      },
      { latin: "zzxq", items: [] },
    ],
  });
  const blank = await client.request("quikscript/spellings", {});
  assert.deepEqual(blank.result, { words: [] });

  const shutdownResponse = await client.request("shutdown", null);
  assert.equal(shutdownResponse.result, null);
  client.notify("exit", null);
  assert.equal(await exitedWithin(client, 2000), 0);
});

test("completions are off by default and each mode works", async () => {
  const uri = "file:///draft/modes.txt";
  const client = new Client(target);
  await client.request("initialize", {
    processId: process.pid,
    rootUri: null,
    capabilities: {},
  });
  client.notify("initialized", {});
  client.notify("textDocument/didOpen", {
    textDocument: { uri, languageId: "plaintext", version: 1, text: "read\n" },
  });
  await client.published();
  const positionParams = { textDocument: { uri }, position: { line: 0, character: 4 } };

  const refused = await client.request("textDocument/completion", {
    ...positionParams,
    context: { triggerKind: 1 },
  });
  assert.equal(refused.result, null);

  client.notify("workspace/didChangeConfiguration", {
    settings: { quikscript: { completions: "onDemand" } },
  });
  const invoked = await client.request("textDocument/completion", {
    ...positionParams,
    context: { triggerKind: 1 },
  });
  assert.equal(invoked.result.length, 2);
  const typed = await client.request("textDocument/completion", {
    ...positionParams,
    context: { triggerKind: 2 },
  });
  assert.equal(typed.result, null);
  const contextless = await client.request("textDocument/completion", positionParams);
  assert.equal(contextless.result.length, 2);

  client.notify("workspace/didChangeConfiguration", {
    settings: { quikscript: { completions: "off" } },
  });
  const shut = await client.request("textDocument/completion", {
    ...positionParams,
    context: { triggerKind: 1 },
  });
  assert.equal(shut.result, null);

  const shutdownResponse = await client.request("shutdown", null);
  assert.equal(shutdownResponse.result, null);
  client.notify("exit", null);
  assert.equal(await exitedWithin(client, 2000), 0);
});

test("a client that supports workspace/configuration is asked for its settings", async () => {
  const uri = "file:///draft/pulled.txt";
  const client = new Client(target);
  await client.request("initialize", {
    processId: process.pid,
    rootUri: null,
    capabilities: { workspace: { configuration: true } },
    initializationOptions: { completions: "off" },
  });
  client.notify("initialized", {});
  const pulled = await client.next(
    (message) => message.method === "workspace/configuration",
  );
  assert.deepEqual(pulled.params.items, [{ section: "quikscript" }]);
  client.send({ id: pulled.id, result: [{ completions: "auto" }] });

  client.notify("textDocument/didOpen", {
    textDocument: { uri, languageId: "plaintext", version: 1, text: "read\n" },
  });
  await client.published();
  const positionParams = { textDocument: { uri }, position: { line: 0, character: 4 } };
  const answered = await client.request("textDocument/completion", positionParams);
  assert.equal(answered.result.length, 2);

  client.notify("workspace/didChangeConfiguration", { settings: {} });
  const repulled = await client.next(
    (message) => message.method === "workspace/configuration",
  );
  client.send({ id: repulled.id, result: [{ completions: "off" }] });
  const shut = await client.request("textDocument/completion", positionParams);
  assert.equal(shut.result, null);

  const shutdownResponse = await client.request("shutdown", null);
  assert.equal(shutdownResponse.result, null);
  client.notify("exit", null);
  assert.equal(await exitedWithin(client, 2000), 0);
});

test("an untitled document can add a project ignore but not a directory ignore", async () => {
  const workspaceDir = path.join(scratch, "workspace");
  mkdirSync(workspaceDir, { recursive: true });
  const uri = "untitled:Untitled-1";
  const E = misspelled(GOOD);

  const client = new Client(target);
  await client.request("initialize", {
    processId: process.pid,
    rootUri: pathToFileURL(workspaceDir).href,
    capabilities: {},
  });
  client.notify("initialized", {});
  client.notify("textDocument/didOpen", {
    textDocument: { uri, languageId: "plaintext", version: 1, text: `${E}\n` },
  });
  const first = await client.published();
  assert.deepEqual(firstMessageLines(first.params.diagnostics), [unknownMessage(E)]);

  await client.request("workspace/executeCommand", {
    command: "quikscript.ignore.project",
    arguments: [{ uri, word: E }],
  });
  const second = await client.published();
  assert.equal(second.params.uri, uri);
  assert.deepEqual(second.params.diagnostics, []);
  assert.equal(readFileSync(path.join(workspaceDir, ".quikscript-ignore"), "utf8"), `${E}\n`);

  const nowhere = await client.request("workspace/executeCommand", {
    command: "quikscript.ignore.directory",
    arguments: [{ uri, word: E }],
  });
  assert.equal(nowhere.result, null);
  assert.deepEqual(readdirSync(workspaceDir), [".quikscript-ignore"]);

  const shutdownResponse = await client.request("shutdown", null);
  assert.equal(shutdownResponse.result, null);
  client.notify("exit", null);
  assert.equal(await exitedWithin(client, 2000), 0);
});

test("quikscript/fixes returns each flagged word's suggestions, glosses, edits and ignores", async () => {
  const A = misspelled(GOOD);
  const B = misspelled(A);
  const panel = path.join(scratch, "panel");
  mkdirSync(panel, { recursive: true });
  const uri = pathToFileURL(path.join(panel, "notes.txt")).href;

  const client = new Client(target);
  await client.request("initialize", {
    processId: process.pid,
    rootUri: pathToFileURL(panel).href,
    capabilities: {},
  });
  client.notify("initialized", {});
  client.notify("textDocument/didOpen", {
    textDocument: { uri, languageId: "plaintext", version: 1, text: `${A} ${A} ${B}\n` },
  });
  const first = await client.published();
  const diagnostics = first.params.diagnostics;
  assert.deepEqual(firstMessageLines(diagnostics), [A, A, B].map(unknownMessage));

  const answered = await client.request("quikscript/fixes", { textDocument: { uri } });
  /** @type {any[]} */
  const flags = answered.result.flags;
  assert.deepEqual(
    flags.map((flag) => [flag.word, flag.occurrence, flag.range]),
    [
      [A, 0, diagnostics[0].range],
      [A, 1, diagnostics[1].range],
      [B, 0, diagnostics[2].range],
    ],
  );
  assert.deepEqual(flags[0].spans, [diagnostics[0].range, diagnostics[1].range]);
  assert.deepEqual(flags[1].spans, [diagnostics[0].range, diagnostics[1].range]);
  assert.deepEqual(flags[2].spans, [diagnostics[2].range]);

  const latinBySpelling = parseLatinBySpelling(data);
  let glosses = 0;
  for (const flag of flags) {
    /** @type {any[]} */
    const fixes = flag.fixes;
    const suggestions = core.suggest(flag.word, suggestContext());
    assert.ok(suggestions.length > 0);
    assert.deepEqual(fixes.map((one) => one.fix), suggestions);
    for (const one of fixes) {
      assert.equal(one.gloss, glossed(one.fix, latinBySpelling));
      if (one.gloss) glosses += 1;
      assert.deepEqual(one.edit, {
        changes: { [uri]: [{ range: flag.range, newText: one.fix }] },
      });
    }
    assert.deepEqual(flag.ignore, {
      occurrence: {
        command: "quikscript.ignore.occurrence",
        arguments: [{ uri, word: flag.word, occurrence: flag.occurrence }],
      },
      directory: null,
      project: { command: "quikscript.ignore.project", arguments: [{ uri, word: flag.word }] },
      user: { command: "quikscript.ignore.user", arguments: [{ word: flag.word }] },
    });
  }
  assert.ok(glosses > 0);

  const absent = await client.request("quikscript/fixes", {
    textDocument: { uri: "file:///draft/absent.txt" },
  });
  assert.deepEqual(absent.result, { flags: [] });

  await client.request("workspace/executeCommand", {
    command: flags[0].ignore.occurrence.command,
    arguments: flags[0].ignore.occurrence.arguments,
  });
  const second = await client.published();
  assert.deepEqual(firstMessageLines(second.params.diagnostics), [A, B].map(unknownMessage));
  const again = await client.request("quikscript/fixes", { textDocument: { uri } });
  /** @type {any[]} */
  const rest = again.result.flags;
  assert.deepEqual(
    rest.map((flag) => [flag.word, flag.occurrence, flag.range]),
    [
      [A, 1, diagnostics[1].range],
      [B, 0, diagnostics[2].range],
    ],
  );

  const shutdownResponse = await client.request("shutdown", null);
  assert.equal(shutdownResponse.result, null);
  client.notify("exit", null);
  assert.equal(await exitedWithin(client, 2000), 0);
});

test("with no root, an untitled document gets no project ignore", async () => {
  const uri = "untitled:Untitled-2";
  const F = misspelled(GOOD);

  const client = new Client(target);
  await client.request("initialize", {
    processId: process.pid,
    rootUri: null,
    capabilities: {},
  });
  client.notify("initialized", {});
  client.notify("textDocument/didOpen", {
    textDocument: { uri, languageId: "plaintext", version: 1, text: `${F}\n` },
  });
  const first = await client.published();
  assert.deepEqual(firstMessageLines(first.params.diagnostics), [unknownMessage(F)]);

  const answered = await client.request("quikscript/fixes", { textDocument: { uri } });
  /** @type {any[]} */
  const flags = answered.result.flags;
  assert.equal(flags.length, 1);
  assert.deepEqual(flags[0].range, first.params.diagnostics[0].range);
  assert.deepEqual(flags[0].ignore, {
    occurrence: {
      command: "quikscript.ignore.occurrence",
      arguments: [{ uri, word: F, occurrence: 0 }],
    },
    directory: null,
    project: null,
    user: { command: "quikscript.ignore.user", arguments: [{ word: F }] },
  });

  const shutdownResponse = await client.request("shutdown", null);
  assert.equal(shutdownResponse.result, null);
  client.notify("exit", null);
  assert.equal(await exitedWithin(client, 2000), 0);
});
