from qslex.tokenizer import tokenize
from qslex.validate import stressed_rhotic_ears

from conftest import MAPPING, OVERRIDES


def test_stressed_rhotic_ears_counts_only_rhotic_stressed() -> None:
    cases = [
        ("dɪəR", 1),
        ("ˈhæpɪəR", 0),
        ("ˈθɪətəR", 0),
        ("ænˈtɪərɪəR", 1),
        ("ˈbeɪkəR", 0),
    ]
    for ipa, expected in cases:
        assert stressed_rhotic_ears(ipa, tokenize(ipa, MAPPING, OVERRIDES)) == expected
