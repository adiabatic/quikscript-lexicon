const assert = require("node:assert/strict");
const { test, before, after } = require("node:test");
const { spawn } = require("node:child_process");
const { mkdirSync, mkdtempSync, readFileSync, rmSync, statSync } = require("node:fs");
const path = require("node:path");
const { bundle } = require("../bundle.js");
const data = require("../payload.json");

const GOOD = data.words.split("\n", 1)[0].split("\t", 1)[0];
const BAD = "\uE650".repeat(9);
const PUBLISHED = "textDocument/publishDiagnostics";

const ROOT = path.join(__dirname, "..", "..", "..");
let scratch = "";
let target = "";
/** @type {Client[]} */
const spawned = [];

class Client {
  /** @param {string} launched */
  constructor(launched) {
    this.child = spawn(process.execPath, [launched, "--stdio"]);
    this.leftover = Buffer.alloc(0);
    /** @type {any[]} */
    this.inbox = [];
    /** @type {{match: (message: any) => boolean, took: (message: any) => void}[]} */
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
      const seam = this.leftover.indexOf("\r\n\r\n");
      if (seam < 0) return;
      const held = this.leftover.subarray(0, seam).toString("ascii");
      const counted = held.match(/Content-Length: (\d+)/i);
      assert.ok(counted, `framing headers carry a length: ${held}`);
      const length = Number(counted[1]);
      if (this.leftover.length < seam + 4 + length) return;
      const body = this.leftover.subarray(seam + 4, seam + 4 + length);
      this.leftover = this.leftover.subarray(seam + 4 + length);
      const message = JSON.parse(body.toString("utf8"));
      const at = this.waiting.findIndex((keen) => keen.match(message));
      if (at >= 0) this.waiting.splice(at, 1)[0].took(message);
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
    return new Promise((took, refuse) => {
      const bomb = setTimeout(() => {
        refuse(new Error(`timed out waiting on the server; stderr:\n${this.stderr}`));
      }, 5000);
      this.waiting.push({
        match,
        took: (message) => {
          clearTimeout(bomb);
          took(message);
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
  });
  assert.equal(answer.result.serverInfo.name, "quikscript-lsp");
  client.notify("initialized", {});

  const logged = await client.next((message) => message.method === "window/logMessage");
  assert.match(logged.params.message, /75651 spellings/);

  client.notify("textDocument/didOpen", {
    textDocument: { uri, languageId: "markdown", version: 1, text: opened },
  });
  const first = await client.published();
  assert.equal(first.params.uri, uri);
  assert.equal(first.params.version, 1);
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
  const scolded = await client.next(
    (message) =>
      message.method === "window/logMessage" &&
      /ranged changes/.test(message.params.message),
  );
  assert.equal(scolded.params.type, 2);
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

  const bye = await client.request("shutdown", null);
  assert.equal(bye.result, null);
  client.notify("exit", null);
  assert.equal(await exitedWithin(client, 2000), 0);
});

test("exit without shutdown is the failure the spec prescribes", async () => {
  const client = new Client(target);
  client.notify("exit", null);
  assert.equal(await exitedWithin(client, 2000), 1);
});

test("a vanished client leaves no orphan process", async () => {
  const client = new Client(target);
  await client.request("initialize", {
    processId: process.pid,
    rootUri: null,
    capabilities: {},
  });
  client.child.stdin.end();
  assert.equal(await exitedWithin(client, 2000), 1);
});
