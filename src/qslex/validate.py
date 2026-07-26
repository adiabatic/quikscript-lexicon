from __future__ import annotations

import argparse
import collections
import dataclasses
import re
import sys
from pathlib import Path

from qslex.divergences import load_divergences
from qslex.lint import CHECKS, lint, load_pragmas
from qslex.manual import SIGN_ANCHORS, load_examples
from qslex.mapping import Mapping, load_mapping
from qslex.overrides import Override, load_overrides
from qslex.passages import SPECIMENS, load_passages
from qslex.quirks import load_quirks, normalize
from qslex.readlex import CORPUS_HEADWORDS, CORPUS_ROWS, CorpusError, Row, load_rows
from qslex.roundtrip import (
    EDITS,
    align,
    phonemes_of,
    source_phonemes,
    spelt_phonemes,
)
from qslex.rules import (
    RULES,
    Context,
    claims,
    load_tables,
    naive,
    spell,
    split,
    undecided_ess,
    undecided_ful,
    undecided_ing,
    undecided_ligature,
    undecided_prefix,
)
from qslex.tokenizer import (
    STRESS_MARKS,
    Token,
    TokenizeError,
    letters,
    pre_r,
    tokenize,
)
from qslex.variants import kept, load_var_tags
from qslex.words import CORE_EIGHT, Contraction, load_contractions

EAR = "\U0001047d"
IAN = "\U0001047e"
IT = "\U00010466"
ARRAY = "\U0001047c"

EXPECTED_TOKEN_COUNTS = {
    ("R", ""): 27512,
    ("Ə", ""): 7846,
    ("I", ""): 617,
    ("Æ", ""): 1707,
    ("Ɑː", ""): 1705,
    ("ʍ", ""): 560,
    ("Ð", ""): 25,
    ("T", ""): 33,
    ("N", ""): 32,
    ("V", ""): 43,
    ("F", ""): 25,
    ("x", ""): 1,
    ("ɬ", ""): 1,
    ("u", ""): 580,
    ("tʃ", ""): 4361,
    ("dʒ", ""): 5827,
    ("eə", "no-r"): 3,
    ("ʊə", ""): 762,
    ("aɪə", "pre-r"): 655,
    ("aɪə", "no-r"): 523,
    ("əʊ", ""): 10569,
    ("aʊə", "pre-r"): 270,
    ("aʊə", "no-r"): 51,
}

RRP_ROWS = 108425
RRP_HEADWORDS = 56649

# Rows each orthographic rule actually rewrites, counted over the rows the lexicon
# spells rather than over the whole corpus. Sixteen of the Manual's rules are satisfied
# by ReadLex's IPA already and ship as normalisers, so a zero here is a statement, not a
# bug: it says the corpus never contradicts that rule.
EXPECTED_RULE_CHANGES: dict[str, int] = {
    "terminal-es-ed": 7681,
    "terminal-ing": 10976,
    "prefix-con-com": 1390,
    "prefix-un": 0,
    "prefix-an-al-ar": 0,
    "prefix-ob-of": 0,
    "prefix-be-de-re": 0,
    "prefix-pre-pro": 0,
    "prefix-per-pur": 0,
    "prefix-in-en": 0,
    "terminal-ally-able": 978,
    "terminal-tion": 2751,
    "terminal-ess-est": 1818,
    "terminal-land-ment": 893,
    "terminal-ent-ance": 0,
    "terminal-us-ous": 1,
    "terminal-ward": 71,
    "terminal-ful": 0,
    "terminal-ain": 22,
    "terminal-age": 302,
    "terminal-al-el-le-il": 3140,
    "terminal-ia-ea": 13,
    "terminal-ier-ior": 0,
    "terminal-er": 0,
    "terminal-y": 14,
    "terminal-en-on": 25,
}

# Rows each word sign or standard outline rewrites, again over the rows the lexicon
# spells. Most of the Manual's Common words are already what ReadLex's IPA gives, and
# five of the core eight arrive as upstream's own Ð/T/N/V/F capitals, so a zero here
# says the corpus agrees with the Manual rather than that the row is idle. Counts
# include the word inside a phrase entry.
EXPECTED_SIGN_CHANGES: dict[str, int] = {
    "after": 5,
    "always": 1,
    "at": 4,
    "be": 3,
    "dr": 1,
    "is": 2,
    "it": 2,
    "last": 5,
    "mr": 2,
    "mrs": 2,
    "that": 3,
    "to": 3,
    "was": 1,
}

# Rows whose Junior spelling diverges from the Senior one: non-demonstrative that,
# and the two standard outlines that reduce a vowel ReadLex writes in full.
EXPECTED_JUNIOR_DIVERGENCES = 5

# Words the Manual spells out that ReadLex has no entry for, so the fixture records
# them without being able to reproduce them.
EXPECTED_MANUAL_ABSENT = 2

# What the round trip finds when it reads every shipped spelling back to a phoneme
# string and lays it beside the IPA it came from. Every difference is one of the
# `EDITS` the mapping and the conventions license, and each is pinned here, so a rule
# that starts eliding a vowel it has no business eliding shows up as a count that moved.
EXPECTED_ROUNDTRIP_EDITS: dict[tuple[str, str], int] = {
    ("ə", ""): 19509,
    ("ɪ", ""): 11245,
    ("ə", "e"): 1828,
    ("e", "eɪ"): 1354,
    ("ɪ", "iː"): 1312,
    ("ʊ", "uː"): 763,
    ("ɪ", "e"): 700,
    ("ɪ", "ə"): 351,
    ("", "ə"): 256,
    ("r", ""): 71,
    ("ə", "ɪ"): 14,
    ("ɑː", "æ"): 10,
    ("ə", "æ"): 4,
    ("iː", ""): 3,
    ("uː", ""): 3,
    ("æ", ""): 3,
    ("t", ""): 2,
    ("eɪ", "ə"): 1,
    ("ɒ", "ə"): 1,
}

# Spellings that read straight back to their own IPA, with nothing elided or levelled.
EXPECTED_ROUNDTRIP_IDENTICAL = 76756

# The Manual's three abbreviations are written without a break between letters and
# stand for the written word, not for its sounds, so there is nothing to read back.
EXPECTED_ROUNDTRIP_SKIPPED = 5

EXPECTED_RAW_COUNTS = {
    "raw ʊə incl. inside aʊə and across əʊ+ə": (r"ʊə", 1231),
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


def by_latin(
    spellings: dict[str, dict[tuple[str, str], set[str]]],
) -> dict[str, dict[str, set[str]]]:
    """Every spelling the lexicon carries for a word, by word and then by column."""
    out: dict[str, dict[str, set[str]]] = {}
    for column, table in spellings.items():
        for (latin, _), values in table.items():
            out.setdefault(latin, {}).setdefault(column, set()).update(values)
    return out


def contracted_by_word(
    contractions: tuple[Contraction, ...],
) -> dict[str, set[str]]:
    out: dict[str, set[str]] = collections.defaultdict(set)
    for entry in contractions:
        out[entry.word].add(entry.contraction)
    return out


def passages(
    spellings: dict[str, dict[tuple[str, str], set[str]]],
    contractions: tuple[Contraction, ...],
) -> list[str]:
    """Hold every word of the Manual's specimen passages to what the lexicon spells.

    The passages are the one place the Manual writes running text rather than a rule's
    example, so they are the only fixture that exercises the word signs, the terminals
    and the segment mapping together, in the proportions English actually uses them.
    """
    failures: list[str] = []
    by_word = by_latin(spellings)
    contracted = contracted_by_word(contractions)

    tally: dict[str, collections.Counter[str]] = collections.defaultdict(
        collections.Counter
    )
    for word in load_passages():
        tally[word.passage][word.verdict] += 1
        columns = by_word.get(word.latin, {})
        produced = {v for column in word.columns for v in columns.get(column, ())}
        where = f"{word.passage} word {word.index} ({word.latin!r})"
        if word.verdict == "contraction":
            if word.spelling not in contracted.get(word.latin, set()):
                failures.append(
                    f"{where} is the §III contraction {word.spelling}, "
                    f"which contractions.tsv does not carry"
                )
        elif word.verdict == "absent":
            if columns:
                failures.append(
                    f"{where} is recorded as absent from ReadLex, which now spells it "
                    f"{sorted(produced)}"
                )
        elif word.verdict == "differs":
            if not columns:
                failures.append(f"{where} differs from a word ReadLex no longer has")
            elif word.spelling in produced:
                failures.append(
                    f"{where} is recorded as differing but is now reproduced; the row "
                    f"should say which column spells it"
                )
            else:
                ours = " / ".join(sorted(columns.get(word.columns[0], set())))
                if ours != word.ours:
                    failures.append(
                        f"{where} pins {word.ours} against the Manual's "
                        f"{word.spelling}, but the lexicon now spells {ours}"
                    )
        elif word.spelling not in columns.get(word.verdict, set()):
            failures.append(
                f"{where}: the Manual writes {word.spelling}, the {word.verdict} "
                f"column has {sorted(columns.get(word.verdict, set()))}"
            )

    print("\nManual specimen passages, word by word:")
    for name, specimen in SPECIMENS.items():
        counts = tally[name]
        summary = ", ".join(f"{v} {k}" for k, v in sorted(counts.items()))
        print(
            f"  {name:19} {specimen.level:6} {sum(counts.values()):4} words: {summary}"
        )
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Tokenize every ReadLex IPA string against the mapping, and hold "
        "the rows the lexicon spells to the Manual"
    )
    parser.add_argument("readlex", nargs="?", type=Path, default=None)
    parser.add_argument("--no-verify-digest", action="store_true")
    args = parser.parse_args(argv)

    mapping: Mapping = load_mapping()
    var_tags = load_var_tags()
    quirk_rules = load_quirks()
    overrides = load_overrides(mapping)
    divergences = load_divergences()
    tables = load_tables()
    contractions = load_contractions()
    pragmas = load_pragmas()
    examples = load_examples()
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

    rule_changes: collections.Counter[str] = collections.Counter()
    rule_claims: collections.Counter[str] = collections.Counter()
    rule_word_hits: set[tuple[str, str]] = set()
    ligature_hits: set[tuple[str, str]] = set()
    sign_changes: collections.Counter[str] = collections.Counter()
    sign_hits: set[tuple[str, str]] = set()
    junior_rows = 0
    junior_drift: list[str] = []
    lint_hits: collections.Counter[str] = collections.Counter()
    lint_examples: dict[str, list[str]] = collections.defaultdict(list)
    lint_excused: set[tuple[str, str]] = set()
    roundtrip: collections.Counter[tuple[str, str]] = collections.Counter()
    roundtrip_identical = 0
    roundtrip_skipped = 0
    unreadable: list[str] = []
    core_misses: list[str] = []
    undecided: dict[str, set[str]] = collections.defaultdict(set)
    stray_ligatures: list[str] = []
    spellings: dict[str, dict[tuple[str, str], set[str]]] = {
        "senior": collections.defaultdict(set),
        "junior": collections.defaultdict(set),
        "ligature": collections.defaultdict(set),
    }

    try:
        policy = [kept(var_tags, row.var) for row in rows]
    except ValueError as error:
        print(f"cannot apply the row policy: {error}")
        return 1
    vvg = {
        row.word.lower()
        for row, spells in zip(rows, policy, strict=True)
        if row.pos == "VVG" and spells
    }
    core_signs = {word: tables.signs[(word, "")].senior for word in CORE_EIGHT}
    unsigned = dataclasses.replace(tables, signs={})
    read_back = phonemes_of(mapping)

    var_rows: collections.Counter[str] = collections.Counter()
    var_words: dict[str, set[str]] = collections.defaultdict(set)
    rrp_rows = 0
    rrp_headwords: set[str] = set()

    normalized_strings: list[str] = []
    for row, spells in zip(rows, policy, strict=True):
        var_rows[row.var] += 1
        var_words[row.var].add(row.word)
        if spells:
            rrp_rows += 1
            rrp_headwords.add(row.headword)
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

        if spells:
            word = row.word.lower()
            context = Context(word, row.pos, ipa, tuple(tokens))
            raw = naive(context)
            result = spell(context, tables)
            spellings["senior"][(word, row.pos)].add(result.senior)
            spellings["junior"][(word, row.pos)].add(result.junior or result.senior)
            spellings["ligature"][(word, row.pos)].add(result.ligature or result.senior)
            for rule_id in result.applied:
                rule_changes[rule_id] += 1
            rule_word_hits.update(result.ruled)
            for element in split(context, raw):
                if not element.word:
                    continue
                inner = element.context
                part = inner.latin
                for orthographic in RULES:
                    if orthographic.latin is None or claims(orthographic, inner):
                        rule_claims[orthographic.id] += 1
                if undecided_ing(part, vvg) and not tables.ruled("terminal-ing", part):
                    undecided["terminal-ing"].add(part)
                if undecided_ess(inner, element.letters, tables):
                    undecided["terminal-ess-est"].add(part)
                if undecided_ful(inner, element.letters, tables):
                    undecided["terminal-ful"].add(part)
                if undecided_prefix(inner, element.letters, tables):
                    undecided["prefix-be-de-re"].add(part)
            why = undecided_ligature(context, raw, tables)
            if why:
                undecided[f"ligature/{why}"].add(word)
            for key in ((word, row.pos), (word, "")):
                if key in tables.ligatures:
                    ligature_hits.add(key)
                    break
            if result.ligature and "x" not in word:
                stray_ligatures.append(f"{word!r} has no x but got {result.ligature}")
            for touched in dict.fromkeys(result.signed):
                sign_changes[touched] += 1
            sign_hits.update(result.signs)
            if word in core_signs and result.senior != core_signs[word]:
                core_misses.append(
                    f"{word!r} [{row.pos}] is a core word sign, wanted "
                    f"{core_signs[word]}, got {result.senior}"
                )
            for check_id, part, complaint in lint(
                word, row.pos, result.senior, result.ligature, ipa, tables, {}
            ):
                if (check_id, word) in pragmas:
                    lint_excused.add((check_id, word))
                    continue
                lint_hits[check_id] += 1
                if len(lint_examples[check_id]) < 5:
                    lint_examples[check_id].append(
                        f"{part!r} in {word!r} [{row.pos}] {result.senior}: {complaint}"
                    )

            abbreviated = any(
                tables.signs[key].tier == "abbreviation"
                for key in result.signs
                if key[0] in set(result.signed)
            )
            if abbreviated:
                roundtrip_skipped += 1
            else:
                said = source_phonemes(tuple(tokens))
                for spelling in dict.fromkeys(
                    s for s in (result.senior, result.junior, result.ligature) if s
                ):
                    written = spelt_phonemes(spelling, read_back)
                    if said == written:
                        roundtrip_identical += 1
                        continue
                    edits = align(said, written)
                    if edits is None:
                        unreadable.append(
                            f"{word!r} [{row.pos}] {ipa} spelt {spelling} reads back "
                            f"as {' '.join(written)}"
                        )
                        continue
                    roundtrip.update(edits)
            if result.junior:
                junior_rows += 1
                bare = spell(context, unsigned).senior
                if result.junior != bare:
                    junior_drift.append(
                        f"{word!r} [{row.pos}] declares Junior {result.junior}, but "
                        f"leaving the sign unapplied gives {bare}"
                    )

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

    print("\nvariant tags:")
    for tag, entry in sorted(var_tags.items(), key=lambda kv: -kv[1].rows):
        actual = var_rows.get(tag, 0)
        marker = "ok" if actual == entry.rows else f"MISMATCH (expected {entry.rows})"
        print(
            f"  {tag:9} -> {entry.canonical:9} {entry.policy:4} {actual:7} rows "
            f"{marker}"
        )
        if actual != entry.rows:
            failures.append(f"tag {tag!r} covers {actual} rows, expected {entry.rows}")
        declared = set(entry.declared_words)
        if not declared:
            continue
        undeclared = sorted(var_words[tag] - declared)
        unseen = sorted(declared - var_words[tag])
        if undeclared:
            failures.append(f"tag {tag!r} touches undeclared words: {undeclared}")
            print(f"    UNDECLARED: {', '.join(undeclared)}")
        if unseen:
            failures.append(f"tag {tag!r} declares words it no longer covers: {unseen}")
            print(f"    DECLARED BUT UNMATCHED: {', '.join(unseen)}")
    unruled = sorted(set(var_rows) - set(var_tags))
    if unruled:
        failures.append(f"variant tags with no row policy: {unruled}")
    print(f"  rows the lexicon spells: {rrp_rows} (expected {RRP_ROWS})")
    print(
        f"  headwords they fall under: {len(rrp_headwords)} of {CORPUS_HEADWORDS} "
        f"(expected {RRP_HEADWORDS})"
    )
    if rrp_rows != RRP_ROWS:
        failures.append(f"{rrp_rows} rows survive the row policy, expected {RRP_ROWS}")
    if len(rrp_headwords) != RRP_HEADWORDS:
        failures.append(
            f"{len(rrp_headwords)} headwords survive the row policy, "
            f"expected {RRP_HEADWORDS}"
        )

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

    print("\northographic rules, rows rewritten:")
    for orthographic in RULES:
        changed = rule_changes.get(orthographic.id, 0)
        pinned = EXPECTED_RULE_CHANGES.get(orthographic.id)
        drift = "" if pinned is None or changed == pinned else f" MISMATCH ({pinned})"
        claimed = rule_claims.get(orthographic.id, 0)
        print(f"  {orthographic.id:22} {changed:6} of {claimed:6} claimed{drift}")
        if not claimed:
            failures.append(f"rule {orthographic.id} claims no word in the corpus")
        if pinned is not None and changed != pinned:
            failures.append(
                f"rule {orthographic.id} rewrote {changed} rows, expected {pinned}"
            )
    unpinned = [r.id for r in RULES if r.id not in EXPECTED_RULE_CHANGES]
    if unpinned:
        failures.append(f"rules with no pinned rewrite count: {unpinned}")

    print("\nundecided residue (must be ruled on in rule-words.tsv / x-ligatures.tsv):")
    for label in sorted(undecided):
        words = sorted(undecided[label])
        print(f"  {label}: {len(words)}")
        for word in words[:10]:
            print(f"    {word}")
        failures.append(f"{len(words)} undecided {label} words: {words[:10]}")
    if not undecided:
        print("  none")

    print("\nrule-word rulings:")
    for key in sorted(tables.words):
        if key not in rule_word_hits:
            failures.append(f"rule-word ruling {key} was never exercised")
    print(f"  {len(tables.words)} rulings, {len(rule_word_hits)} exercised")

    print("\nx-ligature rulings:")
    unused_ligatures = sorted(set(tables.ligatures) - ligature_hits)
    print(f"  {len(tables.ligatures)} rulings, {len(ligature_hits)} exercised")
    if unused_ligatures:
        failures.append(f"x-ligature rulings never exercised: {unused_ligatures}")
    print(f"  ligatures on words with no x: {len(stray_ligatures)}")
    for line in stray_ligatures[:10]:
        print(f"    {line}")
    if stray_ligatures:
        failures.append(f"{len(stray_ligatures)} ligatures on words without an x")

    print("\nword signs and standard outlines, rows rewritten:")
    for key in sorted(tables.signs):
        if key not in sign_hits:
            failures.append(f"word-sign row {key} was never reached by a corpus row")
    for word in sorted(set(EXPECTED_SIGN_CHANGES) | set(sign_changes)):
        changed = sign_changes.get(word, 0)
        pinned = EXPECTED_SIGN_CHANGES.get(word)
        drift = "" if pinned is None or changed == pinned else f" MISMATCH ({pinned})"
        print(f"  {word:12} {changed:4}{drift}")
        if pinned is None:
            failures.append(f"{word!r} rewrites {changed} rows with no pinned count")
        elif changed != pinned:
            failures.append(
                f"word sign {word!r} rewrote {changed} rows, expected {pinned}"
            )
    corroborated = {e.word for e in examples if e.rule in SIGN_ANCHORS}
    uncorroborated = sorted(set(sign_changes) - corroborated)
    print(f"  rewriting words with no Manual fixture: {uncorroborated or 'none'}")
    if uncorroborated:
        failures.append(
            f"these words rewrite rows but no manual-spellings.tsv row holds their "
            f"spelling to the Manual: {uncorroborated}"
        )
    busy = {key for key in tables.signs if key[0] in sign_changes}
    print(
        f"  {len(tables.signs)} rows, {len(sign_hits)} reached, "
        f"{len(tables.signs) - len(busy)} that rewrite nothing"
    )
    for word, spelling in sorted(core_signs.items()):
        print(f"  core: {word:5} {spelling}")
    print(f"  core-eight rows disagreeing with their sign: {len(core_misses)}")
    for line in core_misses[:10]:
        print(f"    {line}")
    if core_misses:
        failures.append(f"{len(core_misses)} rows spell a core word sign in full")

    print(f"\nJunior divergences: {junior_rows} (want {EXPECTED_JUNIOR_DIVERGENCES})")
    for line in junior_drift[:10]:
        print(f"    {line}")
    if junior_rows != EXPECTED_JUNIOR_DIVERGENCES:
        failures.append(
            f"{junior_rows} rows carry a Junior spelling, "
            f"expected {EXPECTED_JUNIOR_DIVERGENCES}"
        )
    if junior_drift:
        failures.append(
            f"{len(junior_drift)} Junior spellings are not simply the unsigned spelling"
        )

    print(
        f"\nSenior contraction table (converter layer, applied to no column): "
        f"{len(contractions)} rows"
    )
    known_words = {row.word.lower() for row in rows}
    orphans = [
        entry.word
        for entry in contractions
        if entry.kind == "word" and entry.word not in known_words
    ]
    print(f"  contractions with no ReadLex entry: {len(orphans)}")
    if orphans:
        failures.append(f"contraction rows for words ReadLex does not have: {orphans}")

    absent = 0
    unreproduced: list[str] = []
    for example in examples:
        candidates = {
            value
            for (word, pos), values in spellings[example.column].items()
            if word == example.word and (not example.pos or pos == example.pos)
            for value in values
        }
        if not candidates:
            absent += 1
            continue
        if not any(example.matches(value) for value in candidates):
            unreproduced.append(
                f"{example.word!r} [{example.rule}] wants {example.kind} "
                f"{example.spelling}, got {sorted(candidates)}"
            )
    print(f"\nManual example words: {len(examples)}")
    print(f"  reproduced: {len(examples) - absent - len(unreproduced)}")
    print(f"  not in ReadLex: {absent} (expected {EXPECTED_MANUAL_ABSENT})")
    print(f"  NOT reproduced: {len(unreproduced)}")
    for line in unreproduced[:20]:
        print(f"    {line}")
    if unreproduced:
        failures.append(f"{len(unreproduced)} Manual spellings not reproduced")
    if absent != EXPECTED_MANUAL_ABSENT:
        failures.append(
            f"{absent} Manual example words are missing from ReadLex, "
            f"expected {EXPECTED_MANUAL_ABSENT}"
        )

    print("\nthe Manual's own lint, re-derived and run over every spelt row:")
    for check in CHECKS:
        broken = lint_hits.get(check.id, 0)
        excused = sum(1 for key in pragmas if key[0] == check.id)
        print(f"  {check.id:34} {broken:5} broken, {excused:3} pragma'd")
        for line in lint_examples[check.id]:
            print(f"      {line}")
        if broken:
            failures.append(
                f"lint {check.id} is broken by {broken} rows, and the Manual requires "
                f"that {check.requires}"
            )
    stale = sorted(set(pragmas) - lint_excused)
    print(f"  pragmas never needed: {stale or 'none'}")
    if stale:
        failures.append(f"lint pragmas that excuse nothing: {stale}")

    print("\nround trip, every spelling read back to a phoneme string:")
    print(f"  identical to the IPA it came from: {roundtrip_identical}")
    print(f"  abbreviations, which spell no sounds: {roundtrip_skipped}")
    print(f"  not readable back at all: {len(unreadable)}")
    for line in unreadable[:10]:
        print(f"    {line}")
    if unreadable:
        failures.append(
            f"{len(unreadable)} spellings cannot be read back to their own IPA by any "
            f"licensed difference"
        )
    if roundtrip_identical != EXPECTED_ROUNDTRIP_IDENTICAL:
        failures.append(
            f"{roundtrip_identical} spellings read back unchanged, "
            f"expected {EXPECTED_ROUNDTRIP_IDENTICAL}"
        )
    if roundtrip_skipped != EXPECTED_ROUNDTRIP_SKIPPED:
        failures.append(
            f"{roundtrip_skipped} abbreviation rows skipped, "
            f"expected {EXPECTED_ROUNDTRIP_SKIPPED}"
        )
    for edit in sorted(set(EXPECTED_ROUNDTRIP_EDITS) | set(roundtrip)):
        found = roundtrip.get(edit, 0)
        pinned = EXPECTED_ROUNDTRIP_EDITS.get(edit)
        drift = "" if found == pinned else f" MISMATCH ({pinned})"
        shape = f"{edit[0] or '-':4} -> {edit[1] or '-':4}"
        print(f"  {shape} {found:7}{drift}  {EDITS[edit]}")
        if pinned is None:
            failures.append(f"round-trip difference {edit} has no pinned count")
        elif found != pinned:
            failures.append(
                f"round-trip difference {edit} occurs {found} times, expected {pinned}"
            )

    failures.extend(passages(spellings, contractions))

    if failures:
        print(f"\nFAILED: {len(failures)} problem(s)")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("\nOK: total coverage, all invariants hold")
    return 0


if __name__ == "__main__":
    sys.exit(main())
