import pytest
from ggbot.text.text import find, tokenize


def pipeline(t: str) -> list:
    return tokenize(t)


@pytest.mark.parametrize('doc, pattern, expected', [
    ('very long string', 'very long string', 0),
    ('very long string', 'long string', 1),
    ('very long string', 'string', 2),
    ('very long string', 'very string', -1),
    ('very long string', 'even longer string', -1),
    ('very long string', 'banana', -1),
    ('very long string', '', 0),
    ('', 'something', -1),
])
def test_find(doc, pattern, expected):
    result = find(
        pipeline(doc),
        pipeline(pattern)
    )
    assert result == expected
