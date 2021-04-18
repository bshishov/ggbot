import pytest

from ggbot.text.tokenization import Tokenizer


@pytest.fixture
def tokenizer():
    return Tokenizer()


@pytest.mark.parametrize('text, expected', [
    ('hello', ('hello', )),
    ('hello world', ('hello', 'world')),
    ('hello?', ('hello', '?')),
    ('hello?', ('hello', '?')),
    ('user: email is a@b.c.d', ('user', ':', 'email', 'is', 'a', '@', 'b', '.', 'c', '.', 'd')),
    ('hello <other>', ('hello', '<other>')),
    ('hello <other:named>', ('hello', '<other:named>')),
    ('hello {slot}', ('hello', '{slot}')),
    ('hello {named:slot}', ('hello', '{named:slot}')),
    ('слово', ('слово',)),
    ('{слот}', ('{слот}', )),
    ('{не слот}', ('{', 'не', 'слот', '}')),
    ('hello < other>', ('hello', '<', 'other', '>')),
    ('hello { other}', ('hello', '{', 'other', '}')),
    ('25k', ('25', 'k')),
    ('25 k', ('25', 'k')),
    ('привет мир', ('привет', 'мир')),
    ('67тыс', ('67', 'тыс')),
])
def test_tokenizer(tokenizer, text, expected):
    actual = tuple(map(str, tokenizer.tokenize(text)))
    assert actual == expected
