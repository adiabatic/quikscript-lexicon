const path = require("node:path");
const { existsSync } = require("node:fs");
const { Range, Uri, WorkspaceEdit, commands, env, languages, window, workspace } = require("vscode");
const { LanguageClient, TransportKind } = require("vscode-languageclient/node");
const { lookupRows, resolveMessage, rows, shell } = require("./lib/panel.js");

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
const NO_DOCUMENT_NOTE = "Open a Markdown or plain text file.";
const SERVER_NOT_RUNNING_NOTE = "The language server is not running.";
const REQUEST_FAILED_NOTE = "The request to the language server failed.";
const NOTHING_FLAGGED_NOTE = "Nothing flagged.";

/** @typedef {import("./lib/panel.js").Change} Change */
/** @typedef {import("./lib/panel.js").Flag} Flag */
/** @typedef {import("./lib/panel.js").LookupResult} LookupResult */
/** @typedef {import("./lib/panel.js").Span} Span */
/** @typedef {import("./lib/panel.js").State} State */

/** @type {LanguageClient | undefined} */
let client;
/** @type {import("vscode").WebviewView | undefined} */
let view;
/** @type {import("./lib/panel.js").DocumentFlags} */
let lastFixes = { uri: "", flags: [] };
/** @type {State} */
let lastState = { rows: [], note: NO_DOCUMENT_NOTE };

/**
 * @param {string} root
 * @returns {string | null}
 */
function serverPath(root) {
  const configured = workspace.getConfiguration(SECTION).get("serverPath");
  if (typeof configured === "string" && configured) return configured;
  for (const parts of [BUNDLED, BESIDE]) {
    const guess = path.join(root, ...parts);
    if (existsSync(guess)) return guess;
  }
  return null;
}

/** @returns {import("vscode").TextDocument | null} */
function activeDocument() {
  const editor = window.activeTextEditor;
  if (!editor) return null;
  const { document } = editor;
  if (document.uri.scheme !== "file") return null;
  return LANGUAGES.includes(document.languageId) ? document : null;
}

/** @param {State} next */
function post(next) {
  lastState = next;
  if (view) view.webview.postMessage({ type: "state", state: next });
}

/**
 * @param {number} id
 * @param {string} text
 */
async function lookUp(id, text) {
  /** @type {{rows: import("./lib/panel.js").LookupRow[], note: string}} */
  let result = { rows: [], note: SERVER_NOT_RUNNING_NOTE };
  if (client && client.isRunning()) {
    try {
      const response = /** @type {{words: LookupResult[]}} */ (
        await client.sendRequest(SPELLINGS, { text })
      );
      result = { rows: lookupRows(response.words), note: "" };
    } catch {
      result = { rows: [], note: REQUEST_FAILED_NOTE };
    }
  }
  if (view) view.webview.postMessage({ type: "lookupResult", id, ...result });
}

async function refresh() {
  const document = activeDocument();
  if (!document) return post({ rows: [], note: NO_DOCUMENT_NOTE });
  if (!client || !client.isRunning()) return post({ rows: [], note: SERVER_NOT_RUNNING_NOTE });
  const uri = client.code2ProtocolConverter.asUri(document.uri);
  try {
    const response = /** @type {{flags: Flag[]}} */ (
      await client.sendRequest(FIXES, { textDocument: { uri } })
    );
    lastFixes = { uri, flags: response.flags };
    post({ rows: rows(response.flags), note: NOTHING_FLAGGED_NOTE });
  } catch {
    post({ rows: [], note: REQUEST_FAILED_NOTE });
  }
}

/**
 * @param {Span} span
 * @returns {import("vscode").Range}
 */
function toRange(span) {
  return new Range(span.start.line, span.start.character, span.end.line, span.end.character);
}

/** @param {Change} change */
async function applyChange(change) {
  const edit = new WorkspaceEdit();
  for (const [uri, edits] of Object.entries(change.changes)) {
    for (const one of edits) edit.replace(Uri.parse(uri), toRange(one.range), one.newText);
  }
  await workspace.applyEdit(edit);
}

/** @param {any} message */
async function handle(message) {
  if (message.type === "ready") return post(lastState);
  if (message.type === "copy") return env.clipboard.writeText(String(message.text));
  if (message.type === "lookup") return lookUp(Number(message.id), String(message.text));
  const resolution = resolveMessage(lastFixes, message);
  if (!resolution) return;
  if ("edit" in resolution) return applyChange(resolution.edit);
  if ("command" in resolution) {
    const { command } = resolution;
    await commands.executeCommand(command.command, ...command.arguments);
    return;
  }
  const document = await workspace.openTextDocument(Uri.parse(lastFixes.uri));
  await window.showTextDocument(document, { selection: toRange(resolution.range) });
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
      const document = activeDocument();
      if (!document) return;
      const uri = document.uri.toString();
      if (event.uris.some((one) => one.toString() === uri)) refresh();
    }),
  );
  const entry = serverPath(context.extensionPath);
  if (!entry) {
    window.showErrorMessage(
      "Quikscript: no language server found. Run `make vsix`, or set quikscript.serverPath.",
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
