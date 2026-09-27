const path = require("node:path");
const { existsSync } = require("node:fs");
const { Range, Uri, WorkspaceEdit, commands, env, languages, window, workspace } = require("vscode");
const { LanguageClient, TransportKind } = require("vscode-languageclient/node");
const { resolved, rows, shell, shown } = require("./lib/panel.js");

const SECTION = "quikscript";
const BUNDLED = ["dist", "quikscript-lsp"];
const BESIDE = ["..", "server", "server.js"];
const VIEW = "quikscript.fixes";
const FIXES = "quikscript/fixes";
const SPELLINGS = "quikscript/spellings";
const MEDIA = "media";
const STYLES = ["quikscript-webview.css", "panel.css"];
const SCRIPT = "panel.js";
const LANGUAGES = ["markdown", "plaintext"];
const SHUT = "Open a Markdown or plain text file.";
const STILL = "The language server is not running.";
const CLEAN = "Nothing flagged.";

/** @typedef {import("./lib/panel.js").Change} Change */
/** @typedef {import("./lib/panel.js").Fixed} Fixed */
/** @typedef {import("./lib/panel.js").Span} Span */
/** @typedef {import("./lib/panel.js").State} State */
/** @typedef {import("./lib/panel.js").Written} Written */

/** @type {LanguageClient | undefined} */
let client;
/** @type {import("vscode").WebviewView | undefined} */
let view;
/** @type {import("./lib/panel.js").Held} */
let held = { uri: "", flags: [] };
/** @type {State} */
let told = { rows: [], note: SHUT };

/**
 * @param {string} root
 * @returns {string | null}
 */
function located(root) {
  const configured = workspace.getConfiguration(SECTION).get("serverPath");
  if (typeof configured === "string" && configured) return configured;
  for (const parts of [BUNDLED, BESIDE]) {
    const guess = path.join(root, ...parts);
    if (existsSync(guess)) return guess;
  }
  return null;
}

/** @returns {import("vscode").TextDocument | null} */
function subject() {
  const editor = window.activeTextEditor;
  if (!editor) return null;
  const { document } = editor;
  if (document.uri.scheme !== "file") return null;
  return LANGUAGES.includes(document.languageId) ? document : null;
}

/** @param {State} next */
function post(next) {
  told = next;
  if (view) view.webview.postMessage({ type: "state", state: next });
}

/**
 * @param {number} id
 * @param {string} text
 */
async function written(id, text) {
  /** @type {{rows: import("./lib/panel.js").Shown[], note: string}} */
  let answer = { rows: [], note: STILL };
  if (client && client.isRunning()) {
    try {
      const words = /** @type {{words: Written[]}} */ (
        await client.sendRequest(SPELLINGS, { text })
      );
      answer = { rows: shown(words.words), note: "" };
    } catch {}
  }
  if (view) view.webview.postMessage({ type: "written", id, ...answer });
}

async function refresh() {
  const document = subject();
  if (!document) return post({ rows: [], note: SHUT });
  if (!client || !client.isRunning()) return post({ rows: [], note: STILL });
  const uri = client.code2ProtocolConverter.asUri(document.uri);
  try {
    const answer = /** @type {{flags: Fixed[]}} */ (
      await client.sendRequest(FIXES, { textDocument: { uri } })
    );
    held = { uri, flags: answer.flags };
    post({ rows: rows(answer.flags), note: CLEAN });
  } catch {
    post({ rows: [], note: STILL });
  }
}

/**
 * @param {Span} span
 * @returns {import("vscode").Range}
 */
function ranged(span) {
  return new Range(span.start.line, span.start.character, span.end.line, span.end.character);
}

/** @param {Change} change */
async function applied(change) {
  const edit = new WorkspaceEdit();
  for (const [uri, edits] of Object.entries(change.changes)) {
    for (const one of edits) edit.replace(Uri.parse(uri), ranged(one.range), one.newText);
  }
  await workspace.applyEdit(edit);
}

/** @param {any} message */
async function handle(message) {
  if (message.type === "ready") return post(told);
  if (message.type === "copy") return env.clipboard.writeText(String(message.text));
  if (message.type === "write") return written(Number(message.id), String(message.text));
  const answer = resolved(held, message);
  if (!answer) return;
  if ("edit" in answer) return applied(answer.edit);
  if ("order" in answer) {
    await commands.executeCommand(answer.order.command, ...answer.order.arguments);
    return;
  }
  const shown = await workspace.openTextDocument(Uri.parse(held.uri));
  await window.showTextDocument(shown, { selection: ranged(answer.range) });
}

/**
 * @param {import("vscode").ExtensionContext} context
 * @returns {import("vscode").WebviewViewProvider}
 */
function provider(context) {
  const media = Uri.joinPath(context.extensionUri, MEDIA);
  return {
    resolveWebviewView(panel) {
      view = panel;
      const { webview } = panel;
      webview.options = { enableScripts: true, localResourceRoots: [media] };
      webview.html = shell({
        csp: webview.cspSource,
        styles: STYLES.map((file) => webview.asWebviewUri(Uri.joinPath(media, file)).toString()),
        script: webview.asWebviewUri(Uri.joinPath(media, SCRIPT)).toString(),
      });
      webview.onDidReceiveMessage(handle, null, context.subscriptions);
      panel.onDidDispose(
        () => {
          if (view === panel) view = undefined;
        },
        null,
        context.subscriptions,
      );
      panel.onDidChangeVisibility(
        () => {
          if (panel.visible) refresh();
        },
        null,
        context.subscriptions,
      );
    },
  };
}

/** @param {import("vscode").ExtensionContext} context */
async function activate(context) {
  context.subscriptions.push(
    window.registerWebviewViewProvider(VIEW, provider(context)),
    window.onDidChangeActiveTextEditor(() => refresh()),
    languages.onDidChangeDiagnostics((event) => {
      const document = subject();
      if (!document) return;
      const uri = document.uri.toString();
      if (event.uris.some((one) => one.toString() === uri)) refresh();
    }),
  );
  const entry = located(context.extensionPath);
  if (!entry) {
    window.showErrorMessage(
      "Quikscript: no language server found. Run `make bundle`, or set quikscript.serverPath.",
    );
    await refresh();
    return;
  }
  /** @type {import("vscode-languageclient/node").NodeModule} */
  const node = { module: entry, transport: TransportKind.stdio };
  client = new LanguageClient(
    SECTION,
    "Quikscript",
    { run: node, debug: node },
    {
      documentSelector: [
        { scheme: "file", language: "markdown" },
        { scheme: "file", language: "plaintext" },
      ],
      initializationOptions: {
        completions: workspace.getConfiguration(SECTION).get("completions"),
      },
      synchronize: { configurationSection: SECTION },
    },
  );
  await client.start();
  await refresh();
}

async function deactivate() {
  if (client) await client.stop();
}

module.exports = { activate, deactivate };
