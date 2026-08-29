/** @typedef {import("../lib/panel.js").Named} Named */
/** @typedef {import("../lib/panel.js").Offered} Offered */
/** @typedef {import("../lib/panel.js").State} State */
/** @typedef {{postMessage(message: unknown): void}} Bridge */

const EMPTY = "No suggestions";

const bridge = /** @type {{acquireVsCodeApi(): Bridge}} */ (
  /** @type {unknown} */ (globalThis)
).acquireVsCodeApi();
const board = /** @type {HTMLElement} */ (document.querySelector("main"));

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
 * @param {Offered} row
 * @returns {HTMLElement}
 */
function offered(row) {
  const held = document.createElement("div");
  held.className = "offer";
  const button = pressed("fix", { type: "fix", flag: row.flag, at: row.at, sweep: false });
  button.append(made("span", "text", row.fix));
  if (row.gloss) button.append(made("span", "gloss", row.gloss));
  held.append(button);
  if (row.others > 0) {
    const rest = row.others === 1 ? "the 1 other" : `the ${row.others} others`;
    const all = pressed("all", { type: "fix", flag: row.flag, at: row.at, sweep: true });
    all.textContent = `(${row.others})`;
    all.title = `Correct this misspelling and ${rest} written the same way`;
    held.append(all);
  }
  return held;
}

/** @param {State} state */
function painted(state) {
  board.replaceChildren();
  if (state.rows.length === 0) {
    board.append(made("p", "quiet", state.note));
    return;
  }
  let card = board;
  for (const row of state.rows) {
    if (row.kind === "word") {
      card = document.createElement("section");
      board.append(card);
      card.append(worded(row));
    } else if (row.kind === "none") {
      card.append(made("p", "quiet", EMPTY));
    } else if (row.kind === "offer") {
      card.append(offered(row));
    } else {
      const button = pressed("ignore", { type: "ignore", flag: row.flag, tier: row.tier });
      button.textContent = row.label;
      card.append(button);
    }
  }
}

window.addEventListener("message", (event) => painted(event.data));
bridge.postMessage({ type: "ready" });
