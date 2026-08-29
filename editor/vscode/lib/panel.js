/** @typedef {{line: number, character: number}} Position */
/** @typedef {{start: Position, end: Position}} Span */
/** @typedef {{range: Span, newText: string}} Edit */
/** @typedef {{changes: Record<string, Edit[]>}} Change */
/** @typedef {{command: string, arguments: unknown[]}} Order */
/** @typedef {{fix: string, gloss: string, edit: Change}} Offer */
/** @typedef {"occurrence" | "project" | "user"} Tier */
/** @typedef {{occurrence: Order, project: Order | null, user: Order}} Ignore */
/** @typedef {{word: string, occurrence: number, range: Span, spans: Span[], fixes: Offer[], ignore: Ignore}} Fixed */
/** @typedef {{uri: string, flags: Fixed[]}} Held */
/** @typedef {{kind: "word", flag: number, word: string, line: number, character: number}} Named */
/** @typedef {{kind: "none"}} Blank */
/** @typedef {{kind: "offer", flag: number, at: number, fix: string, gloss: string, others: number}} Offered */
/** @typedef {{kind: "ignore", flag: number, tier: Tier, label: string}} Told */
/** @typedef {Named | Blank | Offered | Told} Row */
/** @typedef {{type: "fix", flag: number, at: number, sweep: boolean}} Chosen */
/** @typedef {{type: "ignore", flag: number, tier: Tier}} Excused */
/** @typedef {{type: "reveal", flag: number}} Sought */
/** @typedef {Chosen | Excused | Sought} Message */
/** @typedef {{edit: Change} | {order: Order} | {range: Span} | null} Answer */
/** @typedef {{rows: Row[], note: string}} State */

/** @type {[Tier, string][]} */
const TIERS = [
  ["occurrence", "Ignore this occurrence"],
  ["project", "Ignore in this project"],
  ["user", "Ignore everywhere"],
];

/**
 * @param {Fixed[]} flags
 * @returns {Row[]}
 */
function rows(flags) {
  /** @type {Row[]} */
  const out = [];
  for (const [flag, held] of flags.entries()) {
    const { line, character } = held.range.start;
    out.push({ kind: "word", flag, word: held.word, line, character });
    if (held.fixes.length === 0) out.push({ kind: "none" });
    const others = held.spans.length - 1;
    for (const [at, offer] of held.fixes.entries()) {
      out.push({ kind: "offer", flag, at, fix: offer.fix, gloss: offer.gloss, others });
    }
    for (const [tier, label] of TIERS) {
      if (held.ignore[tier]) out.push({ kind: "ignore", flag, tier, label });
    }
  }
  return out;
}

/**
 * @param {Held} held
 * @param {Message} message
 * @returns {Answer}
 */
function resolved(held, message) {
  const flag = held.flags[message.flag];
  if (!flag) return null;
  if (message.type === "reveal") return { range: flag.range };
  if (message.type === "ignore") {
    const order = flag.ignore[message.tier];
    return order ? { order } : null;
  }
  const offer = flag.fixes[message.at];
  if (!offer) return null;
  if (!message.sweep) return { edit: offer.edit };
  const changes = flag.spans.map((span) => ({ range: span, newText: offer.fix }));
  return { edit: { changes: { [held.uri]: changes } } };
}

/**
 * @param {{csp: string, styles: string[], script: string}} parts
 * @returns {string}
 */
function shell({ csp, styles, script }) {
  const policy = `default-src 'none'; font-src ${csp} data:; style-src ${csp}; script-src ${csp};`;
  return [
    "<!doctype html>",
    '<html lang="en">',
    "<head>",
    '<meta charset="utf-8">',
    `<meta http-equiv="Content-Security-Policy" content="${policy}">`,
    ...styles.map((href) => `<link rel="stylesheet" href="${href}">`),
    "</head>",
    "<body>",
    "<main></main>",
    `<script src="${script}"></script>`,
    "</body>",
    "</html>",
  ].join("\n");
}

module.exports = { resolved, rows, shell };
