from typing import Optional
import pytest
from ggbot.text.legacy.en2ru import en2ru, Match, match_rule


@pytest.mark.skip
@pytest.mark.parametrize(
    "src,expected",
    [
        ("hello", "хелло"),
        ("london", "лондон"),
        ("is", "is"),
        ("the", "зэ"),
        ("capital", "кэпитал"),
    ],
)
def test_en2ru(src: str, expected: str):
    ru_transcription = en2ru(src)
    assert ru_transcription == expected


@pytest.mark.parametrize(
    "text,rule,start,expected",
    [
        ("abc", "abc", 0, Match()),
        ("abc", "abc", 1, None),
        ("abc", "b", 0, None),
        ("abc", "b", 1, Match()),
        ("abc", "(b)", 1, Match(1, 2)),
        ("abc", "&(b)", 0, Match(1, 2)),
        ("abc", "&#c", 0, Match()),
        ("abc", "^abc$", 0, Match()),
        ("abc", "^(ab.)$", 0, Match(0, 3)),
        ("this", "(th)&", 0, Match(0, 2)),
        ("the", "(th)$", 0, None),
        ("this", "(th)$", 0, None),
        ("these", "(th)$", 0, None),
    ],
)
def test_match_rule(text: str, rule: str, start: int, expected: Optional[str]):
    match = match_rule(text, rule, start=start)
    assert match == expected
