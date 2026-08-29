const path = require("node:path");
const { existsSync } = require("node:fs");
const { window, workspace } = require("vscode");
const { LanguageClient, TransportKind } = require("vscode-languageclient/node");

const SECTION = "quikscript";
const BUNDLED = ["dist", "quikscript-lsp"];
const BESIDE = ["..", "server", "server.js"];

/** @type {LanguageClient | undefined} */
let client;

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

/** @param {import("vscode").ExtensionContext} context */
async function activate(context) {
  const entry = located(context.extensionPath);
  if (!entry) {
    window.showErrorMessage(
      "Quikscript: no language server found. Run `make bundle`, or set quikscript.serverPath.",
    );
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
}

async function deactivate() {
  if (client) await client.stop();
}

module.exports = { activate, deactivate };
