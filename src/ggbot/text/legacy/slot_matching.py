from typing import Iterable

import re

from .tokenization import Token, TextToken


__all__ = [
    'BaseSlotMatcher',
    'AnySlotMatcher',
    'FnSlotMatcher',
    'EmailSlotMatcher',
    'DiscordMentionMatcher'
]


def to_string(tokens: Iterable[Token], sep: str = ' ') -> str:
    return sep.join(t.raw for t in tokens)


class BaseSlotMatcher:
    def match(self, tokens: tuple[TextToken]) -> tuple[float, dict]:
        raise NotImplementedError


class AnySlotMatcher(BaseSlotMatcher):
    def match(self, tokens: tuple[TextToken]) -> tuple[float, dict]:
        return 0.5, {'match': to_string(tokens)}


class FnSlotMatcher(BaseSlotMatcher):
    def __init__(self, fn):
        self.fn = fn

    def match(self, tokens: tuple[TextToken]) -> tuple[float, dict]:
        raw = to_string(tokens, sep='')
        try:
            return 0.0, {'value': self.fn(raw)}
        except ValueError:
            return 1.0, {}


class EmailSlotMatcher(BaseSlotMatcher):
    def __init__(self):
        self.re = re.compile(r'[^@]+@[^@]+\.[^@]+')  # Yes it is simplified

    def match(self, tokens: tuple[TextToken]) -> tuple[float, dict]:
        raw = to_string(tokens, sep='')
        match = self.re.fullmatch(raw)
        if match:
            return 0.0, {'match': raw, 'email': match.group(0)}
        return 1.0, {}


class DiscordMentionMatcher(BaseSlotMatcher):
    def __init__(self):
        self.re = re.compile(r'<@!(\d+)>')

    def match(self, tokens: tuple[TextToken]) -> tuple[float, dict]:
        raw = to_string(tokens, sep='')
        match = self.re.fullmatch(raw)
        if match:
            return 0.0, {'match': raw, 'mention': match.group(1)}
        return 1.0, {}
