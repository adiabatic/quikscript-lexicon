from __future__ import annotations

from dataclasses import dataclass

from qslex.mapping import MapEntry, Mapping
from qslex.overrides import Override, Overrides

STRESS_MARKS = frozenset("ˈˌ")
CHUNK_SEPARATORS = frozenset(" -+")
VOWEL_CHARS = frozenset("ɪieæaɑɒɔʊuʌəɜːÆƏIⱭ")
NO_OVERRIDES: Overrides = {}


@dataclass(frozen=True)
class Token:
    ipa: str
    entry: MapEntry


class TokenizeError(ValueError):
    def __init__(self, ipa: str, position: int):
        self.ipa = ipa
        self.position = position
        super().__init__(
            f"no token matches {ipa!r} at position {position} ({ipa[position:]!r})"
        )


def tokenize(
    ipa: str, mapping: Mapping, overrides: Overrides = NO_OVERRIDES
) -> list[Token]:
    rule = overrides.get(ipa)
    tokens: list[Token] = []
    position = 0
    while position < len(ipa):
        for candidate in mapping.tokens_by_length:
            if not ipa.startswith(candidate, position):
                continue
            following = position + len(candidate)
            if candidate.endswith("ə") and ipa.startswith("ʊ", following):
                continue
            entry = _resolve(ipa, position, candidate, mapping, rule)
            tokens.append(Token(candidate, entry))
            position = following
            break
        else:
            raise TokenizeError(ipa, position)
    return tokens


def _resolve(
    ipa: str,
    position: int,
    token: str,
    mapping: Mapping,
    rule: Override | None,
) -> MapEntry:
    conditions = mapping.lookup[token]
    if "" in conditions:
        return conditions[""]
    if rule is not None and rule.token == token:
        return conditions[rule.condition]
    if "stressed" in conditions:
        return conditions["stressed" if is_stressed(ipa, position) else "unstressed"]
    return conditions["pre-r" if pre_r(ipa, position + len(token)) else "no-r"]


def pre_r(ipa: str, position: int) -> bool:
    while position < len(ipa) and ipa[position] in STRESS_MARKS:
        position += 1
    return position < len(ipa) and ipa[position] in ("r", "R")


def is_stressed(ipa: str, position: int) -> bool:
    start = position
    while start > 0 and ipa[start - 1] not in CHUNK_SEPARATORS:
        start -= 1
    index = position - 1
    while index >= start:
        char = ipa[index]
        if char in STRESS_MARKS:
            return True
        if char in VOWEL_CHARS:
            return False
        index -= 1
    end = position
    while end < len(ipa) and ipa[end] not in CHUNK_SEPARATORS:
        end += 1
    return not any(mark in STRESS_MARKS for mark in ipa[start:end])


def letters(tokens: list[Token]) -> str:
    parts: list[str] = []
    for token in tokens:
        if token.entry.kind == "hiatus":
            continue
        if token.entry.kind == "structural":
            parts.append(token.ipa)
        else:
            parts.extend("·" + name for name in token.entry.letters)
    return "".join(parts)


def qs(tokens: list[Token]) -> str:
    parts: list[str] = []
    for token in tokens:
        if token.entry.kind == "hiatus":
            continue
        if token.entry.kind == "structural":
            parts.append(token.ipa)
        else:
            parts.append(token.entry.qs)
    return "".join(parts)
