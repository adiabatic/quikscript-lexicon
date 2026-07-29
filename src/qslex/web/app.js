const source = document.getElementById("source");
const preview = document.getElementById("preview");
const grade = document.getElementById("senior");
const fixer = document.getElementById("fixer");
const copier = document.getElementById("copy");
const excused = document.getElementById("ignored");

const DELAY = 150;
const HELD = 1500;
const GAP = 4;
const EDGE = 8;
const ANCHOR = "--qs-miss";
const ANCHORING = typeof CSS !== "undefined" && CSS.supports("anchor-name: --qs");
const RESTING = copier.textContent;
const EMPTY = "No suggestions";
const DONE = "Copied";
const BY_HAND = "Press ⌘C";
const IGNORE_ONE = "Ignore one";
const IGNORE_ALL = "Ignore all";
const KEPT = "qs-playground.ignored";
const CHOSEN = "qs-playground.senior";
const SENIOR_GRADE = "senior";
const JUNIOR_GRADE = "junior";

const counts = new Map();
for (const line of QS.words.split("\n")) {
  const tab = line.indexOf("\t");
  if (tab < 0) counts.set(line, 0);
  else counts.set(line.slice(0, tab), Number(line.slice(tab + 1)));
}

const ACCEPTED = new Set(counts.keys());

function remembered() {
  try {
    const held = JSON.parse(localStorage.getItem(KEPT) || "[]");
    return Array.isArray(held) ? held.filter((word) => typeof word === "string") : [];
  } catch {
    return [];
  }
}

const ignored = new Set(remembered());
const overlooked = new Set();

function spot(word, occurrence) {
  return `${word}\t${occurrence}`;
}

function recalled() {
  try {
    return localStorage.getItem(CHOSEN) === SENIOR_GRADE;
  } catch {
    return false;
  }
}

function keep() {
  try {
    localStorage.setItem(CHOSEN, grade.checked ? SENIOR_GRADE : JUNIOR_GRADE);
  } catch {}
}

let pending = 0;
let restore = 0;
let anchor = null;

function advice() {
  return {
    active: ACCEPTED,
    freq: counts,
    letters: QS.try_order,
    rep: QS.rep,
  };
}

function skipped(node) {
  for (let held = node.parentNode; held && held !== preview; held = held.parentNode) {
    if (held.nodeType !== Node.ELEMENT_NODE) continue;
    if (held.tagName === "PRE" || held.tagName === "CODE") return true;
    if (held.hasAttribute("popover")) return true;
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
    span.textContent = hit.word;
    pieces.append(span);
    at = hit.end;
  }
  if (at < written.length) pieces.append(document.createTextNode(written.slice(at)));
  text.replaceWith(pieces);
}

function mark() {
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
      if (overlooked.has(spot(hit.word, occurrence))) continue;
      if (!accepts(ACCEPTED, hit.word)) flagged.push([hit, occurrence]);
    }
    if (flagged.length > 0) wrap(text, flagged);
  }
}

function render() {
  clearTimeout(pending);
  dismiss();
  preview.innerHTML = marked.parse(stripFrontMatter(source.value));
  mark();
}

function tally() {
  const held = ignored.size + overlooked.size;
  excused.hidden = held === 0;
  excused.textContent = `Ignored: ${held} — clear`;
}

function store() {
  try {
    localStorage.setItem(KEPT, JSON.stringify([...ignored]));
  } catch {}
}

function revise() {
  store();
  tally();
  render();
}

function excuse(word) {
  ignored.add(word);
  for (const key of overlooked) {
    if (key.startsWith(`${word}\t`)) overlooked.delete(key);
  }
  revise();
}

function overlook(word, occurrence) {
  overlooked.add(spot(word, occurrence));
  tally();
  render();
}

function schedule() {
  clearTimeout(pending);
  pending = setTimeout(render, DELAY);
}

function dismiss() {
  if (fixer.matches(":popover-open")) fixer.hidePopover();
}

function pin(span) {
  const box = span.getBoundingClientRect();
  const own = fixer.getBoundingClientRect();
  const rightmost = window.innerWidth - own.width - EDGE;
  const lowest = window.innerHeight - own.height - EDGE;
  const under = box.bottom + GAP;
  const over = box.top - own.height - GAP;
  fixer.style.left = `${Math.max(EDGE, Math.min(box.left, rightmost))}px`;
  fixer.style.top = `${under <= lowest ? under : Math.max(EDGE, Math.min(over, lowest))}px`;
}

function choose(word, occurrence, fix) {
  source.value = replaceOccurrence(source.value, word, occurrence, fix);
  render();
}

function propose(span) {
  const word = span.dataset.w;
  const occurrence = Number(span.dataset.occ);
  const offers = suggest(word, advice());

  fixer.replaceChildren();
  const heading = document.createElement("div");
  heading.className = "word";
  heading.textContent = word;
  fixer.append(heading);
  if (offers.length === 0) {
    const none = document.createElement("p");
    none.className = "none";
    none.textContent = EMPTY;
    fixer.append(none);
  }
  for (const fix of offers) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = fix;
    button.addEventListener("click", () => choose(word, occurrence, fix));
    fixer.append(button);
  }
  const once = document.createElement("button");
  once.type = "button";
  once.className = "ignore";
  once.textContent = IGNORE_ONE;
  once.addEventListener("click", () => overlook(word, occurrence));
  fixer.append(once);
  const leave = document.createElement("button");
  leave.type = "button";
  leave.className = "ignore";
  leave.textContent = IGNORE_ALL;
  leave.addEventListener("click", () => excuse(word));
  fixer.append(leave);

  if (ANCHORING) {
    if (anchor) anchor.style.removeProperty("anchor-name");
    anchor = span;
    span.style.setProperty("anchor-name", ANCHOR);
  }
  if (!fixer.matches(":popover-open")) fixer.showPopover();
  if (!ANCHORING) pin(span);
}

function flip(text) {
  copier.textContent = text;
  clearTimeout(restore);
  restore = setTimeout(() => {
    copier.textContent = RESTING;
  }, HELD);
}

function byHand() {
  source.focus();
  source.select();
  flip(BY_HAND);
}

function regrade() {
  preview.classList.toggle("senior", grade.checked);
  fixer.classList.toggle("senior", grade.checked);
}

source.addEventListener("input", schedule);

grade.addEventListener("change", () => {
  keep();
  regrade();
});

preview.addEventListener("click", (event) => {
  const span = event.target.closest?.(".miss");
  if (span) propose(span);
});

excused.addEventListener("click", () => {
  ignored.clear();
  overlooked.clear();
  revise();
});

copier.addEventListener("click", () => {
  if (!navigator.clipboard) {
    byHand();
    return;
  }
  navigator.clipboard.writeText(source.value).then(() => flip(DONE), byHand);
});

marked.use({ gfm: true });
if (ANCHORING) fixer.classList.add("anchored");
grade.checked = recalled();
regrade();
tally();
render();
