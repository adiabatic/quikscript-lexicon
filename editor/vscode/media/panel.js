/** @typedef {import("../lib/panel.js").Named} Named */
/** @typedef {import("../lib/panel.js").Offered} Offered */
/** @typedef {import("../lib/panel.js").Shown} Shown */
/** @typedef {import("../lib/panel.js").State} State */
/** @typedef {{postMessage(message: unknown): void}} Bridge */
/** @typedef {(fix: string, sweep: boolean) => unknown} Picker */
/** @typedef {{root: HTMLElement, input: HTMLInputElement, ask(): void, answer(id: number, rows: Shown[], note: string): void}} Writer */

const EMPTY = "No suggestions";
const PROMPT = "Spell it in Latin letters";
const COPY = "Copy this spelling";
const PATIENCE = 150;

const bridge = /** @type {{acquireVsCodeApi(): Bridge}} */ (
  /** @type {unknown} */ (globalThis)
).acquireVsCodeApi();
const board = /** @type {HTMLElement} */ (document.querySelector("main"));
/** @type {Map<number, Writer>} */
const waiting = new Map();
/** @type {Map<string, string>} */
const drafts = new Map();
let serial = 0;

/**
 * @param {string} tag
 * @param {string} mark
 * @param {string} text
 * @returns {HTMLElement}
 */
function made(tag, mark, text) {
  const held = document.createElement(tag);
  held.className = mark;
  held.textContent = text;
  return held;
}

/**
 * @param {string} mark
 * @param {unknown} message
 * @returns {HTMLButtonElement}
 */
function pressed(mark, message) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = mark;
  button.addEventListener("click", () => bridge.postMessage(message));
  return button;
}

/**
 * @param {Named} row
 * @returns {HTMLButtonElement}
 */
function worded(row) {
  const button = pressed("word", { type: "reveal", flag: row.flag });
  button.append(
    made("span", "text", row.word),
    made("span", "at", `${row.line + 1}:${row.character + 1}`),
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
function choice(fix, gloss, others, pick, hint) {
  const held = document.createElement("div");
  held.className = "offer";
  const button = pressed("fix", pick(fix, false));
  button.append(made("span", "text", fix));
  if (gloss) button.append(made("span", "gloss", gloss));
  if (hint) button.title = hint;
  held.append(button);
  if (others > 0) {
    const rest = others === 1 ? "the 1 other" : `the ${others} others`;
    const all = pressed("all", pick(fix, true));
    all.textContent = `(${others})`;
    all.title = `Correct this misspelling and ${rest} written the same way`;
    held.append(all);
  }
  return held;
}

/**
 * @param {Offered} row
 * @returns {HTMLElement}
 */
function offered(row) {
  /** @type {Picker} */
  const pick = (_fix, sweep) => ({ type: "fix", flag: row.flag, at: row.at, sweep });
  return choice(row.fix, row.gloss, row.others, pick, "");
}

/**
 * @param {number} others
 * @param {Picker} pick
 * @param {string} hint
 * @returns {Writer}
 */
function writer(others, pick, hint) {
  const root = document.createElement("form");
  root.className = "writer";
  const told = made("div", "written", "");
  root.addEventListener("submit", (event) => {
    event.preventDefault();
    const first = /** @type {HTMLButtonElement | null} */ (told.querySelector("button.fix"));
    if (first) first.click();
  });
  const input = document.createElement("input");
  input.type = "search";
  input.className = "latin";
  input.placeholder = PROMPT;
  input.spellcheck = false;
  input.autocomplete = "off";
  root.append(input, told);
  /** @type {ReturnType<typeof setTimeout> | undefined} */
  let timer;
  let sent = 0;
  /** @type {Writer} */
  const held = {
    root,
    input,
    ask() {
      const text = input.value.trim();
      if (!text) {
        sent = 0;
        told.replaceChildren();
        return;
      }
      serial += 1;
      sent = serial;
      waiting.set(serial, held);
      bridge.postMessage({ type: "write", id: serial, text });
    },
    answer(id, rows, note) {
      if (id !== sent) return;
      told.replaceChildren();
      if (note) told.append(made("p", "quiet", note));
      for (const row of rows) {
        if (row.kind === "phrase") told.append(choice(row.fix, "", others, pick, hint));
        else if (row.kind === "form") told.append(choice(row.fix, row.gloss, others, pick, hint));
        else told.append(made("p", "quiet", `No spelling for ${row.latin}`));
      }
    },
  };
  input.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(() => held.ask(), PATIENCE);
  });
  return held;
}

/**
 * @param {Named} row
 * @returns {Writer}
 */
function typist(row) {
  const key = `${row.word} ${row.occurrence}`;
  /** @type {Picker} */
  const pick = (fix, sweep) => ({ type: "typed", flag: row.flag, fix, sweep });
  const held = writer(row.others, pick, "");
  held.input.addEventListener("input", () => drafts.set(key, held.input.value));
  const draft = drafts.get(key);
  if (draft) {
    held.input.value = draft;
    held.ask();
  }
  return held;
}

/** @param {State} state */
function painted(state) {
  board.replaceChildren();
  /** @type {Set<string>} */
  const live = new Set();
  if (state.rows.length === 0) board.append(made("p", "quiet", state.note));
  let card = board;
  /** @type {Named | null} */
  let named = null;
  /** @type {HTMLElement | null} */
  let ignores = null;
  for (const row of state.rows) {
    if (row.kind === "word") {
      card = document.createElement("section");
      board.append(card);
      card.append(worded(row));
      named = row;
      ignores = null;
      live.add(`${row.word} ${row.occurrence}`);
    } else if (row.kind === "none") {
      card.append(made("p", "quiet", EMPTY));
    } else if (row.kind === "offer") {
      card.append(offered(row));
    } else {
      if (!ignores) {
        if (named) card.append(typist(named).root);
        ignores = made("div", "ignores", "");
        card.append(ignores);
      }
      const button = pressed("ignore", { type: "ignore", flag: row.flag, tier: row.tier });
      button.textContent = row.label;
      ignores.append(button);
    }
  }
  for (const key of drafts.keys()) {
    if (!live.has(key)) drafts.delete(key);
  }
}

const lookup = writer(0, (fix) => ({ type: "copy", text: fix }), COPY);
lookup.root.classList.add("lookup");
board.before(lookup.root);

window.addEventListener("message", (event) => {
  const message = event.data;
  if (message.type === "written") {
    const held = waiting.get(message.id);
    waiting.delete(message.id);
    if (held) held.answer(message.id, message.rows, message.note);
  } else if (message.type === "state") {
    painted(message.state);
  }
});
bridge.postMessage({ type: "ready" });
