const latin = document.getElementById("latin");
const lookupForm = document.getElementById("lookup");
const results = document.getElementById("results");
const copyStatus = document.getElementById("status");

const DELAY = 150;
const COPY_TITLE = "Copy this spelling";
const COPIED = "Copied";
const APPLE = /Mac|iPhone|iPad|iPod/.test(
  navigator.userAgentData?.platform || navigator.platform || "",
);
const MANUAL_COPY = `Press ${APPLE ? "⌘C" : "Ctrl+C"} to copy`;

let spellingsByLatin = null;
let pending = 0;

function loadedSpellings() {
  if (!spellingsByLatin) spellingsByLatin = parseSpellingsByLatin(QS);
  return spellingsByLatin;
}

function quikscript(spelling) {
  const text = document.createElement("span");
  text.className = "text";
  text.lang = "en-Qaas";
  text.textContent = spelling;
  return text;
}

function note(message) {
  const paragraph = document.createElement("p");
  paragraph.className = "note";
  paragraph.textContent = message;
  return paragraph;
}

function copied(spelling) {
  copyStatus.replaceChildren(COPIED, quikscript(spelling));
}

function selectForManualCopy(text) {
  window.getSelection()?.selectAllChildren(text);
  copyStatus.replaceChildren(MANUAL_COPY);
}

function copy(spelling, text) {
  if (!navigator.clipboard) {
    selectForManualCopy(text);
    return;
  }
  navigator.clipboard.writeText(spelling).then(
    () => copied(spelling),
    () => selectForManualCopy(text),
  );
}

function spellingButton(spelling, gloss) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "spelling";
  button.title = COPY_TITLE;
  const text = quikscript(spelling);
  button.append(text);
  if (gloss) {
    const detail = document.createElement("span");
    detail.className = "gloss";
    detail.textContent = gloss;
    button.append(detail);
  }
  button.addEventListener("click", () => copy(spelling, text));
  return button;
}

function show() {
  clearTimeout(pending);
  copyStatus.replaceChildren();
  results.replaceChildren();
  const words = lookupSpellings(latin.value, loadedSpellings());
  if (words.length > 1 && words.every((word) => word.items.length > 0)) {
    results.append(spellingButton(words.map((word) => word.items[0].label).join(" "), ""));
  }
  for (const word of words) {
    if (word.items.length === 0) {
      results.append(note(`No spelling for ${word.latin}`));
      continue;
    }
    for (const item of word.items) {
      const gloss = words.length > 1 ? `${word.latin} — ${item.detail}` : item.detail;
      results.append(spellingButton(item.label, gloss));
    }
  }
}

latin.addEventListener("input", () => {
  clearTimeout(pending);
  pending = setTimeout(show, DELAY);
});

lookupForm.addEventListener("submit", (event) => {
  event.preventDefault();
  show();
  results.querySelector("button")?.click();
});
