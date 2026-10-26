/** @typedef {import("../lib/panel.js").LookupRow} LookupRow */
/** @typedef {import("../lib/panel.js").State} State */
/** @typedef {import("../lib/panel.js").SuggestionRow} SuggestionRow */
/** @typedef {import("../lib/panel.js").WordRow} WordRow */
/** @typedef {{postMessage(message: unknown): void}} VsCodeApi */
/** @typedef {(fix: string, all: boolean) => unknown} Picker */
/** @typedef {{root: HTMLElement, input: HTMLInputElement, requestLookup(): void, showResults(id: number, rows: LookupRow[], note: string): void}} LookupForm */

const EMPTY = "No suggestions";
const PROMPT = "Spell it in Latin letters";
const COPY = "Copy this spelling";
const LOOKUP_DEBOUNCE_MS = 150;

const vscodeApi = /** @type {{acquireVsCodeApi(): VsCodeApi}} */ (
  /** @type {unknown} */ (globalThis)
).acquireVsCodeApi();
const container = /** @type {HTMLElement} */ (document.querySelector("main"));
/** @type {Map<number, LookupForm>} */
const pendingLookups = new Map();
/** @type {Map<string, string>} */
const drafts = new Map();
let lastRequestId = 0;

/**
 * @param {string} tag
 * @param {string} className
 * @param {string} text
 * @returns {HTMLElement}
 */
function textElement(tag, className, text) {
  const element = document.createElement(tag);
  element.className = className;
  element.textContent = text;
  return element;
}

/**
 * @param {string} className
 * @param {unknown} message
 * @returns {HTMLButtonElement}
 */
function messageButton(className, message) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = className;
  button.addEventListener("click", () => vscodeApi.postMessage(message));
  return button;
}

/**
 * @param {WordRow} row
 * @returns {HTMLButtonElement}
 */
function wordButton(row) {
  const button = messageButton("word", { type: "reveal", flag: row.flag });
  button.append(
    textElement("span", "text", row.word),
    textElement("span", "position", `${row.line + 1}:${row.character + 1}`),
  );
  return button;
}

/**
 * @param {string} fix
 * @param {string} gloss
 * @param {number} others
 * @param {Picker} pick
 * @param {string} hint
 * @returns {HTMLElement}
 */
function suggestionElement(fix, gloss, others, pick, hint) {
  const suggestion = document.createElement("div");
  suggestion.className = "suggestion";
  const button = messageButton("fix", pick(fix, false));
  button.append(textElement("span", "text", fix));
  if (gloss) button.append(textElement("span", "gloss", gloss));
  if (hint) button.title = hint;
  suggestion.append(button);
  if (others > 0) {
    const rest = others === 1 ? "the 1 other" : `the ${others} others`;
    const fixAll = messageButton("fix-all", pick(fix, true));
    fixAll.textContent = `(${others})`;
    fixAll.title = `Correct this misspelling and ${rest} written the same way`;
    suggestion.append(fixAll);
  }
  return suggestion;
}

/**
 * @param {SuggestionRow} row
 * @returns {HTMLElement}
 */
function suggestionRow(row) {
  /** @type {Picker} */
  const pick = (_fix, all) => ({ type: "fix", flag: row.flag, at: row.at, all });
  return suggestionElement(row.fix, row.gloss, row.others, pick, "");
}

/**
 * @param {number} others
 * @param {Picker} pick
 * @param {string} hint
 * @returns {LookupForm}
 */
function lookupForm(others, pick, hint) {
  const root = document.createElement("form");
  root.className = "lookup-form";
  const results = textElement("div", "lookup-results", "");
  root.addEventListener("submit", (event) => {
    event.preventDefault();
    const first = /** @type {HTMLButtonElement | null} */ (results.querySelector("button.fix"));
    if (first) first.click();
  });
  const input = document.createElement("input");
  input.type = "search";
  input.className = "latin-input";
  input.placeholder = PROMPT;
  input.spellcheck = false;
  input.autocomplete = "off";
  root.append(input, results);
  /** @type {ReturnType<typeof setTimeout> | undefined} */
  let timer;
  let currentRequestId = 0;
  /** @type {LookupForm} */
  const form = {
    root,
    input,
    requestLookup() {
      const text = input.value.trim();
      if (!text) {
        currentRequestId = 0;
        results.replaceChildren();
        return;
      }
      lastRequestId += 1;
      currentRequestId = lastRequestId;
      pendingLookups.set(lastRequestId, form);
      vscodeApi.postMessage({ type: "lookup", id: lastRequestId, text });
    },
    showResults(id, rows, note) {
      if (id !== currentRequestId) return;
      results.replaceChildren();
      if (note) results.append(textElement("p", "note", note));
      for (const row of rows) {
        if (row.kind === "phrase")
          results.append(suggestionElement(row.fix, "", others, pick, hint));
        else if (row.kind === "form")
          results.append(suggestionElement(row.fix, row.gloss, others, pick, hint));
        else results.append(textElement("p", "note", `No spelling for ${row.latin}`));
      }
    },
  };
  input.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(() => form.requestLookup(), LOOKUP_DEBOUNCE_MS);
  });
  return form;
}

/**
 * @param {WordRow} row
 * @returns {LookupForm}
 */
function fixInput(row) {
  const key = `${row.word} ${row.occurrence}`;
  /** @type {Picker} */
  const pick = (fix, all) => ({ type: "typed", flag: row.flag, fix, all });
  const form = lookupForm(row.others, pick, "");
  form.input.addEventListener("input", () => drafts.set(key, form.input.value));
  const draft = drafts.get(key);
  if (draft) {
    form.input.value = draft;
    form.requestLookup();
  }
  return form;
}

/** @param {State} state */
function render(state) {
  container.replaceChildren();
  /** @type {Set<string>} */
  const shownKeys = new Set();
  if (state.rows.length === 0) container.append(textElement("p", "note", state.note));
  let section = container;
  /** @type {WordRow | null} */
  let wordRow = null;
  /** @type {HTMLElement | null} */
  let ignores = null;
  for (const row of state.rows) {
    if (row.kind === "word") {
      section = document.createElement("section");
      container.append(section);
      section.append(wordButton(row));
      wordRow = row;
      ignores = null;
      shownKeys.add(`${row.word} ${row.occurrence}`);
    } else if (row.kind === "none") {
      section.append(textElement("p", "note", EMPTY));
    } else if (row.kind === "suggestion") {
      section.append(suggestionRow(row));
    } else {
      if (!ignores) {
        if (wordRow) section.append(fixInput(wordRow).root);
        ignores = textElement("div", "ignores", "");
        section.append(ignores);
      }
      const button = messageButton("ignore", { type: "ignore", flag: row.flag, scope: row.scope });
      button.textContent = row.label;
      ignores.append(button);
    }
  }
  for (const key of drafts.keys()) {
    if (!shownKeys.has(key)) drafts.delete(key);
  }
}

const lookup = lookupForm(0, (fix) => ({ type: "copy", text: fix }), COPY);
lookup.root.classList.add("lookup");
container.before(lookup.root);

window.addEventListener("message", (event) => {
  const message = event.data;
  if (message.type === "lookupResult") {
    const form = pendingLookups.get(message.id);
    pendingLookups.delete(message.id);
    if (form) form.showResults(message.id, message.rows, message.note);
  } else if (message.type === "state") {
    render(message.state);
  }
});
vscodeApi.postMessage({ type: "ready" });
