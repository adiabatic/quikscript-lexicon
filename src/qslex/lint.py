from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from qslex.elements import DIVIDERS, chunks, components, elements
from qslex.letters import VOWELS, Letters, names, parse
from qslex.rules import AL, ALLY, ENT, ING_TAILS, X_LETTERS, Tables
from qslex.tables import rows_of
from qslex.tokenizer import marked

EXEMPTIONS_FILE = "lint-exemptions.tsv"
EXEMPTIONS_HEADER = ["check", "word", "reason", "note"]

# The only reason `load_exemptions` accepts. A row may exempt a word from a check only because of a known defect tracked in another issue.
DEFECT = "known-defect"

REDUCIBLE = frozenset({"It", "Utter"})
VOWEL_CHARS = frozenset("ɪieæaɑɒɔʊuʌəɜːƏIÆⱭ")

# The Manual says “While L needs no preceding vowel in Spaniel = ·See·Pea·At·No·Ye·Low, one is clearly needed wherever -al follows on a vowel-sound”. ·Ye counts here as the vowel it stands in for.
VOWELS_BEFORE_L = VOWELS | {"Ye"}

# Each check runs only where the Orthodox spelling has the ending the Manual’s rule names. Without that condition a check would report ReadLex’s IPA wherever it differs from the rule. For example, ·Et·No·Tea is wrong only where the Orthodox spelling ends in -ent. The lint does not check ReadLex’s /e/ anywhere else. A check whose rule matches the same ending uses that rule’s pattern: `rules.ENT`, `rules.AL` and `rules.ALLY`. `rules.ALLY` matches -able and -ally, so the -al check skips those words, as the terminal rules do by trying `rules.ALLY` before `rules.AL`. The two patterns below differ from `rules.LAND` because -men is the exception to the -land rule and has its own check.
LAND = re.compile(r"(?<=.)(land|ment|man)(s)?$")
MEN = re.compile(r"(?<=.)men$")


@dataclass(frozen=True)
class Site:
    """One element of one entry, as the lint sees it."""

    word: str
    latin: str
    letters: Letters
    x_letter: Letters
    ipa: str
    last: bool

    @property
    def spelled(self) -> tuple[str, ...]:
        return names(self.letters)

    @property
    def x_spelled(self) -> tuple[str, ...]:
        return names(self.x_letter or self.letters)

    @property
    def stressed(self) -> bool:
        return marked(self.ipa)

    @property
    def reducible_ending(self) -> bool:
        """Whether the last vowel ReadLex wrote for this element is a schwa.

        Every rule these checks re-derive applies to an *unstressed* vowel. ə is the only vowel ReadLex writes that is always unstressed. ɪ and ʌ are often full vowels (distil, fulfil, until), so treating them as reducible would make the checks report false positives.
        """
        vowels = [c for c in self.ipa if c in VOWEL_CHARS]
        return bool(vowels) and vowels[-1] in {"ə", "Ə"}


@dataclass(frozen=True)
class Check:
    id: str
    requires: str
    test: Callable[[Site, Tables], str]


def _tail(site: Site, *shape: str) -> bool:
    return site.spelled[-len(shape) :] == shape


def _before(spelled: tuple[str, ...], shape: tuple[str, ...]) -> str:
    return spelled[-len(shape) - 1] if len(spelled) > len(shape) else ""


def _ing_affix(latin: str) -> str:
    for tail in ING_TAILS:
        if latin.endswith(tail) and latin.rindex("ing") > 0:
            return tail
    return ""


ING_SHAPES = {
    "ing": ("-ing",),
    "ings": ("-ing", "Zoo"),
    "ingly": ("-ing", "Low", "It"),
    "ingness": ("-ing", "No", "Et", "See"),
}


def ing_vowel_omitted(site: Site, tables: Tables) -> str:
    """“Provided it is an affix and not a root, omit vowel-i.” (terminal-ing)

    “Spell -ing in full after roots ending in -y: ·Key·At·Roe·It·It·-ing = carrying.” The check also skips roots ending in -i (taxi, ski), which are the same case.
    """
    affix = _ing_affix(site.latin)
    stem = site.latin[: site.latin.rindex("ing")] if affix else ""
    if not affix or stem.endswith(("y", "i")):
        return ""
    if tables.has_decision("terminal-ing", site.latin):
        return ""
    shape = ING_SHAPES[affix]
    if not _tail(site, *shape):
        return ""
    return "·It before the -ing" if _before(site.spelled, shape) == "It" else ""


def al_vowel_omitted(site: Site, tables: Tables) -> str:
    """“omit any unstressed vowel sound between L and the preceding consonant”

    Runs only on an entry’s last element. The Manual says “Where another syllable is added, the vowel sound before this L must be clearly pronounced and spelt”, and a following element adds a syllable as a suffix does. (terminal-al-el-le-il)
    """
    if not site.last or not AL.search(site.latin) or ALLY.search(site.latin):
        return ""
    if not site.reducible_ending:
        return ""
    spelled = site.spelled
    if spelled and spelled[-1] in {"Zoo", "See"} and site.latin.endswith("s"):
        spelled = spelled[:-1]
    if len(spelled) < 3 or spelled[-1] != "Low" or spelled[-2] not in REDUCIBLE:
        return ""
    if spelled[-3] in VOWELS_BEFORE_L:
        return ""
    return f"·{spelled[-2]} between a consonant and the final ·Low"


def ent_ance_utter(site: Site, tables: Tables) -> str:
    """“Written invariably with — ·Utter·No followed by a penlift” (terminal-ent-ance)"""
    match = ENT.search(site.latin)
    if not match or LAND.search(site.latin) or not site.reducible_ending:
        return ""
    shape = ("No", "Tea") if match.group(1) in {"ent", "ant"} else ("No", "See")
    if not _tail(site, *shape):
        return ""
    before = _before(site.spelled, shape)
    return f"·{before} before ·No, not ·Utter" if before not in {"Utter", ""} else ""


def land_ment_vowel_omitted(site: Site, tables: Tables) -> str:
    """“The unstressed vowel is omitted for convenient joining except in -men.”

    (terminal-land-ment)
    """
    match = LAND.search(site.latin)
    if not match or not site.reducible_ending:
        return ""
    ending = match.group(1)
    shape = {"land": ("No", "Day"), "ment": ("No", "Tea"), "man": ("No",)}[ending]
    consonant = {"land": "Low", "ment": "May", "man": "May"}[ending]
    if site.latin.endswith("s") and site.spelled[-1:] == ("Zoo",):
        spelled = site.spelled[:-1]
    else:
        spelled = site.spelled
    if spelled[-len(shape) :] != shape:
        return ""
    vowel = spelled[-len(shape) - 1] if len(spelled) > len(shape) else ""
    if vowel not in REDUCIBLE:
        return ""
    keeps = spelled[-len(shape) - 2] if len(spelled) > len(shape) + 1 else ""
    if keeps != consonant:
        return ""
    return f"·{vowel} kept between ·{consonant} and the -{ending}"


def men_keeps_a_vowel(site: Site, tables: Tables) -> str:
    """“The unstressed vowel is omitted for convenient joining except in -men.”

    The Manual says the vowel is kept but not which vowel, and ReadLex writes both. seamen ˈsiːmen gives ·May·Et·No, and dutchmen ˈdʌtʃmən gives ·May·Utter·No. Either vowel keeps seamen distinct from seaman, which is the purpose of the exception. Requiring ·Et would add a sound the corpus does not record. (terminal-land-ment)
    """
    if not MEN.search(site.latin) or not _tail(site, "No"):
        return ""
    vowel = _before(site.spelled, ("No",))
    if not vowel or vowel in VOWELS:
        return ""
    return f"-men joined straight onto ·{vowel}, with no vowel kept"


def initial_ex_et(site: Site, tables: Tables) -> str:
    """“·Et·Excite for Excite, Extreme, Expect with an initial vowel ·Et easier than ·It.” (section-2)"""
    spelled = site.x_spelled
    if not site.latin.startswith("ex") or len(spelled) < 2:
        return ""
    if spelled[1] not in X_LETTERS or site.stressed:
        return ""
    return f"·{spelled[0]} before the X-letter, not ·Et" if spelled[0] != "Et" else ""


def x_letter_only_with_x(site: Site, tables: Tables) -> str:
    """“but only where Orthodox spells these sounds with X … and only one ·Excite in Xerxes.” (section-2)"""
    used = sum(1 for name in site.x_spelled if name in X_LETTERS)
    available = site.latin.count("x")
    if used <= available:
        return ""
    return f"{used} X-letters for {available} x in the Latin"


CHECKS: tuple[Check, ...] = (
    Check(
        "terminal-ing-vowel-omitted",
        "an -ing affix is written ·-ing with no ·It before it",
        ing_vowel_omitted,
    ),
    Check(
        "terminal-al-vowel-omitted",
        "a final L drops the unstressed vowel before it, after a consonant",
        al_vowel_omitted,
    ),
    Check(
        "terminal-ent-ance-utter",
        "-ent, -ant, -ence and -ance are written invariably with ·Utter·No",
        ent_ance_utter,
    ),
    Check(
        "terminal-land-ment-vowel-omitted",
        "-land, -ment and -man omit the unstressed vowel",
        land_ment_vowel_omitted,
    ),
    Check(
        "terminal-men-keeps-a-vowel",
        "-men keeps its vowel",
        men_keeps_a_vowel,
    ),
    Check(
        "initial-ex-et",
        "an initial ex- takes ·Et before the X-letter",
        initial_ex_et,
    ),
    Check(
        "x-letter-only-with-x",
        "no more X-letters than the Latin has x",
        x_letter_only_with_x,
    ),
)

CHECK_IDS = tuple(check.id for check in CHECKS)


def load_exemptions(path: Path | None = None) -> dict[tuple[str, str], str]:
    """The rows of `lint-exemptions.tsv`, as (check, word) mapped to the reason.

    Each row exempts one word from one lint check because of a known defect tracked in another issue. Every row must give the reason `known-defect` and a note that describes the defect, so the table cannot become a list of unexplained exceptions.
    """
    exemptions: dict[tuple[str, str], str] = {}
    for lineno, source, row in rows_of(path, EXEMPTIONS_FILE, EXEMPTIONS_HEADER):
        check, word, reason, note = row
        if check not in CHECK_IDS:
            raise ValueError(f"{source}:{lineno}: {check!r} is not a check")
        if reason != DEFECT:
            raise ValueError(
                f"{source}:{lineno}: reason must be {DEFECT!r}, got {reason!r}"
            )
        if not note:
            raise ValueError(
                f"{source}:{lineno}: a known defect needs a note saying what it is"
            )
        key = (check, word)
        if key in exemptions:
            raise ValueError(f"{source}:{lineno}: duplicate exemption for {key}")
        exemptions[key] = reason
    return exemptions


def sites(word: str, spelling: str, x_letter: str, ipa: str) -> tuple[Site, ...]:
    """One Site per element, split where `qslex.elements` splits.

    If the Latin parts and the spelling’s runs do not line up one for one, the whole entry is treated as one element. If the IPA does not split into one chunk per word, each element gets the whole IPA string.
    """
    letters = parse(spelling)
    pairs = elements(word, letters)
    x_elements = elements(word, parse(x_letter)) if x_letter else None
    if pairs is None:
        return (Site(word, word, letters, parse(x_letter), ipa, True),)
    words = [part for part in components(word) if part not in DIVIDERS]
    runs = [run for part, run in pairs if part not in DIVIDERS]
    x_letter_runs = (
        [run for part, run in x_elements if part not in DIVIDERS]
        if x_elements is not None and len(x_elements) == len(pairs)
        else [()] * len(runs)
    )
    said = chunks(ipa, len(words))
    return tuple(
        Site(word, latin, run, tuple(other), chunk, index == len(words) - 1)
        for index, (latin, run, other, chunk) in enumerate(
            zip(words, runs, x_letter_runs, said, strict=True)
        )
    )


def lint(
    word: str,
    spelling: str,
    x_letter: str,
    ipa: str,
    tables: Tables,
) -> tuple[tuple[str, str, str], ...]:
    """Every check this entry breaks, as (check id, element, what is wrong)."""
    out: list[tuple[str, str, str]] = []
    for site in sites(word, spelling, x_letter, ipa):
        for check in CHECKS:
            complaint = check.test(site, tables)
            if complaint:
                out.append((check.id, site.latin, complaint))
    return tuple(out)
