from typing import Iterable, Optional, Dict
from dataclasses import dataclass, field
import itertools

import jinja2
from jinja2.nativetypes import NativeEnvironment
from Stemmer import Stemmer

from ggbot.text.legacy.distance import damerau_levenshtein_distance
from ggbot.text.base import NluBase, IntentMatchResultBase
from ggbot.text.legacy.tokenization import *
from ggbot.utils import load_yamls
from ggbot.text.legacy.slot_matching import *


__all__ = [
    "Matcher",
    "TGrammar",
    "GrammarBasedNlu",
    "GrammarBasedNluMatchResult",
    "grammar_from_dict",
]


STEMMER = Stemmer("russian")
JINJA_ENV = NativeEnvironment()


def to_string(tokens: Iterable[Token]) -> str:
    return " ".join(t.raw for t in tokens)


@dataclass
class Rule:
    tokens: tuple[Token]
    meta: dict = field(default_factory=dict)

    _targets: set[str] = None

    def __post_init__(self):
        for k, v in self.meta.items():
            if isinstance(v, str):
                self.meta[k] = JINJA_ENV.from_string(v)

    def get_ref_targets(self) -> set[str]:
        if self._targets is None:
            self._targets = {t.target for t in self.tokens if isinstance(t, RefToken)}
        return self._targets

    def render_meta(self, context) -> dict:
        if not context:
            return self.meta
        result = {}
        for k, v in self.meta.items():
            if isinstance(v, jinja2.Template):
                result[k] = v.render(context)
            else:
                result[k] = v
        return result


@dataclass
class RuleSet:
    name: str
    rules: list[Rule]
    meta: dict = field(default_factory=dict)


TGrammar = Dict[str, RuleSet]


def validate_grammar(grammar: TGrammar):
    for ruleset in grammar.values():
        for rule in ruleset.rules:
            for t in rule.tokens:
                if isinstance(t, RefToken):
                    assert t.target in grammar, (
                        f"Invalid target {t.target} "
                        f"in rule: '{to_string(rule.tokens)}' "
                        f"in ruleset '{ruleset.name}'"
                    )


tokenizer = Tokenizer(text_postprocessing_fn=lambda t: STEMMER.stemWord(t))


def tokenize(text: str, parameters: bool) -> tuple[Token]:
    return tokenizer.tokenize(text)


def grammar_from_dict(data: dict) -> TGrammar:
    grammar = {}
    for key, ruleset_raw in data.items():
        rules = []
        for raw_rule in ruleset_raw:
            if isinstance(raw_rule, str):
                rules.append(Rule(tokens=tokenize(raw_rule, parameters=True)))
            elif isinstance(raw_rule, dict):
                for k, v in raw_rule.items():
                    rules.append(Rule(tokens=tokenize(k, parameters=True), meta=v))
        ruleset = RuleSet(name=key, rules=rules)
        grammar[key] = ruleset
    return grammar


def text_token_distance(t1: TextToken, t2: TextToken) -> float:
    # return 1.0 - float(t1.text == t2.text)
    return damerau_levenshtein_distance(t1.text, t2.text) / max(
        len(t1.text), len(t2.text)
    )


def iter_subsets(s, indices):
    """
    s     idx       result
    abcd  ()        abcd,
    abcd  (1,)      a,bcd
    abcd  (1,2)     a,b,cd
    """
    start = 0
    for idx in indices:
        yield s[start:idx]
        start = idx
    yield s[start:]


class Matcher:
    def __init__(
        self,
        grammar: TGrammar,
        slot_matchers: dict[str, BaseSlotMatcher],
        default_slot_matcher: BaseSlotMatcher = AnySlotMatcher(),
    ):
        self.grammar = grammar
        self.default_slot_matcher = default_slot_matcher
        self.cache = {}
        self.slot_matchers = slot_matchers

    def match(self, tokens: tuple[TextToken], rule: Rule) -> tuple[float, dict]:
        tokens_len = len(tokens)
        pattern_len = len(rule.tokens)

        if tokens_len < pattern_len:
            # Sequence is too short to match
            return 1.0, {}

        best_distance = 100.0
        best_meta = {}

        for indices in itertools.combinations(range(1, tokens_len), pattern_len - 1):
            combination_distance = 0.0
            combination_meta = {}

            for subset, rule_token in zip(iter_subsets(tokens, indices), rule.tokens):
                cache_key = (subset, rule_token)

                if cache_key in self.cache:
                    match_distance, match_meta = self.cache.get(cache_key)
                else:
                    match_distance, match_meta = self.tokens_to_token_match(
                        subset, rule_token
                    )
                    self.cache[cache_key] = match_distance, match_meta

                combination_distance += match_distance
                if isinstance(rule_token, (RefToken, SlotToken)):
                    combination_meta[rule_token.name] = match_meta

            if combination_distance < best_distance:
                best_distance = combination_distance
                best_meta = combination_meta
                if combination_distance == 0.0:
                    # Perfect match
                    break

        best_meta["distance"] = best_distance
        best_meta["rule"] = to_string(rule.tokens)
        best_meta.update(rule.render_meta(best_meta))
        return best_distance / pattern_len, best_meta

    def match_ruleset(
        self, tokens: tuple[TextToken], ruleset: RuleSet
    ) -> tuple[float, dict]:
        best_distance = 100.0
        best_meta = {}

        for rule in ruleset.rules:
            match_distance, match_meta = self.match(tokens, rule)
            if match_distance < best_distance:
                best_distance = match_distance
                best_meta = match_meta
                if match_distance == 0.0:
                    # Perfect match
                    break

        best_meta["ruleset"] = ruleset.name
        return best_distance, best_meta

    def tokens_to_token_match(
        self, tokens: tuple[TextToken], token: Token
    ) -> tuple[float, dict]:
        if isinstance(token, TextToken):
            s1 = " ".join(t.text for t in tokens)
            s2 = token.text

            if len(s1) > len(s2) * 2:
                return 1.0, {}

            # print(s1, s2)
            return damerau_levenshtein_distance(s1, s2) / max(len(s1), len(s2)), {}
            # if len(tokens) > 1:
            #    return 1.0, {}
            # return text_token_distance(tokens[0], token), {}
        elif isinstance(token, SlotToken):
            slot_matcher = self.slot_matchers.get(token.type, self.default_slot_matcher)
            return slot_matcher.match(tokens)
        elif isinstance(token, RefToken):
            ruleset = self.grammar[token.target]
            return self.match_ruleset(tokens, ruleset)
        raise TypeError(f"Unexpected token type: {type(token)}")


def iter_rule(rule: Rule, grammar: TGrammar) -> Iterable[Iterable[TextToken]]:
    def _token_variants_gen() -> Iterable[Iterable[TextToken]]:
        for _t in rule.tokens:
            if isinstance(_t, RefToken):
                yield iter_ruleset(grammar[_t.target], grammar)
            else:
                yield ((_t,), None),

    for combination in itertools.product(*_token_variants_gen()):
        result = []
        ctx = {}
        for token_index, (tokens, rule_meta) in enumerate(combination):
            rule_token = rule.tokens[token_index]
            for t in tokens:
                result.append(t)

            if isinstance(rule_token, RefToken):
                tgt = rule_token.target
                if tgt not in ctx:
                    ctx[tgt] = []
                ctx[tgt].append(rule_meta)

        yield result, rule.render_meta(ctx)
    return


def iter_ruleset(
    ruleset: RuleSet, grammar: TGrammar
) -> Iterable[tuple[Iterable[TextToken], dict]]:
    for rule in ruleset.rules:
        for combination in iter_rule(rule, grammar):
            yield combination


def iter_rules(grammar: TGrammar) -> Iterable[Iterable[TextToken]]:
    for key, ruleset in grammar.items():
        for combination in iter_ruleset(ruleset, grammar):
            yield combination


class GrammarBasedNluMatchResult(IntentMatchResultBase):
    def __init__(self, intent: str, distance: float, meta: dict):
        self.intent = intent
        self.meta = meta
        self.distance = distance

    def get_confidence(self) -> float:
        return 1.0 - self.distance

    def get_intent(self) -> str:
        return self.intent

    def get_slot_value(self, slot_name: str) -> Optional[str]:
        return self.meta[slot_name]

    def get_all_slots(self) -> dict[str, str]:
        return self.meta


class GrammarBasedNlu(NluBase):
    def __init__(self, grammar: TGrammar, matcher: Matcher = None):
        self._matcher = matcher or Matcher(
            grammar,
            slot_matchers={
                "float": FnSlotMatcher(float),
                "int": FnSlotMatcher(int),
                "email": EmailSlotMatcher(),
                "mention": DiscordMentionMatcher(),
                "text": AnySlotMatcher(),
            },
            default_slot_matcher=AnySlotMatcher(),
        )
        self._grammar = grammar
        self._intents = [
            ruleset.name
            for ruleset in self._grammar.values()
            if "intent" in ruleset.name
        ]

    def match_any_intent(self, text: str) -> Optional[IntentMatchResultBase]:
        return self.match_intent_one_of(text, self._intents)

    def match_intent_one_of(
        self, text: str, intents: Iterable[str]
    ) -> Optional[IntentMatchResultBase]:
        tokens = tokenize(text, parameters=False)

        best_distance = 1.0
        best_meta = {}
        best_intent = None

        for intent in intents:
            if intent in self._grammar:
                distance, meta = self._matcher.match_ruleset(
                    tokens, self._grammar[intent]
                )
                if distance < best_distance:
                    best_distance = distance
                    best_meta = meta
                    best_intent = intent
                    if distance == 0:
                        break

        if best_intent is None:
            return None

        return GrammarBasedNluMatchResult(
            intent=best_intent, distance=best_distance, meta=best_meta
        )

    @classmethod
    def load(cls, path: str) -> "GrammarBasedNlu":
        import yaml

        with open(path, "r", encoding="utf-8") as fp:
            grammar = grammar_from_dict(yaml.full_load(fp))
            return GrammarBasedNlu(grammar)


def test():
    import yaml
    from ggbot.utils import benchmark

    grammar_data = load_yamls(
        "../common/common.yaml",
        "../common/datetime.yaml",
        "../common/numbers.yaml",
        "../common/money.yaml",
        "../common/intents.yaml",
        # Custom
        "../dota/grammar.yaml",
        "../dota/heroes.yaml",
        "../search/grammar.yaml",
    )

    grammar = grammar_from_dict(grammar_data)
    validate_grammar(grammar)

    nlu = GrammarBasedNlu(grammar=grammar)

    # for k, r in grammar.items():
    #   print(r)

    phrase = "@gg-bot что собрать на войде в харде против ключника"
    print(phrase)
    for i in range(3):  # Caching test
        with benchmark("match-ruleset"):
            match = nlu.match_any_intent(phrase)
    assert isinstance(match, GrammarBasedNluMatchResult)
    print("{}".format(match.distance))
    print(yaml.dump(match.meta, allow_unicode=True))


if __name__ == "__main__":
    test()
