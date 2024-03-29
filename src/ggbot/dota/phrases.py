from typing import Optional, List
import random
import logging

from attr import dataclass, asdict

import ctor

from ggbot.fuzzy import *
from ggbot.assets import *
from ggbot.text.base import NluBase
from ggbot.opendota import Player


__all__ = ["build_rules", "parse_rules", "PhraseGenerator", "get_dota_variables"]

_logger = logging.getLogger(__name__)


def default_numeric_set(
    x_min: float,
    x_max: float,
):
    dist = x_max - x_min

    def d(x: float):
        return x_min + x * dist

    return {
        "zero": TriangularMf(-1, 0, 0.0001),
        "very low": TriangularMf(d(-1), d(0), d(0.25)),
        "low": TriangularMf(d(-1), d(0), d(0.5)),
        "avg": TriangularMf(d(0), d(0.3), d(1)),
        "high": TriangularMf(d(0.3), d(1), d(2)),
    }


@dataclass
class PhraseRule:
    condition: And
    phrase_template: str
    weight: float


def build_rules(
    phrases: IndexedCollection[list], nlu: NluBase, variables: List[Variable]
) -> List[PhraseRule]:
    variables_dict = {v.name: v for v in variables}

    phrase_rules = []
    for condition, weight, phrase in phrases:
        condition = condition.strip()
        phrase = phrase.strip()
        weight = float(weight.replace(",", "."))

        if not condition or not phrase:
            continue

        match = nlu.match_intent_one_of(condition, ["statements"])
        if not match:
            _logger.warning(f"Failed to parse: {condition}")
            continue

        match_rules = match.get_slot_value("rules")
        if not match_rules:
            _logger.warning(f"No rules in match: {match}")
            continue

        operands = []
        for r in match_rules:
            var_name = r["var"]
            value_name = r["value"]

            if var_name == "player":
                # Common python rule
                operands.append(EqualsValue(var_name, value_name))
            elif var_name == "hero_id":
                operands.append(ValueIsOneOf(var_name, set(value_name)))
            else:
                # Linguistic
                v = variables_dict[var_name]
                operands.append(Is(v, value_name))

        rule_condition = And(*operands)
        _logger.debug(phrase)
        _logger.debug(condition)
        _logger.debug(rule_condition)

        phrase_rule = PhraseRule(
            condition=rule_condition,
            phrase_template=phrase,
            weight=weight
            + 0.5 * len(operands),  # Longer the AND statement -> higher the weight
        )

        phrase_rules.append(phrase_rule)
    return phrase_rules


def get_dota_variables():
    return [
        Variable("kills", (0, 25), **default_numeric_set(0, 25)),
        Variable("deaths", (0, 20), **default_numeric_set(0, 20)),
        Variable("assists", (0, 25), **default_numeric_set(0, 25)),
        Variable("kills_per_min", (0, 0.5), **default_numeric_set(0, 0.5)),
        Variable("deaths_per_min", (0, 0.4), **default_numeric_set(0, 0.4)),
        Variable("assists_per_min", (0, 0.5), **default_numeric_set(0, 0.5)),
        Variable("ka_per_min", (0, 1), **default_numeric_set(0, 1)),
        Variable("kda", (0, 10), **default_numeric_set(0, 10)),
        Variable("gold_per_min", (0, 1000), **default_numeric_set(0, 1000)),
        Variable("xp_per_min", (0, 1000), **default_numeric_set(0, 1000)),
        Variable("hero_damage", (0, 50000), **default_numeric_set(0, 50000)),
        Variable("tower_damage", (0, 20000), **default_numeric_set(0, 20000)),
        Variable("hero_healing", (0, 10000), **default_numeric_set(0, 10000)),
        Variable(
            "duration", (0, 80 * 60), **default_numeric_set(0, 80 * 60)
        ),  # seconds
        Variable("last_hits", (0, 500), **default_numeric_set(0, 500)),
        Variable(
            "result", (0, 1), lose=TriangularMf(-1, 0, 1), won=TriangularMf(0, 1, 2)
        ),
    ]


def parse_rules(raw_phrases: IndexedCollection, nlu: NluBase) -> List[PhraseRule]:
    variables = get_dota_variables()
    return build_rules(raw_phrases, nlu, variables)


_CTX = ctor.JsonSerializationContext()
_PLAYER_CONVERTER = _CTX.get_converter(Player)


@dataclass
class PhraseGenerator:
    phrase_rules: List[PhraseRule]
    threshold: float = 0.1

    def generate_phrase(
        self, match_id: int, player: Player, player_name: str, hero_name: str
    ) -> Optional[str]:
        is_radiant = player.player_slot < 128
        radiant_win = player.radiant_win is True
        context = asdict(player)

        context["player"] = player_name.lower()

        if radiant_win:
            context["result"] = is_radiant
        else:
            context["result"] = not is_radiant

        k = context.get("kills", 0)
        a = context.get("assists", 0)
        d = context.get("deaths", 0)
        ka = k + a

        if d > 0:
            context["kda"] = ka / d
        else:
            context["kda"] = ka

        duration_minutes = context.get("duration", 0) / 60.0
        context["kills_per_min"] = k / duration_minutes
        context["deaths_per_min"] = d / duration_minutes
        context["assists_per_min"] = a / duration_minutes
        context["ka_per_min"] = (k + a) / duration_minutes

        population = []
        for phrase_rule in self.phrase_rules:
            res = phrase_rule.condition.evaluate(**context) * phrase_rule.weight

            if res > self.threshold:
                phrase = phrase_rule.phrase_template.format(
                    name=player_name, hero=hero_name
                )
                _logger.debug(f"{res:.2f}  {phrase}")
                population.append((phrase, res))

        if not population:
            return None

        population = sorted(population, key=lambda _: _[1], reverse=True)
        population = population[:3]

        rnd = random.Random()
        rnd.seed(match_id)
        p, res = rnd.choice(population)

        _logger.debug(f"Selected: {p}")
        return p
