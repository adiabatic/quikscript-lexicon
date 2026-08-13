const source = document.getElementById("source");
const preview = document.getElementById("preview");
const grade = document.getElementById("grade");
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
const IGNORE_ONE_TITLE = "Ignore this occurrence alone";
const IGNORE_ALL_TITLE = "Ignore this spelling everywhere, now and in future sessions";
const KEPT = "qs-desk.ignored";
const CHOSEN = "qs-desk.senior";
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
const misses = new Map();

function spot(word, occurrence) {
  return `${word}\t${occurrence}`;
}

function recalled() {
  try {
    return localStorage.getItem(CHOSEN) !== JUNIOR_GRADE;
  } catch {
    return true;
  }
}

function isSenior() {
  return grade.getAttribute("aria-pressed") === "true";
}

function paint(senior) {
  grade.setAttribute("aria-pressed", String(senior));
  grade.textContent = senior ? "Senior" : "Junior";
}

function keep() {
  try {
    localStorage.setItem(CHOSEN, isSenior() ? SENIOR_GRADE : JUNIOR_GRADE);
  } catch {}
}

let pending = 0;
let restore = 0;
let anchor = null;

function advice() {
  return {
    active: ACCEPTED,
    freq: counts,
    groups: QS.confusions,
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
      if (overlooked.has(spot(hit.word, occurrence))) continue;
      if (!accepts(ACCEPTED, hit.word)) {
        flagged.push([hit, occurrence]);
        const held = misses.get(hit.word);
        if (held) held.push(occurrence);
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
  mark();
}

function tally() {
  const held = ignored.size + overlooked.size;
  excused.hidden = held === 0;
  excused.textContent = `Unignore ${held}`;
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

function renumber(word, swept) {
  const lead = `${word}\t`;
  const kept = [];
  for (const key of overlooked) {
    if (key.startsWith(lead)) kept.push(Number(key.slice(lead.length)));
  }
  if (kept.length === 0) return;
  const dropped = [...new Set(swept)].sort((one, other) => one - other);
  for (const index of kept) overlooked.delete(spot(word, index));
  for (const index of kept) {
    const below = dropped.filter((occurrence) => occurrence < index).length;
    overlooked.add(spot(word, index - below));
  }
}

function choose(word, occurrence, fix) {
  source.value = replaceOccurrence(source.value, word, occurrence, fix);
  renumber(word, [occurrence]);
  render();
}

function chooseAll(word, occurrences, fix) {
  source.value = replaceOccurrences(source.value, word, occurrences, fix);
  renumber(word, occurrences);
  render();
}

function propose(span) {
  const word = span.dataset.w;
  const occurrence = Number(span.dataset.occ);
  const everywhere = misses.get(word) || [occurrence];
  const others = everywhere.length - 1;
  const rest = others === 1 ? "the 1 other" : `the ${others} others`;
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
    const row = document.createElement("div");
    row.className = "offer";
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = fix;
    button.addEventListener("click", () => choose(word, occurrence, fix));
    row.append(button);
    if (others > 0) {
      const all = document.createElement("button");
      all.type = "button";
      all.className = "all";
      all.textContent = `(${others})`;
      all.title = `Correct this misspelling and ${rest} written the same way`;
      all.addEventListener("click", () => chooseAll(word, everywhere, fix));
      row.append(all);
    }
    fixer.append(row);
  }
  const once = document.createElement("button");
  once.type = "button";
  once.className = "ignore";
  once.textContent = IGNORE_ONE;
  once.title = IGNORE_ONE_TITLE;
  once.addEventListener("click", () => overlook(word, occurrence));
  fixer.append(once);
  const leave = document.createElement("button");
  leave.type = "button";
  leave.className = "ignore";
  leave.textContent = others > 0 ? `${IGNORE_ALL} (${others})` : IGNORE_ALL;
  leave.title = IGNORE_ALL_TITLE;
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
  preview.classList.toggle("senior", isSenior());
  fixer.classList.toggle("senior", isSenior());
}

source.addEventListener("input", schedule);

grade.addEventListener("click", () => {
  paint(!isSenior());
  keep();
  regrade();
});

preview.addEventListener("click", (event) => {
  const span = event.target.closest?.(".miss");
  if (span) {
    event.preventDefault();
    propose(span);
  }
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
paint(recalled());
regrade();
tally();
render();
