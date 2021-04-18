from typing import Optional, Any, Iterable, Union
from dataclasses import dataclass, field
from enum import Enum
import re
import logging

import yaml

from ggbot.text.base import NluBase, IntentMatchResultBase
from ggbot.text.distance import damerau_levenshtein_distance

__all__ = [
    'Nlu',
    'find',
    'tokenize',
    'match_pattern'
]

_logger = logging.getLogger(__name__)


class TokenType(Enum):
    TEXT = 0
    SLOT = 1
    NUMBER = 2


@dataclass
class Token:
    raw: str

    def as_string_to_match(self):
        return self.raw


@dataclass
class TextToken(Token):
    norm: str

    def as_string_to_match(self):
        return self.norm


@dataclass
class MentionToken(Token):
    mention: str


class PunctuationToken(Token):
    pass


@dataclass
class NumberToken(Token):
    number: float


@dataclass
class SlotToken(Token):
    slot: str


class TokenizationRule:
    def tokenize(
            self,
            token: Token,
            prev_token: Optional[Token] = None,
            next_token: Optional[Token] = None
    ) -> Iterable[Token]:
        raise NotImplementedError


class DigitNumberTokenizer(TokenizationRule):
    NUMBER_PATTERN = re.compile(r'[-+]?\d*\[.,]\d+|\d+')

    def tokenize(
            self,
            token: Token,
            prev_token: Optional[Token] = None,
            next_token: Optional[Token] = None
    ) -> Iterable[Token]:
        matches = self.NUMBER_PATTERN.findall(token.raw)
        if matches:
            yield NumberToken(
                raw=token.raw,
                number=float(matches[0])
            )
        else:
            yield token


class SlotTokenizer(TokenizationRule):
    def tokenize(
            self,
            token: Token,
            prev_token: Optional[Token] = None,
            next_token: Optional[Token] = None
    ) -> Iterable[Token]:
        if token.raw.startswith('{') and token.raw.endswith('}'):
            inner = token.raw[1:-1]
            yield SlotToken(
                raw=token.raw,
                slot=inner
            )
        else:
            yield token


class PunctuationTokenizer(TokenizationRule):
    PUNCTUATION_SYMBOLS = set(',.!?\'"()')

    def tokenize(
            self,
            token: Token,
            prev_token: Optional[Token] = None,
            next_token: Optional[Token] = None
    ) -> Iterable[Token]:
        first = token.raw[0]
        last = token.raw[-1]
        if last in self.PUNCTUATION_SYMBOLS and len(token.raw) > 1:
            yield Token(raw=token.raw[:-1])
            yield PunctuationToken(raw=last)
        elif first in self.PUNCTUATION_SYMBOLS and len(token.raw) > 1:
            yield PunctuationToken(raw=first)
            yield Token(raw=token.raw[1:])
        elif len(token.raw) == 1 and first in self.PUNCTUATION_SYMBOLS:
            yield PunctuationToken(raw=first)
        else:
            yield token


class TextTokenTokenizer(TokenizationRule):
    def tokenize(
            self,
            token: Token,
            prev_token: Optional[Token] = None,
            next_token: Optional[Token] = None
    ) -> Iterable[Token]:
        if type(token) == Token:
            yield TextToken(norm=token.raw.lower(), raw=token.raw)
        else:
            yield token


class MentionTokenizer(TokenizationRule):
    def tokenize(
            self,
            token: Token,
            prev_token: Optional[Token] = None,
            next_token: Optional[Token] = None
    ) -> Iterable[Token]:
        if token.raw.startswith('@') and len(token.raw) > 1:
            yield MentionToken(raw=token.raw, mention=token.raw[1:])
        else:
            yield token


_RULES: list[TokenizationRule] = [
    DigitNumberTokenizer(),
    PunctuationTokenizer(),
    SlotTokenizer(),
    MentionTokenizer(),
    TextTokenTokenizer()
]

_SPLIT_PATTERN = re.compile(r'\W+')


def tokenize(text: str) -> list[Token]:
    text = text.strip()
    if not text:
        return []
    tokens = []
    #raw_tokens = filter(bool, re.split(_SPLIT_PATTERN, text))
    for raw_token in text.split():
        raw_token = raw_token.strip()
        if raw_token:
            tokens.append(Token(raw=raw_token))
    for _ in range(1):
        for rule in _RULES:
            new_tokens = []
            for i, token in enumerate(tokens):
                prev_token = None
                next_token = None
                if i > 0:
                    prev_token = tokens[i-1]
                if i < len(tokens) - 1:
                    next_token = tokens[i+1]
                for new_token in rule.tokenize(token, prev_token, next_token):
                    new_tokens.append(new_token)
            tokens = new_tokens
    return tokens


def sim1(t1: Token, t2: Token) -> float:
    s1 = t1.as_string_to_match()
    s2 = t2.as_string_to_match()
    if s1 == s2:
        return 1.0
    distance = damerau_levenshtein_distance(s1, s2)
    return 1.0 - distance / max(len(s1), len(s2))


def locate_similar(t: Token, tl: Iterable[tuple[int, Token]]) -> tuple[int, float]:
    loc = -1
    max_similarity = 0.0
    for index, t2 in tl:
        similarity = sim1(t, t2)
        if similarity > max_similarity:
            max_similarity = similarity
            loc = index
    return loc, max_similarity


def _iter_l2r(arr: list, s: int):
    for i in range(s, len(arr)):
        yield i, arr[i]


def _iter_r2l(arr: list, s: int):
    s = min(len(arr) - 1, s)
    for i in range(s, 0, -1):
        yield i, arr[i]


def locate_similar_l2r(t: Token, tl: list[Token], start: int = 0) -> tuple[int, float]:
    return locate_similar(t, _iter_l2r(tl, start))


def locate_similar_r2l(t: Token, tl: list[Token], start: int = 0) -> tuple[int, float]:
    return locate_similar(t, _iter_r2l(tl, start))


@dataclass
class MatchResult:
    score: float
    slots: dict[str, list[Token]] = field(default_factory=dict)


def match_pattern(
        tl: list[Token],
        tp: list[Token],
        sim_threshold: float = 0.5,
        l2r_sim_coeff: float = 0.8,
        token_disposition_coeff: float = 0.2
) -> MatchResult:
    score = 0
    expected_loc = -1
    p_token_locations = []
    for p in tp:
        if isinstance(p, SlotToken):
            expected_loc += 1

        loc, sim = locate_similar_l2r(p, tl, expected_loc + 1)
        if loc < 0 or sim <= sim_threshold:
            loc, sim = locate_similar_r2l(p, tl, expected_loc - 1)
            sim *= l2r_sim_coeff

        if loc >= 0 and sim > sim_threshold:
            #print(f'Matched \'{p}\' with \'{tl[loc]}\'')
            score += sim
            score -= abs(expected_loc - loc) * token_disposition_coeff
            expected_loc = loc

        p_token_locations.append(loc)

    slots = {}
    for i, p in enumerate(tp):
        if not isinstance(p, SlotToken):
            continue

        prev_token_loc = -1
        next_token_loc = -1

        if i > 0:
            # From previous token in pattern to the start of the pattern
            # find first that has determined location
            for j in range(i - 1, -1, -1):
                prev_token_loc = p_token_locations[j]
                if prev_token_loc >= 0:
                    break

        if i < len(tp) - 1:
            # From next token in pattern to the end of the pattern
            # find first that has determined location
            for j in range(i + 1, len(tp)):
                next_token_loc = p_token_locations[j]
                if next_token_loc >= 0:
                    break

        # No boundary on left (match from start)
        if prev_token_loc < 0:
            prev_token_loc = -1

        # No boundary on the right (match till the end)
        if next_token_loc < 0:
            next_token_loc = len(tl)

        matched_tokens = tl[prev_token_loc+1:next_token_loc]
        slots[p.slot] = matched_tokens

    return MatchResult(slots=slots, score=score)


def load_synonyms(path: str) -> dict[str, list[list[Token]]]:
    synonyms = {}
    with open(path, encoding='utf-8') as f:
        data = yaml.full_load(f)
        for key, values in data.items():
            options = []
            for v in values:
                options.append(tokenize(v))
            synonyms[key] = options
    return synonyms


def find(tl: list[Token], pattern: list[Token], sim_threshold: float = 0.5) -> int:
    if not tl:
        return -1
    if not pattern:
        return 0

    first_loc, sim = locate_similar_l2r(pattern[0], tl)
    if first_loc < 0 or sim < sim_threshold:
        return -1

    remaining_len = len(tl) - first_loc
    if len(pattern) > remaining_len:
        return -1

    for i in range(1, len(pattern)):
        if sim1(tl[first_loc + i], pattern[i]) < sim_threshold:
            return -1
    return first_loc


def as_raw_text(tl: list[Token]) -> str:
    return ' '.join(t.raw for t in tl)


def replace_synonyms(tl: list[Token], synonyms, sim_threshold: float = 0.5) -> list[Token]:
    result = tl
    for replacement, synonyms in synonyms.items():
        for syn in synonyms:
            syn_loc = find(result, syn, sim_threshold)
            if syn_loc >= 0:
                result = result[:syn_loc] + [Token(replacement)] + result[syn_loc+len(syn):]
    return result


def load_intents(path: str, pipeline) -> dict[str, list[list[Token]]]:
    intents = {}
    with open(path, encoding='utf-8') as f:
        data = yaml.full_load(f)['intents']
        for intent, phrases_raw in data.items():
            phrases = []
            for phrase in phrases_raw:
                phrases.append(pipeline(phrase))
            intents[intent] = phrases
    return intents


def match_intent(
        tl: list[Token],
        intents: dict[str, list[list[Token]]]
) -> tuple[str, MatchResult]:
    best_match = None
    best_match_intent = None
    best_match_score = -1
    for intent, phrases in intents.items():
        for phrase in phrases:
            match = match_pattern(tl, phrase)
            if match.score > best_match_score:
                best_match_score = match.score
                best_match_intent = intent
                best_match = match
    return best_match_intent, best_match


@dataclass
class _IntentMatchResult(IntentMatchResultBase):
    intent: str
    confidence: float
    slots: dict[str, list[Token]]

    def get_confidence(self) -> float:
        return self.confidence

    def get_intent(self) -> str:
        return self.intent

    def get_slot_value(self, slot_name: str) -> Optional[str]:
        if slot_name not in self.slots:
            return None
        return as_raw_text(self.slots[slot_name])

    def get_all_slots(self) -> dict[str, str]:
        return {k: as_raw_text(v) for k, v in self.slots.items()}


class Nlu(NluBase):
    def __init__(self, intents, synonyms):
        self.intents = intents
        self.synonyms = synonyms

    def match_any_intent(self, text: str) -> Optional[IntentMatchResultBase]:
        return self._match_intent(text, self.intents)

    def match_intent_one_of(self,
                            text: str,
                            intents: Iterable[str]) -> Optional[IntentMatchResultBase]:
        intents_to_match = {}
        for intent in intents:
            if intent in self.intents:
                intents_to_match[intent] = self.intents[intent]
        return self._match_intent(text, intents_to_match)

    def _match_intent(self, text: str, intents_to_match: dict) -> Optional[IntentMatchResultBase]:
        tokenized = tokenize(text)
        _logger.debug(f'Tokenized {text} as {tokenized}')

        tokenized = replace_synonyms(tokenized, self.synonyms, sim_threshold=0.9)
        _logger.debug(f'Replaced synonyms: {tokenized}')

        intent, match = match_intent(tokenized, intents_to_match)
        if intent is None or match is None:
            _logger.debug(f'No match for {text}')
            return None

        result = _IntentMatchResult(
            intent=intent,
            confidence=match.score,
            slots=match.slots
        )
        _logger.debug(f'Matched {result}')
        return result

    @classmethod
    def load(cls, intents_path: str, synonyms_path: str):
        synonyms = load_synonyms(synonyms_path)

        def _pipeline(text: str):
            result = tokenize(text)
            result = replace_synonyms(result, synonyms, sim_threshold=0.9)
            return result

        intents = load_intents(intents_path, _pipeline)
        return Nlu(
            intents=intents,
            synonyms=synonyms
        )


def test_():
    m = match_pattern(
        tokenize('@gg-bot найди phasmophobia в стиме'),
        tokenize('найди {game} в стиме')
    )

    synonyms = load_synonyms('domain/synonyms.yaml')

    def _pipeline(text: str):
        tokens = tokenize(text)
        tokens = replace_synonyms(tokens, synonyms)
        return tokens

    match_pattern(
        _pipeline('гайз кто хочет в дотан'),
        _pipeline('гайз, кто хочет в {game}?')
    )

    intents = load_intents('domain/intents.yaml', _pipeline)

    test_phrases = [
        '@gg-bot добавь дотан в голосование',
        'всратый бот! добавь чертов дотан в голосование)))!',
        'добавь дотан в голосование',
        'удали доту плз',
        'давай поиграем',
        'гайз кто хочет в дотан',
        'пойдете в доту?',
        'в доту не желаете?',
        'в доту пойдете?',
        'mb dota?',
        'пойдем во что-нить?',
        'можт ow? @here',
        'Никто не хочет сегодня крутануть рулетку/сходить во что-нибудь?',
        ''
    ]

    for phrase in test_phrases:
        p = _pipeline(phrase)
        print(f'{phrase}   {as_raw_text(p)}')
        intent, match = match_intent(p, intents)
        if intent:
            print(f'intent: {intent}')
            print(f'score: {match.score}')
            print(f'slots: {match.slots}')
        print()

    """
    x = tokenize('@gg-bot добавь дотан в голосование')
    pattern = tokenize('{mention} добавь {game} в голосование')
    for t in x:
        print(t)
    print()
    for t in pattern:
        print(t)

    m1 = match_pattern(
        tokenize('всратый бот! добавь чертов дотан в голосование)))!'),
        tokenize('{mention} добавь {game} в голосование')
    )
    print(m1)
    """


if __name__ == '__main__':
    test_()
