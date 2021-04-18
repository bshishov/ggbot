from typing import List, Dict, Optional, Iterable, Union, Any, Mapping
from dataclasses import dataclass
import logging
import re

import yaml
from Stemmer import Stemmer
from tokema import (
    Rule,
    Query,
    IntQuery,
    FloatQuery,
    Resolver,
    ReferenceQuery,
    TerminalQuery,
    TextQuery,
    build_text_parsing_table,
    parse,
    ParseNode,
    Symbol
)
from jinja2 import Template, Environment
from jinja2.nativetypes import NativeEnvironment


from ggbot.text.base import NluBase, IntentMatchResultBase


__all__ = [
    'load_rules_from_yaml',
    'rules_from_grammar_dict',
    'TokemaNlu'
]


_logger = logging.getLogger(__name__)


class ExtendedRule(Rule):
    __slots__ = 'meta'

    def __init__(
            self,
            production: str,
            queries: List[Query],
            meta: Optional[Dict[str, Any]] = None
    ):
        super().__init__(production, tuple(queries))
        self.meta = meta


def build_meta_templates(jinja_env: Environment, meta: Dict[str, str]):
    meta_template = {}
    for k, v in meta.items():
        if isinstance(v, str):
            meta_template[k] = jinja_env.from_string(v)
        else:
            meta_template[k] = v
    return meta_template


@dataclass
class TokemaGrammar:
    rules: list[Rule]


def _parse_queries(raw: str) -> List[Query]:
    queries = []
    for arg in raw.split():
        arg = arg.strip()

        if len(arg) > 2 and arg.startswith('<') and arg.endswith('>'):
            queries.append(ReferenceQuery(arg[1:-1]))
        elif arg == '{int}':
            queries.append(IntQuery())
        elif arg == '{float}':
            queries.append(FloatQuery())
        else:
            queries.append(TextQuery(arg, case_sensitive=False))
    return queries


def _parse_rule(
        production: str,
        raw_queries: str,
        meta: Optional[Dict[str, str]] = None,
        jinja_env: Optional[Environment] = None
) -> ExtendedRule:
    if jinja_env and meta:
        meta = build_meta_templates(jinja_env, meta)

    return ExtendedRule(
        production=production,
        queries=_parse_queries(raw_queries),
        meta=meta
    )


def _parse_rules(
        production: str,
        rules_data: List[Union[str, Dict[str, Any]]],
        jinja_env: Optional[Environment] = None
) -> List[ExtendedRule]:
    rules = []

    for rule_data in rules_data:
        if isinstance(rule_data, str):
            rule = _parse_rule(
                production=production,
                raw_queries=rule_data
            )
            rules.append(rule)
        elif isinstance(rule_data, dict):
            for k, v in rule_data.items():
                rule = _parse_rule(
                    production=production,
                    raw_queries=k,
                    meta=v,
                    jinja_env=jinja_env
                )
                rules.append(rule)
    return rules


def rules_from_grammar_dict(data: Mapping[str, List], j2_env: Environment) -> List[ExtendedRule]:
    rules = []
    for production, rules_data in data.items():
        production_rules = _parse_rules(
            production=production,
            rules_data=rules_data,
            jinja_env=j2_env
        )
        rules.extend(production_rules)
    return rules


def load_rules_from_yaml(filename: str, j2_env: Environment) -> List[ExtendedRule]:
    with open(filename, 'r', encoding='utf-8') as f:
        data = yaml.full_load(f)
        return rules_from_grammar_dict(data, j2_env)


class StemmerResolver(Resolver):
    """Additional resolver that will try to use stemmed text for reverse index lookups"""

    def __init__(self, stemmer: Stemmer):
        self.index = {}
        self.stemmer = stemmer

    def add_query(self, query: TerminalQuery, doc):
        if isinstance(query, TextQuery) and len(query.text) >= 3:
            s = self.stemmer.stemWord(query.text.lower())
            self.index[s] = doc

    def resolve(self, token):
        if isinstance(token, str):
            s = self.stemmer.stemWord(token).lower()
            return self.index.get(s)
        return None


def create_table_for_production(
        production: str,
        rules: List[ExtendedRule],
        additional_resolvers: List[Resolver]
):
    root_rule = _parse_rule('ROOT', f'<{production}> .')
    return build_text_parsing_table(
        rules=[root_rule, *rules],
        additional_resolvers=additional_resolvers
    )


def _render_obj_recursive(obj, **params):
    if isinstance(obj, Template):
        return obj.render(**params)
    elif isinstance(obj, list):
        return [_render_obj_recursive(o, **params) for o in obj]
    elif isinstance(obj, tuple):
        return tuple(_render_obj_recursive(o, **params) for o in obj)
    elif isinstance(obj, dict):
        return {k: _render_obj_recursive(v, **params) for k, v in obj.items()}
    return obj


def render_ast(node: ParseNode) -> Dict:
    args_params = []

    for child in node:
        if isinstance(child, ParseNode):
            args_params.append(render_ast(child))
        elif isinstance(child, Symbol):
            args_params.append({
                'value': child.value,
                'meta': child.meta,
                'position': child.position
            })

    params = {
        'args': args_params,
        'rule': node.rule.production
    }
    if isinstance(node.rule, ExtendedRule):
        if node.rule.meta:
            params.update(_render_obj_recursive(node.rule.meta, **params))
    return params


@dataclass
class TokemaMatchResult(IntentMatchResultBase):
    slots: Dict[str, Any]
    intent: str

    def get_confidence(self) -> float:
        return 1.0

    def get_intent(self) -> str:
        return self.intent

    def get_slot_value(self, slot_name: str) -> Optional[str]:
        return self.slots.get(slot_name)

    def get_all_slots(self) -> dict[str, str]:
        return self.slots


# Tokenization regex
TOKEN_PATTERN = re.compile(
    r'[^\W\d_]+|'   # any alphabetical and non-numeric
    r'\d+|'                                  # or digit
    r'[:";\'!@#$%^&*()<>?,./[\]{}\\|\-_+=]'  # or symbol
)


def tokenize(text: str):
    for match in TOKEN_PATTERN.finditer(text):
        yield match.group(0)


class TokemaNlu(NluBase):
    def __init__(self, rules: List[ExtendedRule], tokenizer_fn=tokenize):
        self.rules = rules
        self.intents = []
        self.resolvers = [
            StemmerResolver(Stemmer('russian'))
        ]
        self.j2_env = NativeEnvironment()
        self.tokenizer_fn = tokenizer_fn

        for r in rules:
            if r.production.startswith('intent'):
                self.intents.append(r.production)

        self.intents = tuple(set(self.intents))

        self._parsing_tables = {}

    def _get_or_create_parsing_table(self, intents: Iterable[str]):
        intents = tuple(intents)
        table = self._parsing_tables.get(intents)

        if table is None:
            _logger.info(f'Creating table for intents {intents}')
            augmented_rules = []

            root_rule = _parse_rule(
                production='ROOT',
                raw_queries='<INTENT> .',
                meta={'intent': '{{ args[0].intent }}'},
                jinja_env=self.j2_env
            )
            augmented_rules.append(root_rule)

            for intent in intents:
                intent_rule = _parse_rule(
                    production='INTENT',
                    raw_queries=f'<{intent}>',
                    meta={'intent': intent}
                )
                augmented_rules.append(intent_rule)

            table = build_text_parsing_table(
                rules=[*augmented_rules, *self.rules],
                #verbose=True,
                additional_resolvers=self.resolvers
            )

            self._parsing_tables[intents] = table
            return table

        return table

    def _match(self, text, table) -> Optional[TokemaMatchResult]:
        input_tokens = [*self.tokenizer_fn(text), '.']

        results = parse(
            input_tokens=input_tokens,
            table=table,
            #verbose=True
        )

        if not results:
            return None

        for ast in reversed(results):
            root = ast[0]

            intent_name = root.rule.meta['intent']
            intent_ast = root[0]

            _logger.info(f'Matched intent {intent_name}: {intent_ast}')

            slots = render_ast(intent_ast)
            #pprint.pprint(slots)

            return TokemaMatchResult(slots=slots, intent=intent_name)

        return None

    def match_any_intent(self, text: str) -> Optional[TokemaMatchResult]:
        table = self._get_or_create_parsing_table(self.intents)
        return self._match(text, table)

    def match_intent_one_of(
            self,
            text: str,
            intents: Iterable[str]
    ) -> Optional[TokemaMatchResult]:
        table = self._get_or_create_parsing_table(intents)
        return self._match(text, table)


def _test():
    from tokema.utils import benchmark

    logging.basicConfig(level=logging.INFO)
    grammar_files = [
        '../common/common.yaml',
        '../common/datetime.yaml',
        '../common/intents.yaml',
        '../common/money.yaml',
        '../common/numbers.yaml',
        '../dota/grammar.yaml',
        '../dota/heroes.yaml',
        '../search/genres.yaml',
        '../search/grammar.yaml',
    ]

    jinja_env = NativeEnvironment()

    rules = []
    for filename in grammar_files:
        rules.extend(load_rules_from_yaml(filename, jinja_env))

    nlu = TokemaNlu(rules)

    test_phrases = [
        #'посоветуй плз кого лучше взять против инво в мид',
        #'тактические настольные инди картонки типа доты',
        #'игры типа доты',
        "найди игры на 5 к человек в жанре тактические настольные инди картонки типа доты"
    ]

    for phrase in test_phrases:
        #match = nlu.match_intent_one_of(phrase, ['intent-search-coop'])

        with benchmark(phrase):
            match = nlu.match_any_intent(phrase)


if __name__ == '__main__':
    _test()
