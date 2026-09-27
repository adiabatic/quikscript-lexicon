const source = document.getElementById("source");
const preview = document.getElementById("preview");
const grade = document.getElementById("grade");
const popover = document.getElementById("popover");
const copyButton = document.getElementById("copy");
const undoButton = document.getElementById("undo");
const unignoreButton = document.getElementById("unignore");

const DELAY = 150;
const COPY_LABEL_MS = 1500;
const GAP = 4;
const EDGE = 8;
const ANCHOR = "--qs-miss";
const SUPPORTS_ANCHOR = typeof CSS !== "undefined" && CSS.supports("anchor-name: --qs");
const COPY_LABEL = copyButton.textContent;
const EMPTY = "No suggestions";
const COPIED_LABEL = "Copied";
const MANUAL_COPY_LABEL = "Press ⌘C";
const IGNORE_ONE = "Ignore one";
const IGNORE_ALL = "Ignore all";
const IGNORE_ONE_TITLE = "Ignore this occurrence alone";
const IGNORE_ALL_TITLE = "Ignore this spelling everywhere in this browser";
const IGNORED_STORAGE_KEY = "qs-desk.ignored";
const GRADE_STORAGE_KEY = "qs-desk.senior";
const SENIOR_GRADE = "senior";
const JUNIOR_GRADE = "junior";
const APPLE = /Mac|iPhone|iPad|iPod/.test(
  navigator.userAgentData?.platform || navigator.platform || "",
);

const counts = new Map();
for (const line of QS.words.split("\n")) {
  const tab = line.indexOf("\t");
  if (tab < 0) counts.set(line, 0);
  else counts.set(line.slice(0, tab), Number(line.slice(tab + 1)));
}

const ACCEPTED = new Set(counts.keys());

function loadIgnored() {
  try {
    const stored = JSON.parse(localStorage.getItem(IGNORED_STORAGE_KEY) || "[]");
    return Array.isArray(stored) ? stored.filter((word) => typeof word === "string") : [];
  } catch {
    return [];
  }
}

const ignored = new Set(loadIgnored());
const ignoredOccurrences = new Set();
const misses = new Map();
const corrections = [];

function occurrenceKey(word, occurrence) {
  return `${word}\t${occurrence}`;
}

function loadSeniorPreference() {
  try {
    return localStorage.getItem(GRADE_STORAGE_KEY) !== JUNIOR_GRADE;
  } catch {
    return true;
  }
}

function isSenior() {
  return grade.getAttribute("aria-pressed") === "true";
}

function setGrade(senior) {
  grade.setAttribute("aria-pressed", String(senior));
  grade.textContent = senior ? "Senior" : "Junior";
}

function saveGrade() {
  try {
    localStorage.setItem(GRADE_STORAGE_KEY, isSenior() ? SENIOR_GRADE : JUNIOR_GRADE);
  } catch {}
}

let pending = 0;
let restore = 0;
let anchor = null;

function suggestContext() {
  return {
    active: ACCEPTED,
    freq: counts,
    groups: QS.confusions,
    letters: QS.try_order,
    rep: QS.rep,
  };
}

function skipped(node) {
  for (
    let ancestor = node.parentNode;
    ancestor && ancestor !== preview;
    ancestor = ancestor.parentNode
  ) {
    if (ancestor.nodeType !== Node.ELEMENT_NODE) continue;
    if (ancestor.tagName === "PRE" || ancestor.tagName === "CODE") return true;
    if (ancestor.hasAttribute("popover")) return true;
  }
  return false;
}

function wrap(text, flagged) {
  const written = text.data;
  const pieces = document.createDocumentFragment();
  let at = 0;
  for (const [hit, occurrence] of flagged) {
    if (hit.start > at) {
      pieces.append(document.createTextNode(written.slice(at, hit.start)));
    }
    const span = document.createElement("span");
    span.className = "miss";
    span.dataset.w = hit.word;
    span.dataset.occ = String(occurrence);
    span.textContent = written.slice(hit.start, hit.end);
    pieces.append(span);
    at = hit.end;
  }
  if (at < written.length) pieces.append(document.createTextNode(written.slice(at)));
  text.replaceWith(pieces);
}

function markMisspellings() {
  misses.clear();
  const walker = document.createTreeWalker(preview, NodeFilter.SHOW_TEXT);
  const texts = [];
  for (let node = walker.nextNode(); node; node = walker.nextNode()) texts.push(node);

  const seen = new Map();
  for (const text of texts) {
    const found = tokens(text.data);
    if (found.length === 0) continue;
    const quoted = skipped(text);
    const flagged = [];
    for (const hit of found) {
      const occurrence = seen.get(hit.word) || 0;
      seen.set(hit.word, occurrence + 1);
      if (quoted || ignored.has(hit.word)) continue;
      if (ignoredOccurrences.has(occurrenceKey(hit.word, occurrence))) continue;
      if (!accepts(ACCEPTED, hit.word)) {
        flagged.push([hit, occurrence]);
        const occurrences = misses.get(hit.word);
        if (occurrences) occurrences.push(occurrence);
        else misses.set(hit.word, [occurrence]);
      }
    }
    if (flagged.length > 0) wrap(text, flagged);
  }
}

function render() {
  clearTimeout(pending);
  dismiss();
  preview.innerHTML = marked.parse(stripFrontMatter(source.value));
  markMisspellings();
}

function updateUnignoreButton() {
  const ignoredCount = ignored.size + ignoredOccurrences.size;
  unignoreButton.hidden = ignoredCount === 0;
  unignoreButton.textContent = `Unignore ${ignoredCount}`;
}

function saveIgnoredWords() {
  try {
    localStorage.setItem(IGNORED_STORAGE_KEY, JSON.stringify([...ignored]));
  } catch {}
}

function saveAndRender() {
  saveIgnoredWords();
  updateUnignoreButton();
  render();
}

function ignoreEverywhere(word) {
  ignored.add(word);
  for (const key of ignoredOccurrences) {
    if (key.startsWith(`${word}\t`)) ignoredOccurrences.delete(key);
  }
  saveAndRender();
}

function ignoreOnce(word, occurrence) {
  ignoredOccurrences.add(occurrenceKey(word, occurrence));
  updateUnignoreButton();
  render();
}

function schedule() {
  clearTimeout(pending);
  pending = setTimeout(render, DELAY);
}

function dismiss() {
  if (popover.matches(":popover-open")) popover.hidePopover();
}

function placePopover(span) {
  const box = span.getBoundingClientRect();
  const own = popover.getBoundingClientRect();
  const rightmost = window.innerWidth - own.width - EDGE;
  const lowest = window.innerHeight - own.height - EDGE;
  const under = box.bottom + GAP;
  const over = box.top - own.height - GAP;
  popover.style.left = `${Math.max(EDGE, Math.min(box.left, rightmost))}px`;
  popover.style.top = `${under <= lowest ? under : Math.max(EDGE, Math.min(over, lowest))}px`;
}

function renumber(word, replaced) {
  const lead = `${word}\t`;
  const ignoredIndexes = [];
  for (const key of ignoredOccurrences) {
    if (key.startsWith(lead)) ignoredIndexes.push(Number(key.slice(lead.length)));
  }
  if (ignoredIndexes.length === 0) return;
  const dropped = [...new Set(replaced)].sort((one, other) => one - other);
  for (const index of ignoredIndexes) ignoredOccurrences.delete(occurrenceKey(word, index));
  for (const index of ignoredIndexes) {
    const below = dropped.filter((occurrence) => occurrence < index).length;
    ignoredOccurrences.add(occurrenceKey(word, index - below));
  }
}

function snapshot() {
  return {
    value: source.value,
    start: source.selectionStart,
    end: source.selectionEnd,
    direction: source.selectionDirection,
    ignoredOccurrences: [...ignoredOccurrences],
  };
}

function updateUndo() {
  undoButton.disabled = corrections.length === 0;
}

function correct(value, word, occurrences) {
  if (value === source.value) return;
  corrections.push(snapshot());
  source.value = value;
  renumber(word, occurrences);
  updateUndo();
  render();
}

function choose(word, occurrence, fix) {
  correct(replaceOccurrence(source.value, word, occurrence, fix), word, [
    occurrence,
  ]);
}

function chooseAll(word, occurrences, fix) {
  correct(replaceOccurrences(source.value, word, occurrences, fix), word, occurrences);
}

function undo() {
  const previous = corrections.pop();
  if (!previous) return;
  source.value = previous.value;
  ignoredOccurrences.clear();
  for (const key of previous.ignoredOccurrences) ignoredOccurrences.add(key);
  updateUndo();
  updateUnignoreButton();
  render();
  source.focus();
  if (Number.isInteger(previous.start) && Number.isInteger(previous.end)) {
    source.setSelectionRange(previous.start, previous.end, previous.direction || "none");
  }
}

function showSuggestions(span) {
  const word = span.dataset.w;
  const occurrence = Number(span.dataset.occ);
  const everywhere = misses.get(word) || [occurrence];
  const others = everywhere.length - 1;
  const rest = others === 1 ? "the 1 other" : `the ${others} others`;
  const suggestions = suggest(word, suggestContext());

  popover.replaceChildren();
  const heading = document.createElement("div");
  heading.className = "word";
  heading.textContent = word;
  popover.append(heading);
  if (suggestions.length === 0) {
    const none = document.createElement("p");
    none.className = "none";
    none.textContent = EMPTY;
    popover.append(none);
  }
  for (const fix of suggestions) {
    const row = document.createElement("div");
    row.className = "suggestion";
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = fix;
    button.addEventListener("click", () => choose(word, occurrence, fix));
    row.append(button);
    if (others > 0) {
      const fixAllButton = document.createElement("button");
      fixAllButton.type = "button";
      fixAllButton.className = "fix-all";
      fixAllButton.textContent = `(${others})`;
      fixAllButton.title = `Correct this misspelling and ${rest} written the same way`;
      fixAllButton.addEventListener("click", () => chooseAll(word, everywhere, fix));
      row.append(fixAllButton);
    }
    popover.append(row);
  }
  const ignoreOneButton = document.createElement("button");
  ignoreOneButton.type = "button";
  ignoreOneButton.className = "ignore";
  ignoreOneButton.textContent = IGNORE_ONE;
  ignoreOneButton.title = IGNORE_ONE_TITLE;
  ignoreOneButton.addEventListener("click", () => ignoreOnce(word, occurrence));
  popover.append(ignoreOneButton);
  const ignoreAllButton = document.createElement("button");
  ignoreAllButton.type = "button";
  ignoreAllButton.className = "ignore";
  ignoreAllButton.textContent = others > 0 ? `${IGNORE_ALL} (${others})` : IGNORE_ALL;
  ignoreAllButton.title = IGNORE_ALL_TITLE;
  ignoreAllButton.addEventListener("click", () => ignoreEverywhere(word));
  popover.append(ignoreAllButton);

  if (SUPPORTS_ANCHOR) {
    if (anchor) anchor.style.removeProperty("anchor-name");
    anchor = span;
    span.style.setProperty("anchor-name", ANCHOR);
  }
  if (!popover.matches(":popover-open")) popover.showPopover();
  if (!SUPPORTS_ANCHOR) placePopover(span);
}

function flashCopyLabel(text) {
  copyButton.textContent = text;
  clearTimeout(restore);
  restore = setTimeout(() => {
    copyButton.textContent = COPY_LABEL;
  }, COPY_LABEL_MS);
}

function selectForManualCopy() {
  source.focus();
  source.select();
  flashCopyLabel(MANUAL_COPY_LABEL);
}

function applyGrade() {
  preview.classList.toggle("senior", isSenior());
  popover.classList.toggle("senior", isSenior());
}

source.addEventListener("input", () => {
  corrections.length = 0;
  updateUndo();
  schedule();
});

undoButton.addEventListener("click", undo);

document.addEventListener("keydown", (event) => {
  const modified = APPLE ? event.metaKey : event.ctrlKey;
  if (
    event.key.toLowerCase() !== "z" ||
    !modified ||
    event.altKey ||
    event.shiftKey ||
    corrections.length === 0
  ) {
    return;
  }
  event.preventDefault();
  undo();
});

grade.addEventListener("click", () => {
  setGrade(!isSenior());
  saveGrade();
  applyGrade();
});

preview.addEventListener("click", (event) => {
  const span = event.target.closest?.(".miss");
  if (span) {
    event.preventDefault();
    showSuggestions(span);
  }
});

unignoreButton.addEventListener("click", () => {
  ignored.clear();
  ignoredOccurrences.clear();
  saveAndRender();
});

copyButton.addEventListener("click", () => {
  if (!navigator.clipboard) {
    selectForManualCopy();
    return;
  }
  navigator.clipboard
    .writeText(source.value)
    .then(() => flashCopyLabel(COPIED_LABEL), selectForManualCopy);
});

marked.use({ gfm: true });
if (SUPPORTS_ANCHOR) popover.classList.add("anchored");
undoButton.title = `Undo last correction (${APPLE ? "⌘Z" : "Ctrl+Z"})`;
setGrade(loadSeniorPreference());
applyGrade();
updateUnignoreButton();
updateUndo();
render();
