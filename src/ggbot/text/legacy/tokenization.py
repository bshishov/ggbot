from typing import Iterable, Callable
from dataclasses import dataclass
import re

__all__ = [
    'BaseTokenizer',
    'Tokenizer',
    'Token',
    'TextToken',
    'RefToken',
    'SlotToken'
]


@dataclass
class Token:
    start: int
    end: int
    raw: str

    @property
    def size(self):
        return self.end - self.start

    def __str__(self):
        return self.raw

    def __hash__(self):
        return hash(self.raw)


@dataclass
class TextToken(Token):
    text: str

    def __hash__(self):
        return hash(self.raw)


@dataclass
class RefToken(Token):
    target: str
    name: str

    def __hash__(self):
        return hash(self.raw)


@dataclass
class SlotToken(Token):
    name: str
    type: str

    def __hash__(self):
        return hash(self.raw)


class BaseTokenizer:
    def tokenize(self, text: str) -> tuple[Token]:
        raise NotImplementedError


class Tokenizer(BaseTokenizer):
    def __init__(self, text_postprocessing_fn: Callable[[str], str] = str.lower):
        self.re = re.compile(
            r'{[\w-]+(:[\w-]+)?}|'  # slot tokens  <n:some-ref>
            r'<[\w-]+(:[\w-]+)?>|'  # ref tokens
            r'[^\W\d_]+|'  # any alphabetical and non-numeric
            r'\d+|'
            r'[:";\'!@#$%^&*()<>?,./[\]{}\\|\-_+=]'
        )
        self.text_postprocessing_fn = text_postprocessing_fn

    def _match(self, text: str) -> Iterable[Token]:
        for match in self.re.finditer(text):
            token = match.group(0)
            started = match.pos
            ended = match.endpos
            if len(token) > 1 and token.startswith('<') and token.endswith('>'):
                parts = token[1:-1].split(':')
                if len(parts) == 1:
                    yield RefToken(
                        target=parts[0],
                        name=parts[0],
                        raw=token,
                        start=started,
                        end=ended
                    )
                else:
                    yield RefToken(
                        target=parts[1],
                        name=parts[0],
                        raw=token,
                        start=started,
                        end=ended
                    )
            elif token.startswith('{') and token.endswith('}'):
                parts = token[1:-1].split(':')
                if len(parts) == 1:
                    yield SlotToken(
                        name=parts[0],
                        type=parts[0],
                        raw=token,
                        start=started,
                        end=ended
                    )
                else:
                    yield SlotToken(
                        name=parts[0],
                        type=parts[1],
                        raw=token,
                        start=started,
                        end=ended
                    )
            else:
                yield TextToken(
                    text=self.text_postprocessing_fn(token),
                    raw=token,
                    start=started,
                    end=ended
                )

    def tokenize(self, text: str) -> tuple[Token]:
        return tuple(self._match(text))
