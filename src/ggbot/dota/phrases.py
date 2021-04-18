from typing import Optional
import random

from dataclasses import dataclass

from ggbot.fuzzy import *
from ggbot.assets import *
from ggbot.text.tokema_integration import TokemaNlu


__all__ = [
    'build_rules',
    'parse_rules',
    'PhraseGenerator'
]


def default_numeric_set(
        x_min: float,
        x_max: float,
):
    dist = x_max - x_min

    def d(x: float):
        return x_min + x * dist

    return {
        'zero': TriangularMf(-1, 0, 0.0001),
        'very low': TriangularMf(d(-1), d(0), d(0.25)),
        'low': TriangularMf(d(-1), d(0), d(0.5)),
        'avg': TriangularMf(d(0), d(0.3), d(1)),
        'high': TriangularMf(d(0.3), d(1), d(2))
    }


def build_rules(phrases: IndexedCollection[list], nlu, variables: list[Variable]):
    variables = {v.name: v for v in variables}

    phrase_rules = []
    for condition, phrase in phrases:
        condition = condition.strip()
        phrase = phrase.strip()

        if not condition or not phrase:
            continue

        match = nlu.match_intent_one_of(condition, ['statements'])
        if not match:
            print(f'Failed to parse: {condition}')
            continue

        match_rules = match.slots.get('rules')
        if not match_rules:
            print(f'No rules in match: {match}')
            continue

        operands = []
        for r in match_rules:
            var_name = r['var']
            value_name = r['value']

            if var_name == 'player':
                # Common python rule
                operands.append(EqualsValue(var_name, value_name))
            elif var_name == 'hero_id':
                operands.append(ValueIsOneOf(var_name, set(value_name)))
            else:
                # Linguistic
                v = variables[var_name]
                operands.append(Is(v, value_name))

        rule = And(*operands)
        print(phrase)
        print(condition)
        print(rule)
        print()
        phrase_rules.append((rule, phrase))
    return phrase_rules


def bool_var(name: str) -> Variable:
    return Variable(
        name,
        bounds=(0, 1),
        false=TriangularMf(-1, 0, 1),
        true=TriangularMf(0, 1, 2),
    )


def player_variables():
    players = [
        'shide',
        'bangodus',
        'varenick',
        'avokadro',
        'mrmerkone,'
        'choco boy'
    ]

    for p in players:
        yield bool_var(f'player_{p}')


def parse_rules(raw_phrases: IndexedCollection, nlu: TokemaNlu):
    variables = [
        Variable('kills', (0, 25), **default_numeric_set(0, 25)),
        Variable('deaths', (0, 20), **default_numeric_set(0, 20)),
        Variable('assists', (0, 25), **default_numeric_set(0, 25)),
        Variable('kills_per_min', (0, .5), **default_numeric_set(0, .5)),
        Variable('deaths_per_min', (0, .4), **default_numeric_set(0, .4)),
        Variable('assists_per_min', (0, .5), **default_numeric_set(0, .5)),
        Variable('ka_per_min', (0, 1), **default_numeric_set(0, 1)),
        Variable('kda', (0, 10), **default_numeric_set(0, 10)),
        Variable('gold_per_min', (0, 1000), **default_numeric_set(0, 1000)),
        Variable('xp_per_min', (0, 1000), **default_numeric_set(0, 1000)),
        Variable('hero_damage', (0, 50000), **default_numeric_set(0, 50000)),
        Variable('tower_damage', (0, 20000), **default_numeric_set(0, 20000)),
        Variable('hero_healing', (0, 10000), **default_numeric_set(0, 10000)),
        Variable('duration', (0, 80 * 60), **default_numeric_set(0, 80 * 60)),  # seconds
        Variable('last_hits', (0, 500), **default_numeric_set(0, 500)),
        Variable('result', (0, 1), lose=TriangularMf(-1, 0, 1), won=TriangularMf(0, 1, 2))
    ]
    return build_rules(raw_phrases, nlu, variables)


@dataclass
class PhraseGenerator:
    phrase_rules: list[tuple[ConditionStatement, str]]
    threshold: float = 0.1

    def generate_phrase(self, match: dict, player_name: str, hero_name: str) -> Optional[str]:
        is_radiant = match['player_slot'] < 128
        radiant_win = match['radiant_win']

        match['player'] = player_name.lower()

        if radiant_win:
            match['result'] = is_radiant
        else:
            match['result'] = not is_radiant

        ka = match['kills'] + match['assists']
        d = match['deaths']
        if d > 0:
            match['kda'] = ka / d
        else:
            match['kda'] = ka

        duration_minutes = match['duration'] / 60.0
        match['kills_per_min'] = match['kills'] / duration_minutes
        match['deaths_per_min'] = match['deaths'] / duration_minutes
        match['assists_per_min'] = match['assists'] / duration_minutes
        match['ka_per_min'] = (match['kills'] + match['assists']) / duration_minutes

        population = []
        #weights = []
        for condition, phrase in self.phrase_rules:
            phrase = phrase.format(name=player_name, hero=hero_name)
            res = condition.evaluate(**match)
            if res > self.threshold:
                print(f'{res:.2f}  {phrase}')

                #population.append(phrase)
                #weights.append(res)
                population.append((phrase, res))

        if not population:
            return None

        population = sorted(population, key=lambda _: _[1], reverse=True)
        population = population[:3]

        rnd = random.Random()
        rnd.seed(match['match_id'])
        p, res = rnd.choice(population)

        #weights = np.asarray(weights)
        #weights = weights / weights.sum()
        #p = np.random.choice(population, 1, p=weights)[0]
        print(f'Selected: {p}')
        return p
