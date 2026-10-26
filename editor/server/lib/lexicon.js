/** @typedef {{words: string, try_order: string, rep: string[][], confusions: string[]}} Payload */
/** @typedef {{active: Set<string>, counts: Map<string, number>, groups: readonly string[], letters: string, rep: readonly string[][]}} Lexicon */

/**
 * @param {Payload} data
 * @returns {Lexicon}
 */
function lexicon(data) {
  /** @type {Map<string, number>} */
  const counts = new Map();
  for (const line of data.words.split("\n")) {
    const tab = line.indexOf("\t");
    if (tab < 0) counts.set(line, 0);
    else counts.set(line.slice(0, tab), Number(line.slice(tab + 1)));
  }
  return {
    active: new Set(counts.keys()),
    counts,
    groups: data.confusions,
    letters: data.try_order,
    rep: data.rep,
  };
}

module.exports = { lexicon };
