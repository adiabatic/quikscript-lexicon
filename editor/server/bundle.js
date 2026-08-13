const { chmodSync } = require("node:fs");
const path = require("node:path");
const { buildSync } = require("esbuild");

/** @param {string} outfile */
function bundle(outfile) {
  buildSync({
    entryPoints: [path.join(__dirname, "server.js")],
    bundle: true,
    platform: "node",
    target: "node20",
    format: "cjs",
    charset: "utf8",
    banner: { js: "#!/usr/bin/env node" },
    outfile,
  });
  chmodSync(outfile, 0o755);
  return outfile;
}

if (require.main === module) {
  const out = process.argv[2];
  if (!out) {
    console.error("usage: node bundle.js <outfile>");
    process.exit(2);
  }
  console.log(`wrote ${bundle(out)}`);
}

module.exports = { bundle };
