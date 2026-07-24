from __future__ import annotations

import argparse
import collections
import re
import sys
from pathlib import Path

from qslex.mapping import Mapping, load_mapping, repo_root
from qslex.quirks import load_quirks, normalize
from qslex.tokenizer import STRESS_MARKS, TokenizeError, tokenize

EXPECTED_TOKEN_COUNTS = {
    ("R", ""): 27317,
    ("Ə", ""): 7778,
    ("I", ""): 616,
    ("Æ", ""): 1707,
    ("Ɑː", ""): 1705,
    ("ʍ", ""): 538,
    ("Ð", ""): 25,
    ("T", ""): 32,
    ("N", ""): 32,
    ("V", ""): 43,
    ("F", ""): 24,
    ("x", ""): 1,
    ("ɬ", ""): 1,
    ("eə", "no-r"): 3,
    ("ʊə", ""): 760,
    ("aɪə", "pre-r"): 655,
    ("aɪə", "no-r"): 549,
    ("aʊə", "pre-r"): 270,
    ("aʊə", "no-r"): 51,
}

EXPECTED_RAW_COUNTS = {
    "raw ʊə incl. inside aʊə and across əʊ+ə (issue #1's 1,229)": (r"ʊə", 1229),
}

FORBIDDEN_RAW_PATTERNS = {
    "bare ɪR (schwa-less EAR)": r"ɪ[ˈˌ]?R",
    "bare aɪR (schwa-less PRICE+R)": r"aɪ[ˈˌ]?R",
    "bare aʊR (schwa-less MOUTH+R)": r"aʊ[ˈˌ]?R",
}


def read_rows(path: Path) -> list[tuple[str, str, str, str, str]]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            fields = line.rstrip("\n").split("\t")
            if len(fields) >= 4:
                rows.append((fields[0], fields[1], fields[2], fields[3], fields[4] if len(fields) > 4 else ""))
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Tokenize every ReadLex IPA string against the mapping")
    parser.add_argument(
        "readlex",
        nargs="?",
        type=Path,
        default=repo_root() / "tmp" / "readlex" / "kingsleyreadlexicon.tsv",
    )
    args = parser.parse_args(argv)

    mapping: Mapping = load_mapping()
    quirk_rules = load_quirks()
    rows = read_rows(args.readlex)

    failures: list[str] = []
    residue: list[str] = []
    token_counts: collections.Counter[tuple[str, str]] = collections.Counter()
    quirk_hits: dict[int, set[str]] = collections.defaultdict(set)
    iea_audit: dict[str, set[str]] = {"stressed": set(), "unstressed": set(), "unmarked-multinucleus": set()}

    for word, _shavian, _pos, raw_ipa, _freq in rows:
        ipa, applied = normalize(raw_ipa, quirk_rules)
        for index in applied:
            quirk_hits[index].add(word)
        try:
            tokens = tokenize(ipa, mapping)
        except TokenizeError as error:
            residue.append(f"{word!r}: {error}")
            continue
        for token in tokens:
            token_counts[(token.ipa, token.entry.condition)] += 1
            if token.ipa == "ɪə":
                iea_audit[token.entry.condition].add(word)

    for word, _shavian, _pos, raw_ipa, _freq in rows:
        ipa, _ = normalize(raw_ipa, quirk_rules)
        for chunk in re.split(r"[ +-]", ipa):
            if "ɪə" in chunk and not any(mark in chunk for mark in STRESS_MARKS):
                if len(re.findall(r"[ɪieæaɑɒɔʊuʌəɜːÆƏIⱭ]+", chunk)) > 1:
                    iea_audit["unmarked-multinucleus"].add(word)

    print(f"rows tokenized: {len(rows)}")
    print(f"unmapped residue: {len(residue)}")
    for line in residue[:20]:
        print(f"  {line}")
    if residue:
        failures.append(f"{len(residue)} rows with unmapped residue")

    print("\nquirk rule applications:")
    for index, rule in enumerate(quirk_rules):
        words = quirk_hits.get(index, set())
        status = f"{len(words)} rows" if words else "UNUSED"
        print(f"  [{rule.scope}] {rule.match!r} -> {rule.replacement!r}: {status} ({', '.join(sorted(words)[:8])})")
        if not words:
            failures.append(f"quirk rule {rule.match!r} matched nothing")

    print("\ninvariant token counts:")
    for key, expected in EXPECTED_TOKEN_COUNTS.items():
        actual = token_counts.get(key, 0)
        marker = "ok" if actual == expected else f"MISMATCH (expected {expected})"
        print(f"  {key[0]!r} {key[1] or '-'}: {actual} {marker}")
        if actual != expected:
            failures.append(f"count mismatch for {key}: {actual} != {expected}")

    raw_blob = "\n".join(raw for _, _, _, raw, _ in rows)
    print("\nexpected raw pattern counts:")
    for label, (pattern, expected) in EXPECTED_RAW_COUNTS.items():
        count = len(re.findall(pattern, raw_blob))
        marker = "ok" if count == expected else f"MISMATCH (expected {expected})"
        print(f"  {label}: {count} {marker}")
        if count != expected:
            failures.append(f"raw count mismatch for {label}: {count} != {expected}")

    print("\nforbidden raw patterns:")
    for label, pattern in FORBIDDEN_RAW_PATTERNS.items():
        count = len(re.findall(pattern, raw_blob))
        print(f"  {label}: {count}")
        if count:
            failures.append(f"forbidden pattern present: {label} ({count})")

    unused = [
        (entry.ipa, entry.condition)
        for entry in mapping.entries
        if token_counts.get((entry.ipa, entry.condition), 0) == 0
    ]
    print(f"\nmapping rows never exercised: {unused if unused else 'none'}")
    if unused:
        failures.append(f"mapping rows never exercised: {unused}")

    print("\nɪə stress conditioning:")
    print(f"  stressed: {token_counts.get(('ɪə', 'stressed'), 0)} occurrences, {len(iea_audit['stressed'])} words")
    print(f"  unstressed: {token_counts.get(('ɪə', 'unstressed'), 0)} occurrences, {len(iea_audit['unstressed'])} words")
    unmarked = sorted(iea_audit["unmarked-multinucleus"])
    print(f"  ɪə in unstressed-marked-less multi-nucleus chunks ({len(unmarked)}): {', '.join(unmarked[:30])}")

    print("\ntop token counts:")
    for (ipa, condition), count in token_counts.most_common(15):
        print(f"  {ipa!r} {condition or '-'}: {count}")

    if failures:
        print(f"\nFAILED: {len(failures)} problem(s)")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("\nOK: total coverage, all invariants hold")
    return 0


if __name__ == "__main__":
    sys.exit(main())
