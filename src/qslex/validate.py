from __future__ import annotations

import argparse
import collections
import re
import sys
from pathlib import Path

from qslex.divergences import load_divergences
from qslex.mapping import Mapping, load_mapping
from qslex.overrides import Override, load_overrides
from qslex.quirks import load_quirks, normalize
from qslex.readlex import CORPUS_ROWS, CorpusError, Row, load_rows
from qslex.tokenizer import (
    STRESS_MARKS,
    Token,
    TokenizeError,
    letters,
    pre_r,
    tokenize,
)

EAR = "\U0001047d"
IAN = "\U0001047e"
IT = "\U00010466"
ARRAY = "\U0001047c"

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
    ("u", ""): 578,
    ("tʃ", ""): 4355,
    ("dʒ", ""): 5802,
    ("eə", "no-r"): 3,
    ("ʊə", ""): 760,
    ("aɪə", "pre-r"): 655,
    ("aɪə", "no-r"): 518,
    ("əʊ", ""): 10506,
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

FORBIDDEN_OUTPUT = {
    "hiatus marker leaked into output": "+",
}


def consulted(tokens: list[Token], rule: Override) -> bool:
    occurrence = 0
    for token in tokens:
        if token.ipa == rule.token:
            occurrence += 1
            if rule.applies_to(occurrence):
                return True
    return False


def stressed_rhotic_ears(ipa: str, tokens: list[Token]) -> int:
    position = 0
    count = 0
    for token in tokens:
        following = position + len(token.ipa)
        if (
            token.ipa == "ɪə"
            and token.entry.condition == "stressed"
            and pre_r(ipa, following)
        ):
            count += 1
        position = following
    return count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Tokenize every ReadLex IPA string against the mapping"
    )
    parser.add_argument("readlex", nargs="?", type=Path, default=None)
    parser.add_argument("--no-verify-digest", action="store_true")
    args = parser.parse_args(argv)

    mapping: Mapping = load_mapping()
    quirk_rules = load_quirks()
    overrides = load_overrides(mapping)
    divergences = load_divergences()
    try:
        rows: tuple[Row, ...] = load_rows(
            args.readlex, verify=not args.no_verify_digest
        )
    except CorpusError as error:
        print(f"cannot read the ReadLex corpus: {error}")
        return 1

    failures: list[str] = []
    residue: list[str] = []
    token_counts: collections.Counter[tuple[str, str]] = collections.Counter()
    quirk_hits: dict[int, set[str]] = collections.defaultdict(set)
    override_hits: dict[tuple[str, str, str], set[str]] = collections.defaultdict(set)
    divergence_hits: set[tuple[str, str]] = set()
    iea_audit: dict[str, set[str]] = {
        "stressed": set(),
        "unstressed": set(),
        "unmarked-multinucleus": set(),
    }
    oracle = {"agree": 0, "disagree": 0, "silent": 0}
    unexpected: list[str] = []
    output_leaks: list[str] = []

    normalized_strings: list[str] = []
    for row in rows:
        ipa, applied = normalize(row.ipa, quirk_rules)
        normalized_strings.append(ipa)
        for index in applied:
            quirk_hits[index].add(row.word)
        try:
            tokens = tokenize(ipa, mapping, overrides)
        except TokenizeError as error:
            residue.append(f"{row.word!r}: {error}")
            continue

        spelling = letters(tokens)
        for label, needle in FORBIDDEN_OUTPUT.items():
            if needle in spelling:
                output_leaks.append(f"{label}: {row.word!r} -> {spelling}")

        for rule in overrides.get(ipa, ()):
            if consulted(tokens, rule):
                override_hits[(rule.ipa, rule.token, rule.occurrence)].add(row.word)

        for token in tokens:
            token_counts[(token.ipa, token.entry.condition)] += 1
            if token.ipa == "ɪə":
                iea_audit[token.entry.condition].add(row.word)

        claimed = row.shavian.count(EAR)
        produced = stressed_rhotic_ears(ipa, tokens)
        if claimed or produced:
            if claimed == produced:
                oracle["agree"] += 1
            else:
                oracle["disagree"] += 1
                key = (row.word, ipa)
                if key in divergences:
                    divergence_hits.add(key)
                    recorded = divergences[key].shavian
                    if recorded != row.shavian:
                        failures.append(
                            f"divergence {key} records Shavian {recorded!r}, "
                            f"corpus has {row.shavian!r}"
                        )
                else:
                    unexpected.append(
                        f"{row.word!r} {ipa!r}: mapping writes {produced} stressed "
                        f"EAR, Shavian {row.shavian!r} writes {claimed}"
                    )
        elif any(t.ipa == "ɪə" for t in tokens):
            oracle["silent"] += 1

    for ipa in normalized_strings:
        for chunk in re.split(r"[ +-]", ipa):
            if (
                "ɪə" in chunk
                and not any(mark in chunk for mark in STRESS_MARKS)
                and len(re.findall(r"[ɪieæaɑɒɔʊuʌəɜːÆƏIⱭ]+", chunk)) > 1
            ):
                iea_audit["unmarked-multinucleus"].add(chunk)

    print(f"rows tokenized: {len(rows)} (expected {CORPUS_ROWS})")
    print(f"unmapped residue: {len(residue)}")
    for line in residue[:20]:
        print(f"  {line}")
    if residue:
        failures.append(f"{len(residue)} rows with unmapped residue")

    print("\nquirk rule applications:")
    for index, quirk in enumerate(quirk_rules):
        hits = quirk_hits.get(index, set())
        status = f"{len(hits)} rows" if hits else "UNUSED"
        print(f"  [{quirk.scope}] {quirk.match!r} -> {quirk.replacement!r}: {status}")
        if not hits:
            failures.append(f"quirk rule {quirk.match!r} matched nothing")
            continue
        declared = set(quirk.declared_words)
        undeclared = sorted(hits - declared)
        unseen = sorted(declared - hits)
        if undeclared:
            failures.append(
                f"quirk rule {quirk.match!r} touches undeclared words: {undeclared}"
            )
            print(f"    UNDECLARED: {', '.join(undeclared)}")
        if unseen:
            failures.append(
                f"quirk rule {quirk.match!r} declares unmatched words: {unseen}"
            )
            print(f"    DECLARED BUT UNMATCHED: {', '.join(unseen)}")

    print("\nstress overrides:")
    all_overrides = [rule for rules in overrides.values() for rule in rules]
    for override in sorted(all_overrides, key=lambda r: (r.words, r.ipa)):
        override_key = (override.ipa, override.token, override.occurrence)
        hits = override_hits.get(override_key, set())
        print(
            f"  {override.words}: {override.token!r} -> {override.condition} "
            f"({len(hits)} rows)"
        )
        if not hits:
            failures.append(f"override {override_key} was never consulted")
        undeclared = sorted(hits - set(override.declared_words))
        if undeclared:
            failures.append(
                f"override {override_key} touches undeclared words: {undeclared}"
            )
        mechanical = letters(tokenize(override.ipa, mapping))
        overridden = letters(tokenize(override.ipa, mapping, overrides))
        if mechanical == overridden:
            failures.append(
                f"override {override_key} changes nothing; the mechanical rule "
                f"already yields {overridden}"
            )

    print("\nstressed EAR vs the ReadLex Shavian column (𐑽 count per row):")
    print(f"  agree: {oracle['agree']}")
    print(f"  disagree, expected (Manual overrules Shavian): {len(divergence_hits)}")
    print(f"  disagree, UNEXPECTED: {len(unexpected)}")
    for line in unexpected[:20]:
        print(f"    {line}")
    print(f"  Shavian silent (non-rhotic ɪə, always 𐑾): {oracle['silent']}")
    if unexpected:
        failures.append(
            f"{len(unexpected)} ɪə decisions contradict Shavian unexpectedly"
        )
    unhit = sorted(set(divergences) - divergence_hits)
    if unhit:
        failures.append(f"divergence rows never exercised: {unhit}")

    print("\ninvariant token counts:")
    for key, expected in EXPECTED_TOKEN_COUNTS.items():
        actual = token_counts.get(key, 0)
        marker = "ok" if actual == expected else f"MISMATCH (expected {expected})"
        print(f"  {key[0]!r} {key[1] or '-'}: {actual} {marker}")
        if actual != expected:
            failures.append(f"count mismatch for {key}: {actual} != {expected}")

    normalized_blob = "\n".join(normalized_strings)
    goat_in_text = len(re.findall("əʊ", normalized_blob))
    goat_tokens = token_counts.get(("əʊ", ""), 0)
    conserved = "ok" if goat_in_text == goat_tokens else "MISMATCH"
    print(
        f"\nəʊ conservation: {goat_in_text} in normalized text, "
        f"{goat_tokens} tokenized {conserved}"
    )
    if goat_in_text != goat_tokens:
        failures.append(
            f"əʊ not conserved: {goat_in_text} in text, {goat_tokens} tokenized"
        )

    raw_blob = "\n".join(row.ipa for row in rows)
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

    print(f"\nforbidden output patterns: {len(output_leaks)}")
    for line in output_leaks[:10]:
        print(f"  {line}")
    if output_leaks:
        failures.append(
            f"{len(output_leaks)} rows leak a structural marker into output"
        )

    unused = [
        (entry.ipa, entry.condition)
        for entry in mapping.entries
        if token_counts.get((entry.ipa, entry.condition), 0) == 0
    ]
    print(f"\nmapping rows never exercised: {unused if unused else 'none'}")
    if unused:
        failures.append(f"mapping rows never exercised: {unused}")

    print("\nɪə stress conditioning:")
    print(
        f"  stressed: {token_counts.get(('ɪə', 'stressed'), 0)} occurrences, "
        f"{len(iea_audit['stressed'])} words"
    )
    print(
        f"  unstressed: {token_counts.get(('ɪə', 'unstressed'), 0)} occurrences, "
        f"{len(iea_audit['unstressed'])} words"
    )
    unmarked = sorted(iea_audit["unmarked-multinucleus"])
    print(f"  ɪə in mark-less multi-nucleus chunks ({len(unmarked)})")

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
