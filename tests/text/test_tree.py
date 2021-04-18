import pytest

from ggbot.text.grammar import iter_subsets


@pytest.mark.parametrize('s, indices, expected', [
    ('abcd', tuple(),   ('abcd', )),
    ('abcd', (0,),      ('', 'abcd')),
    ('abcd', (1,),      ('a', 'bcd')),
    ('abcd', (1, 2),    ('a', 'b', 'cd')),
    ('abcd', (2, ),     ('ab', 'cd')),
    ('abcd', (3, ),     ('abc', 'd')),
    ('abcd', (4, ),     ('abcd', '')),
    ('abcd', (5, ),     ('abcd', '')),
])
def test_iter_subsets(s, indices, expected):
    assert tuple(iter_subsets(s, indices)) == expected
