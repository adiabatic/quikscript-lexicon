from __future__ import annotations

import argparse
import collections
import dataclasses
import re
import sys
from pathlib import Path

from qslex.added import AddedWord, load_added_words
from qslex.divergences import load_divergences
from qslex.lint import CHECKS, lint, load_exemptions
from qslex.manual import SIGN_ANCHORS, load_examples
from qslex.mapping import Mapping, load_mapping
from qslex.overrides import Overrides, load_overrides
from qslex.passages import SPECIMENS, load_passages
from qslex.quirks import QuirkRule, load_quirks, normalize
from qslex.readlex import CORPUS_HEADWORDS, CORPUS_ROWS, CorpusError, Row, load_rows
from qslex.roundtrip import (
    EDITS,
    align,
    phonemes_of,
    source_phonemes,
    spelled_phonemes,
)
from qslex.rules import (
    RULE_IDS,
    RULES,
    TERMINAL_RULES,
    Context,
    Tables,
    Terminal,
    load_tables,
    matches_ending,
    spell,
    substitutable,
    undecided_ess,
    undecided_ful,
    undecided_ing,
    undecided_prefix,
    undecided_x_letter,
    undecided_y,
)
from qslex.tokenizer import (
    Token,
    TokenizeError,
    letters,
    pre_r,
    tokenize,
)
from qslex.variants import kept, load_var_tags
from qslex.words import CORE_EIGHT, Contraction, load_contractions

EAR = "\U0001047d"

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

# Rows each orthographic rule rewrites, counted over the rows the lexicon spells rather than the whole corpus. Eleven of the Manual’s rules rewrite nothing because ReadLex’s IPA already gives the Manual’s spelling. They still run as normalizers, and a zero here means the corpus never contradicts that rule.
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
    "terminal-ess-est": 1860,
    "terminal-land-ment": 893,
    "terminal-nt": 21,
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
    "terminal-y": 91,
    "terminal-en-on": 25,
}

# Rows each word sign or standard outline rewrites, counted over the rows the lexicon spells. A word that rewrites no row is not listed. For most of the Manual’s Common words, and for the five of the core eight that ReadLex writes with its Ð/T/N/V/F capitals, ReadLex’s IPA already gives the Manual’s spelling. Counts include the word inside a phrase entry.
EXPECTED_SIGN_CHANGES: dict[str, int] = {
    "'twas": 1,
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
    "wasn't": 2,
}

# Rows whose Junior spelling differs from the Senior one. These are the non-demonstrative rows of that, the standard outlines that reduce a vowel ReadLex writes in full, and the rows terminal-nt rewrites. The standard outlines are always and was, with was also inside 'twas and wasn't, where the element split cannot separate it. The Junior column keeps the linking vowel that terminal-nt drops.
EXPECTED_JUNIOR_DIVERGENCES = 27

# Words in manual-spellings.tsv that ReadLex has no entry for. The table records their spelling, but the lexicon cannot reproduce it.
EXPECTED_MANUAL_ABSENT = 2

# Differences the round trip finds when it reads each shipped spelling back to a phoneme string and compares it with the IPA it came from. Every difference must be one of the kinds in `roundtrip.EDITS`, and each kind has an expected count here. If a rule starts dropping a vowel it should keep, one of these counts changes and the validator fails.
EXPECTED_ROUNDTRIP_EDITS: dict[tuple[str, str], int] = {
    ("ə", ""): 19527,
    ("ɪ", ""): 11243,
    ("ə", "e"): 1870,
    ("e", "eɪ"): 1354,
    ("ɪ", "iː"): 1312,
    ("ʊ", "uː"): 763,
    ("ɪ", "e"): 736,
    ("ɪ", "ə"): 351,
    ("", "ə"): 256,
    ("r", ""): 71,
    ("iː", "ɪ"): 77,
    ("ə", "ɪ"): 14,
}

# Spellings that read back to their own IPA with no differences.
EXPECTED_ROUNDTRIP_IDENTICAL = 76618

# Rows a word sign or standard outline rewrites. The round trip skips them, because such a spelling stands for the written word rather than its sounds.
EXPECTED_ROUNDTRIP_SKIPPED = 37

FORBIDDEN_RAW_PATTERNS = {
    "bare ɪR (schwa-less EAR)": r"ɪ[ˈˌ]?R",
    "bare aɪR (schwa-less PRICE+R)": r"aɪ[ˈˌ]?R",
    "bare aʊR (schwa-less MOUTH+R)": r"aʊ[ˈˌ]?R",
}


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
    """Every spelling the lexicon has for each word, keyed by word and then by column."""
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
    """Check every word of the Manual’s specimen passages against the lexicon’s spellings.

    The passages are the only running text in the Manual. The Manual’s other examples each illustrate one rule. So the passages are the only test data that exercises the word signs, the terminals and the segment mapping together, in the proportions English uses them.
    """
    failures: list[str] = []
    by_word = by_latin(spellings)
    contracted = contracted_by_word(contractions)

    tally: dict[str, collections.Counter[str]] = collections.defaultdict(
        collections.Counter
    )
    for word in load_passages():
        tally[word.passage][word.outcome] += 1
        columns = by_word.get(word.latin, {})
        produced = {v for column in word.columns for v in columns.get(column, ())}
        where = f"{word.passage} word {word.index} ({word.latin!r})"
        if word.outcome == "contraction":
            if word.spelling not in contracted.get(word.latin, set()):
                failures.append(
                    f"{where} is the contraction {word.spelling}, "
                    f"which contractions.tsv does not list"
                )
        elif word.outcome == "absent":
            if columns:
                failures.append(
                    f"{where} is recorded as absent from ReadLex, which now spells it "
                    f"{sorted(produced)}"
                )
        elif word.outcome == "differs":
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
                        f"{where} records {word.ours} against the Manual’s "
                        f"{word.spelling}, but the lexicon now spells {ours}"
                    )
        elif word.spelling not in columns.get(word.outcome, set()):
            failures.append(
                f"{where}: the Manual writes {word.spelling}, the {word.outcome} "
                f"column has {sorted(columns.get(word.outcome, set()))}"
            )

    print("\nManual specimen passages, word by word:")
    for name, specimen in SPECIMENS.items():
        counts = tally[name]
        summary = ", ".join(f"{v} {k}" for k, v in sorted(counts.items()))
        print(
            f"  {name:19} {specimen.level:6} {sum(counts.values()):4} words: {summary}"
        )
    return failures


def added(
    words: tuple[AddedWord, ...],
    rows: tuple[Row, ...],
    mapping: Mapping,
    quirk_rules: tuple[QuirkRule, ...],
    overrides: Overrides,
    tables: Tables,
) -> list[str]:
    """Check the added words, which the corpus lacks, more strictly than the corpus rows.

    This runs apart from the corpus pass in `main` for two reasons. The expected counts cover corpus rows only, so any change to them after an upstream update comes from ReadLex. And a row we wrote ourselves should need no exemption. A corpus row may break a lint check if `lint-exemptions.tsv` exempts it. An added row must produce the spelling in its `qs` column and pass every lint check. It must read back to its IPA using only the differences in `roundtrip.EDITS`, and no word sign may rewrite it. Added rows get no per-row tolerances, because the differences in that table apply to every word. For example, a -ted, -ing or -tion ending drops its schwa whether or not the row came from the corpus.

    The check that the word is not in ReadLex matters most over time. If ReadLex ever adds the word, the validator fails and names it, so the lexicon cannot ship a second spelling of it.
    """
    failures: list[str] = []
    read_back = phonemes_of(mapping)
    corpus = {row.word.lower() for row in rows}

    print(f"\nwords added beyond the corpus: {len(words)}")
    for entry in words:
        ipa, _ = normalize(entry.ipa, quirk_rules)
        tokens = tuple(tokenize(ipa, mapping, overrides))
        result = spell(Context(entry.word, entry.pos, ipa, tokens), tables)
        print(
            f"  {entry.word:15} {entry.pos:8} {ipa:15} {result.senior}  [{entry.source}]"
        )
        where = f"{entry.word!r} [{entry.pos}]"
        if entry.word in corpus:
            failures.append(
                f"{where} is now in ReadLex, which spells it for itself; the added "
                f"row should go, or say why it stays"
            )
        if result.senior != entry.qs:
            failures.append(
                f"{where} lists {entry.qs}, but the rules now spell it {result.senior}"
            )
        if result.signed:
            failures.append(
                f"{where} is rewritten by the word sign {result.signed}, which the "
                f"added row and the sign table disagree about"
            )
        for check_id, part, complaint in lint(
            entry.word, result.senior, result.x_letter, ipa, tables
        ):
            failures.append(f"{where} breaks lint {check_id} on {part!r}: {complaint}")
        for spelling in dict.fromkeys(
            s for s in (result.senior, result.junior, result.x_letter) if s
        ):
            said = source_phonemes(tokens)
            written = spelled_phonemes(spelling, read_back)
            if said != written and align(said, written) is None:
                failures.append(
                    f"{where} spelled {spelling} reads back as {' '.join(written)}, "
                    f"not {ipa}"
                )
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Tokenize every ReadLex IPA string against the mapping, and check "
        "the rows the lexicon spells against the Manual"
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
    exemptions = load_exemptions()
    examples = load_examples()
    added_words = load_added_words()
    try:
        rows: tuple[Row, ...] = load_rows(
            args.readlex, verify=not args.no_verify_digest
        )
    except CorpusError as error:
        print(f"cannot read the ReadLex corpus: {error}")
        return 1

    failures: list[str] = []
    unmapped: list[str] = []
    token_counts: collections.Counter[tuple[str, str]] = collections.Counter()
    quirk_hits: dict[int, set[str]] = collections.defaultdict(set)
    override_hits: dict[str, set[str]] = collections.defaultdict(set)
    divergence_hits: set[tuple[str, str]] = set()
    iea_audit: dict[str, set[str]] = {"stressed": set(), "unstressed": set()}
    shavian_ear_counts = {"agree": 0, "disagree": 0, "both_zero": 0}
    unexpected: list[str] = []

    rule_changes: collections.Counter[str] = collections.Counter()
    rule_matches: collections.Counter[str] = collections.Counter()
    rule_word_hits: set[tuple[str, str]] = set()
    x_decision_hits: set[str] = set()
    sign_changes: collections.Counter[str] = collections.Counter()
    sign_hits: set[tuple[str, str]] = set()
    junior_rows = 0
    junior_mismatches: list[str] = []
    lint_hits: collections.Counter[str] = collections.Counter()
    lint_examples: dict[str, list[str]] = collections.defaultdict(list)
    lint_exempted: set[tuple[str, str]] = set()
    roundtrip: collections.Counter[tuple[str, str]] = collections.Counter()
    roundtrip_identical = 0
    roundtrip_skipped = 0
    unreadable: list[str] = []
    core_misses: list[str] = []
    undecided: dict[str, set[str]] = collections.defaultdict(set)
    stray_x_letters: list[str] = []
    unsubstituted: list[str] = []
    spellings: dict[str, dict[tuple[str, str], set[str]]] = {
        "senior": collections.defaultdict(set),
        "junior": collections.defaultdict(set),
        "x-letter": collections.defaultdict(set),
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
            unmapped.append(f"{row.word!r}: {error}")
            continue

        rule = overrides.get(ipa)
        if rule is not None:
            override_hits[rule.ipa].add(row.word)

        for token in tokens:
            token_counts[(token.ipa, token.entry.condition)] += 1
            if token.ipa == "ɪə":
                iea_audit[token.entry.condition].add(row.word)

        if spells:
            word = row.word.lower()
            context = Context(word, row.pos, ipa, tuple(tokens))
            result = spell(context, tables)
            spellings["senior"][(word, row.pos)].add(result.senior)
            spellings["junior"][(word, row.pos)].add(result.junior or result.senior)
            spellings["x-letter"][(word, row.pos)].add(result.x_letter or result.senior)
            for rule_id in result.applied:
                rule_changes[rule_id] += 1
            rule_word_hits.update(result.decisions)
            for element in result.elements:
                if not element.word:
                    continue
                inner = element.context
                part = inner.latin
                for terminal in TERMINAL_RULES:
                    if matches_ending(terminal, inner):
                        rule_matches[terminal.id] += 1
                if undecided_ing(part, vvg) and not tables.has_decision(
                    "terminal-ing", part
                ):
                    undecided["terminal-ing"].add(part)
                if undecided_ess(inner, element.letters, tables):
                    undecided["terminal-ess-est"].add(part)
                if undecided_y(inner, element.letters, tables):
                    undecided["terminal-y"].add(part)
                if undecided_ful(inner, element.letters, tables):
                    undecided["terminal-ful"].add(part)
                if undecided_prefix(inner, element.letters, tables):
                    undecided["prefix-be-de-re"].add(part)
                why = undecided_x_letter(inner, element.letters, tables)
                if why:
                    undecided[f"x-letter/{why}"].add(part)
            x_decision_hits.update(latin for latin, _ in result.x_decisions)
            for latin, spelling in result.x_decisions:
                if not tables.x_decisions[latin].x_letter and substitutable(spelling):
                    unsubstituted.append(
                        f"{latin!r} has an x-decisions.tsv row with no X-letter, "
                        f"but is spelled {spelling}"
                    )
            if result.x_letter and "x" not in word:
                stray_x_letters.append(f"{word!r} has no x but got {result.x_letter}")
            for touched in dict.fromkeys(result.signed):
                sign_changes[touched] += 1
            sign_hits.update(result.signs)
            if word in core_signs and result.senior != core_signs[word]:
                core_misses.append(
                    f"{word!r} [{row.pos}] is a core word sign, wanted "
                    f"{core_signs[word]}, got {result.senior}"
                )
            for check_id, part, complaint in lint(
                word, result.senior, result.x_letter, ipa, tables
            ):
                if (check_id, word) in exemptions:
                    lint_exempted.add((check_id, word))
                    continue
                lint_hits[check_id] += 1
                if len(lint_examples[check_id]) < 5:
                    lint_examples[check_id].append(
                        f"{part!r} in {word!r} [{row.pos}] {result.senior}: {complaint}"
                    )

            if result.signed:
                roundtrip_skipped += 1
            else:
                said = source_phonemes(tuple(tokens))
                for spelling in dict.fromkeys(
                    s for s in (result.senior, result.junior, result.x_letter) if s
                ):
                    written = spelled_phonemes(spelling, read_back)
                    if said == written:
                        roundtrip_identical += 1
                        continue
                    edits = align(said, written)
                    if edits is None:
                        unreadable.append(
                            f"{word!r} [{row.pos}] {ipa} spelled {spelling} reads back "
                            f"as {' '.join(written)}"
                        )
                        continue
                    roundtrip.update(edits)
            if result.junior:
                junior_rows += 1
                bare = spell(context, unsigned)
                plain = bare.junior or bare.senior
                if result.junior != plain:
                    junior_mismatches.append(
                        f"{word!r} [{row.pos}] lists Junior {result.junior}, but "
                        f"without word signs or terminal-nt it is spelled {plain}"
                    )

        shavian_ears = row.shavian.count(EAR)
        produced = stressed_rhotic_ears(ipa, tokens)
        if shavian_ears or produced:
            if shavian_ears == produced:
                shavian_ear_counts["agree"] += 1
            else:
                shavian_ear_counts["disagree"] += 1
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
                        f"EAR, Shavian {row.shavian!r} writes {shavian_ears}"
                    )
        elif any(t.ipa == "ɪə" for t in tokens):
            shavian_ear_counts["both_zero"] += 1

    print(f"rows tokenized: {len(rows)} (expected {CORPUS_ROWS})")
    print(f"unmapped IPA: {len(unmapped)}")
    for line in unmapped[:20]:
        print(f"  {line}")
    if unmapped:
        failures.append(f"{len(unmapped)} rows with unmapped IPA")

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
        listed = set(entry.listed_words)
        if not listed:
            continue
        unlisted = sorted(var_words[tag] - listed)
        unseen = sorted(listed - var_words[tag])
        if unlisted:
            failures.append(f"tag {tag!r} touches unlisted words: {unlisted}")
            print(f"    UNLISTED: {', '.join(unlisted)}")
        if unseen:
            failures.append(f"tag {tag!r} lists words it no longer covers: {unseen}")
            print(f"    LISTED BUT UNMATCHED: {', '.join(unseen)}")
    tags_without_policy = sorted(set(var_rows) - set(var_tags))
    if tags_without_policy:
        failures.append(f"variant tags with no row policy: {tags_without_policy}")
    spelled_rows = sum(entry.rows for entry in var_tags.values() if entry.kept)
    print(f"  rows the lexicon spells: {rrp_rows} (expected {spelled_rows})")
    print(
        f"  headwords they fall under: {len(rrp_headwords)} of {CORPUS_HEADWORDS} "
        "(expected all of them)"
    )
    if rrp_rows != spelled_rows:
        failures.append(
            f"{rrp_rows} rows survive the row policy, expected {spelled_rows}"
        )
    if len(rrp_headwords) != CORPUS_HEADWORDS:
        failures.append(
            f"{len(rrp_headwords)} headwords survive the row policy, "
            f"expected {CORPUS_HEADWORDS}"
        )

    print("\nquirk rule applications:")
    for index, quirk in enumerate(quirk_rules):
        hits = quirk_hits.get(index, set())
        status = f"{len(hits)} rows" if hits else "UNUSED"
        print(f"  [{quirk.scope}] {quirk.match!r} -> {quirk.replacement!r}: {status}")
        if not hits:
            failures.append(f"quirk rule {quirk.match!r} matched nothing")
            continue
        listed = set(quirk.listed_words)
        unlisted = sorted(hits - listed)
        unseen = sorted(listed - hits)
        if unlisted:
            failures.append(
                f"quirk rule {quirk.match!r} touches unlisted words: {unlisted}"
            )
            print(f"    UNLISTED: {', '.join(unlisted)}")
        if unseen:
            failures.append(
                f"quirk rule {quirk.match!r} lists unmatched words: {unseen}"
            )
            print(f"    LISTED BUT UNMATCHED: {', '.join(unseen)}")

    print("\nstress overrides:")
    for override in sorted(overrides.values(), key=lambda r: (r.words, r.ipa)):
        hits = override_hits.get(override.ipa, set())
        print(
            f"  {override.words}: {override.token!r} -> {override.condition} "
            f"({len(hits)} rows)"
        )
        if not hits:
            failures.append(f"override {override.ipa!r} was never consulted")
        unlisted = sorted(hits - set(override.listed_words))
        if unlisted:
            failures.append(
                f"override {override.ipa!r} touches unlisted words: {unlisted}"
            )
        mechanical = letters(tokenize(override.ipa, mapping))
        overridden = letters(tokenize(override.ipa, mapping, overrides))
        if mechanical == overridden:
            failures.append(
                f"override {override.ipa!r} changes nothing; the mechanical rule "
                f"already yields {overridden}"
            )

    print("\nstressed EAR vs the ReadLex Shavian column (𐑽 count per row):")
    print(f"  agree: {shavian_ear_counts['agree']}")
    print(f"  disagree, listed in shavian-divergences.tsv: {len(divergence_hits)}")
    print(f"  disagree, UNEXPECTED: {len(unexpected)}")
    for line in unexpected[:20]:
        print(f"    {line}")
    print(
        f"  both zero (every ɪə unstressed or not before R): "
        f"{shavian_ear_counts['both_zero']}"
    )
    if unexpected:
        failures.append(
            f"{len(unexpected)} rows have a stressed EAR count that differs from the Shavian "
            f"column’s 𐑽 count and no row in shavian-divergences.tsv"
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
    print(
        f"  stressed: {token_counts.get(('ɪə', 'stressed'), 0)} occurrences, "
        f"{len(iea_audit['stressed'])} words"
    )
    print(
        f"  unstressed: {token_counts.get(('ɪə', 'unstressed'), 0)} occurrences, "
        f"{len(iea_audit['unstressed'])} words"
    )

    print("\ntop token counts:")
    for (ipa, condition), count in token_counts.most_common(15):
        print(f"  {ipa!r} {condition or '-'}: {count}")

    print("\northographic rules, rows rewritten:")
    for orthographic in RULES:
        changed = rule_changes.get(orthographic.id, 0)
        expected_count = EXPECTED_RULE_CHANGES.get(orthographic.id)
        mismatch = (
            ""
            if expected_count is None or changed == expected_count
            else f" MISMATCH ({expected_count})"
        )
        if isinstance(orthographic, Terminal):
            matched = rule_matches.get(orthographic.id, 0)
            print(
                f"  {orthographic.id:22} {changed:6} of {matched:6} matched{mismatch}"
            )
            if not matched:
                failures.append(
                    f"terminal {orthographic.id} matches no word in the corpus"
                )
        else:
            print(f"  {orthographic.id:22} {changed:6}{mismatch}")
        if expected_count is not None and changed != expected_count:
            failures.append(
                f"rule {orthographic.id} rewrote {changed} rows, "
                f"expected {expected_count}"
            )
    missing_expected = [rule for rule in RULE_IDS if rule not in EXPECTED_RULE_CHANGES]
    if missing_expected:
        failures.append(f"rules with no expected rewrite count: {missing_expected}")
    orphaned = [rule for rule in EXPECTED_RULE_CHANGES if rule not in RULE_IDS]
    if orphaned:
        failures.append(
            f"expected rewrite counts for rules that no longer exist: {orphaned}"
        )

    print("\nundecided words (need a row in rule-words.tsv or x-decisions.tsv):")
    for label in sorted(undecided):
        words = sorted(undecided[label])
        print(f"  {label}: {len(words)}")
        for word in words[:10]:
            print(f"    {word}")
        failures.append(f"{len(words)} undecided {label} words: {words[:10]}")
    if not undecided:
        print("  none")

    print("\nrule-words.tsv rows used:")
    for key in sorted(tables.words):
        if key not in rule_word_hits:
            failures.append(f"rule-words.tsv row {key} was never used")
    print(f"  {len(tables.words)} rows, {len(rule_word_hits)} used")

    print("\nx-decisions.tsv rows used:")
    unused_x_decisions = sorted(set(tables.x_decisions) - x_decision_hits)
    print(f"  {len(tables.x_decisions)} rows, {len(x_decision_hits)} used")
    if unused_x_decisions:
        failures.append(f"x-decisions.tsv rows never used: {unused_x_decisions}")
    print(f"  x-letters on words with no x: {len(stray_x_letters)}")
    for line in stray_x_letters[:10]:
        print(f"    {line}")
    if stray_x_letters:
        failures.append(f"{len(stray_x_letters)} x-letters on words without an x")
    print(
        f"  words with no X-letter in x-decisions.tsv that keep a pair: "
        f"{len(unsubstituted)}"
    )
    for line in unsubstituted[:10]:
        print(f"    {line}")
    if unsubstituted:
        failures.append(
            f"{len(unsubstituted)} words with no X-letter in x-decisions.tsv keep a "
            f"substitutable pair"
        )

    print("\nword signs and standard outlines, rows rewritten:")
    for key in sorted(tables.signs):
        if key not in sign_hits:
            failures.append(f"word-sign row {key} was never used for a corpus row")
    for word in sorted(set(EXPECTED_SIGN_CHANGES) | set(sign_changes)):
        changed = sign_changes.get(word, 0)
        expected_count = EXPECTED_SIGN_CHANGES.get(word)
        mismatch = (
            ""
            if expected_count is None or changed == expected_count
            else f" MISMATCH ({expected_count})"
        )
        print(f"  {word:12} {changed:4}{mismatch}")
        if expected_count is None:
            failures.append(f"{word!r} rewrites {changed} rows with no expected count")
        elif changed != expected_count:
            failures.append(
                f"word sign {word!r} rewrote {changed} rows, expected {expected_count}"
            )
    corroborated = {e.word for e in examples if e.rule in SIGN_ANCHORS}
    uncorroborated = sorted(set(sign_changes) - corroborated)
    print(f"  rewriting words with no Manual fixture: {uncorroborated or 'none'}")
    if uncorroborated:
        failures.append(
            f"these words rewrite rows but no manual-spellings.tsv row checks their "
            f"spelling against the Manual: {uncorroborated}"
        )
    rewriting_rows = {key for key in tables.signs if key[0] in sign_changes}
    print(
        f"  {len(tables.signs)} rows, {len(sign_hits)} used, "
        f"{len(tables.signs) - len(rewriting_rows)} that rewrite nothing"
    )
    for word, spelling in sorted(core_signs.items()):
        print(f"  core: {word:5} {spelling}")
    print(f"  core-eight rows disagreeing with their sign: {len(core_misses)}")
    for line in core_misses[:10]:
        print(f"    {line}")
    if core_misses:
        failures.append(f"{len(core_misses)} rows spell a core word sign in full")

    print(f"\nJunior divergences: {junior_rows} (want {EXPECTED_JUNIOR_DIVERGENCES})")
    for line in junior_mismatches[:10]:
        print(f"    {line}")
    if junior_rows != EXPECTED_JUNIOR_DIVERGENCES:
        failures.append(
            f"{junior_rows} rows have a Junior spelling, "
            f"expected {EXPECTED_JUNIOR_DIVERGENCES}"
        )
    if junior_mismatches:
        failures.append(
            f"{len(junior_mismatches)} Junior spellings differ from the spelling "
            f"without word signs or terminal-nt"
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

    print("\nthe Manual’s own lint, re-derived and run over every spelled row:")
    for check in CHECKS:
        broken = lint_hits.get(check.id, 0)
        exempted = sum(1 for key in exemptions if key[0] == check.id)
        print(f"  {check.id:34} {broken:5} broken, {exempted:3} exempted")
        for line in lint_examples[check.id]:
            print(f"      {line}")
        if broken:
            failures.append(
                f"lint {check.id} is broken by {broken} rows, and the Manual requires "
                f"that {check.requires}"
            )
    stale = sorted(set(exemptions) - lint_exempted)
    print(f"  exemptions never used: {stale or 'none'}")
    if stale:
        failures.append(f"lint exemptions that match nothing: {stale}")

    print("\nround trip, every spelling read back to a phoneme string:")
    print(f"  identical to the IPA it came from: {roundtrip_identical}")
    print(f"  word signs, which spell no sounds: {roundtrip_skipped}")
    print(f"  not readable back at all: {len(unreadable)}")
    for line in unreadable[:10]:
        print(f"    {line}")
    if unreadable:
        failures.append(
            f"{len(unreadable)} spellings cannot be read back to their own IPA by any "
            f"allowed difference"
        )
    if roundtrip_identical != EXPECTED_ROUNDTRIP_IDENTICAL:
        failures.append(
            f"{roundtrip_identical} spellings read back unchanged, "
            f"expected {EXPECTED_ROUNDTRIP_IDENTICAL}"
        )
    if roundtrip_skipped != EXPECTED_ROUNDTRIP_SKIPPED:
        failures.append(
            f"{roundtrip_skipped} word-sign rows skipped, "
            f"expected {EXPECTED_ROUNDTRIP_SKIPPED}"
        )
    for edit in sorted(set(EXPECTED_ROUNDTRIP_EDITS) | set(roundtrip)):
        found = roundtrip.get(edit, 0)
        expected_count = EXPECTED_ROUNDTRIP_EDITS.get(edit)
        mismatch = "" if found == expected_count else f" MISMATCH ({expected_count})"
        shape = f"{edit[0] or '-':4} -> {edit[1] or '-':4}"
        print(f"  {shape} {found:7}{mismatch}  {EDITS[edit]}")
        if expected_count is None:
            failures.append(f"round-trip difference {edit} has no expected count")
        elif found != expected_count:
            failures.append(
                f"round-trip difference {edit} occurs {found} times, "
                f"expected {expected_count}"
            )

    failures.extend(added(added_words, rows, mapping, quirk_rules, overrides, tables))
    failures.extend(passages(spellings, contractions))

    if failures:
        print(f"\nFAILED: {len(failures)} problem(s)")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("\nOK: every check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
