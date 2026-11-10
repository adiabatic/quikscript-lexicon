/** @typedef {{latin_by_spelling: string, spellings_by_latin: string}} LookupMaps */
/** @typedef {{latin: string, pos: string, column: string}} LatinEntry */
/** @typedef {{pos: string, frequency: number, senior: string, junior: string, x: string}} SpellingEntry */
/** @typedef {{label: string, detail: string, sortText: string}} Item */

const SENIOR = "senior";
const JUNIOR = "junior";
const X = "x";
const CONTRACTION = "contraction";
const LETTER = /[A-Za-z]/;
const CURLY = /’/g;
const TRAILING = /'+$/;
const HYPHEN = "-";
const RUN = /[A-Za-z'’-]+/g;
const MAX_LOOKUP_WORDS = 20;
/** @type {Record<string, string>} */
const COLUMN_LABEL = { [SENIOR]: "Senior", [JUNIOR]: "Junior", [X]: "X-letter" };

const POS_LABEL = {
  AJ0: "adjective",
  AJC: "comparative adjective",
  AJS: "superlative adjective",
  AT0: "article",
  AV0: "adverb",
  AVP: "adverbial particle",
  AVQ: "interrogative adverb",
  CJC: "conjunction",
  CJS: "subordinating conjunction",
  CJT: "conjunction",
  CRD: "cardinal number",
  DPS: "possessive determiner",
  DT0: "determiner",
  DTQ: "interrogative determiner",
  EX0: "existential there",
  INT: "interjection",
  ITJ: "interjection",
  NN0: "noun",
  NN1: "singular noun",
  NN2: "plural noun",
  NP0: "proper noun",
  ORD: "ordinal number",
  PNI: "indefinite pronoun",
  PNP: "personal pronoun",
  PNQ: "interrogative pronoun",
  PNX: "reflexive pronoun",
  POS: "possessive marker",
  PRF: "preposition",
  PRP: "preposition",
  TO0: "infinitive marker",
  VBB: "verb",
  VBD: "past-tense verb",
  VBG: "-ing verb",
  VBI: "infinitive",
  VBN: "past participle",
  VBZ: "-s verb",
  VDB: "verb",
  VDD: "past-tense verb",
  VDG: "-ing verb",
  VDI: "infinitive",
  VDN: "past participle",
  VDZ: "-s verb",
  VHB: "verb",
  VHD: "past-tense verb",
  VHG: "-ing verb",
  VHI: "infinitive",
  VHN: "past participle",
  VHZ: "-s verb",
  VM0: "modal verb",
  VVB: "verb",
  VVD: "past-tense verb",
  VVG: "-ing verb",
  VVI: "infinitive",
  VVN: "past participle",
  VVZ: "-s verb",
  XX0: "not",
  ZZ0: "letter",
};

/**
 * @param {string} pos
 * @returns {string}
 */
function label(pos) {
  return pos
    .split("+")
    .map((tag) => /** @type {Record<string, string>} */ (POS_LABEL)[tag] || tag)
    .join(" + ");
}

/**
 * @param {SpellingEntry} row
 * @param {string} column
 * @returns {string}
 */
function spellingIn(row, column) {
  if (column === SENIOR) return row.senior;
  if (column === JUNIOR) return row.junior;
  return row.x;
}

/**
 * @param {LookupMaps} data
 * @returns {Map<string, LatinEntry[]>}
 */
function parseLatinBySpelling(data) {
  /** @type {Map<string, LatinEntry[]>} */
  const out = new Map();
  for (const line of data.latin_by_spelling.split("\n")) {
    if (!line) continue;
    const [spelling, latin, pos, column] = line.split("\t");
    const entry = { latin, pos, column };
    const entries = out.get(spelling);
    if (entries) entries.push(entry);
    else out.set(spelling, [entry]);
  }
  return out;
}

/**
 * @param {LookupMaps} data
 * @returns {Map<string, SpellingEntry[]>}
 */
function parseSpellingsByLatin(data) {
  /** @type {Map<string, SpellingEntry[]>} */
  const out = new Map();
  for (const line of data.spellings_by_latin.split("\n")) {
    if (!line) continue;
    const [latin, pos, frequency, senior, junior, x] = line.split("\t");
    const row = { pos, frequency: Number(frequency), senior, junior, x };
    const rows = out.get(latin);
    if (rows) rows.push(row);
    else out.set(latin, [row]);
  }
  return out;
}

/**
 * @param {SpellingEntry[]} senses
 * @returns {Item[]}
 */
function items(senses) {
  /** @type {Map<string, {labels: string[], frequency: number, columns: Set<string>}>} */
  const merged = new Map();
  for (const sense of senses) {
    for (const column of [SENIOR, JUNIOR, X]) {
      const form = spellingIn(sense, column);
      if (!form) continue;
      const posLabel = label(sense.pos);
      const entry = merged.get(form);
      if (entry) {
        if (!entry.labels.includes(posLabel)) entry.labels.push(posLabel);
        entry.frequency = Math.max(entry.frequency, sense.frequency);
        entry.columns.add(column);
      } else {
        merged.set(form, {
          labels: [posLabel],
          frequency: sense.frequency,
          columns: new Set([column]),
        });
      }
    }
  }
  const ranked = [...merged].sort(
    ([oneForm, one], [otherForm, other]) =>
      other.frequency - one.frequency ||
      Number(!one.columns.has(SENIOR)) - Number(!other.columns.has(SENIOR)) ||
      (oneForm < otherForm ? -1 : 1),
  );
  return ranked.map(([form, entry], at) => ({
    label: form,
    detail: entry.columns.has(SENIOR)
      ? entry.labels.join(", ")
      : `${entry.labels.join(", ")} — ${[...entry.columns]
          .map((column) => COLUMN_LABEL[column])
          .join(", ")} form`,
    sortText: String(at).padStart(4, "0"),
  }));
}

/**
 * @param {string} text
 * @param {Map<string, SpellingEntry[]>} spellingsByLatin
 * @returns {{latin: string, items: Item[]}[]}
 */
function lookupSpellings(text, spellingsByLatin) {
  /** @type {{latin: string, items: Item[]}[]} */
  const out = [];
  for (const [run] of text.matchAll(RUN)) {
    if (!LETTER.test(run)) continue;
    const key = run.toLowerCase().replace(CURLY, "'").replace(TRAILING, "");
    const senses = spellingsByLatin.get(key);
    const pieces = senses || !key.includes(HYPHEN) ? [key] : key.split(HYPHEN);
    for (const piece of pieces) {
      if (out.length >= MAX_LOOKUP_WORDS) return out;
      if (!LETTER.test(piece)) continue;
      const matches = spellingsByLatin.get(piece);
      out.push({ latin: piece, items: matches ? items(matches) : [] });
    }
  }
  return out;
}

if (typeof module !== "undefined") {
  module.exports = {
    COLUMN_LABEL,
    CONTRACTION,
    JUNIOR,
    SENIOR,
    X,
    items,
    label,
    lookupSpellings,
    parseLatinBySpelling,
    parseSpellingsByLatin,
    spellingIn,
  };
}
