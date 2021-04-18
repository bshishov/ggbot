from typing import Iterable, Optional
import pprint
import re
from dataclasses import dataclass

import aiohttp

from ggbot.context import BotContext, Context
from ggbot.component import BotComponent
from ggbot.dota.phrases import PhraseGenerator
from ggbot.assets import *
from ggbot.utils import local_time_cache


__all__ = [
    'Dota',
    'RequestOpenDotaAction',
    'CountMatchupsAction',
    'GeneratePhraseAction',
    'parse_dotabuff_id_from_message'
]


SKILL_BRACKETS = {
    '1': 'Normal',
    '2': 'High',
    '3': 'Very High'
}

OPENDOTA_API_URL = 'https://api.opendota.com/api/'


def skill_id_to_name(skill_id: str) -> str:
    return SKILL_BRACKETS[str(skill_id)]


def player_slot_is_radiant(slot: int) -> bool:
    return 0 <= slot <= 127


def player_slot_is_dire(slot: int) -> bool:
    return 128 <= slot <= 255


@dataclass
class HeroesCollection(IndexedCollection[dict]):
    asset: JsonAsset

    @property
    @local_time_cache(5 * 60)
    def data(self):
        data = self.asset.get_data()
        return {h['id']: h for h in data}

    def iter_items(self) -> Iterable[dict]:
        yield from self.data.values()

    def get_item_by_index(self, index) -> Optional[dict]:
        return self.data.get(index)

    def __len__(self):
        return len(self.data)


class Dota(BotComponent):
    def __init__(self, opendota_api_key: str, phrase_generator: PhraseGenerator):
        self.api_key = opendota_api_key
        self.heroes = HeroesCollection(
            JsonAsset(Cached(UrlSource(f'{OPENDOTA_API_URL}heroes')))
        )
        self.phrase_generator = phrase_generator

    def hero_id_to_name(self, id: str):
        return self.heroes.get_item_by_index(id)['name']

    def hero_id_to_localized_name(self, id: str):
        return self.heroes.get_item_by_index(id)['localized_name']

    async def init(self, context: BotContext):
        context.template_env.filters['dota_hero_id_to_name'] = self.hero_id_to_name
        context.template_env.filters['dota_hero_id_to_localized_name'] = self.hero_id_to_localized_name
        context.template_env.filters['dota_skill_id_to_name'] = skill_id_to_name
        context.template_env.filters['dota_slot_is_radiant'] = player_slot_is_radiant
        context.template_env.filters['dota_slot_is_dire'] = player_slot_is_dire


@dataclass
class RequestOpenDotaAction:
    api_key: str
    query: str
    require_steam_id: bool = True

    async def __call__(self, context: Context) -> bool:
        query = context.render_template(self.query)
        async with aiohttp.ClientSession() as session:
            response = await session.get(f'{OPENDOTA_API_URL}{query}', params={
                'api_key': self.api_key,
            })
            print(response.url)
            result = await response.json()
            pprint.pprint(result)
            context.local['result'] = result

            if response.status == 200:
                return True
        return False


@dataclass
class CountMatchupsAction:

    async def __call__(self, context: Context) -> bool:
        result = context.local['result']
        total_games_played = 0

        for item in result:
            item['winrate'] = item['wins'] / item['games_played']
            total_games_played += item['games_played']

        avg_games_played = total_games_played / len(result)
        result = (x for x in result if x['games_played'] >= avg_games_played)

        result = list(sorted(result, key=lambda x: x['winrate'], reverse=True))
        context.local['result'] = result
        return True


@dataclass
class GeneratePhraseAction:
    phrase_generator: PhraseGenerator

    async def __call__(self, context: Context) -> bool:
        match = context.local.get('result')
        if not match:
            return False

        phrase = self.phrase_generator.generate_phrase(
            match=match[0],
            player_name=context.author.member.display_name,
            hero_name=context.render_template('{{ result[0].hero_id|dota_hero_id_to_localized_name }}')
        )
        context.local['phrase'] = phrase
        return True


DOTA_ID_REGEXES = (
    re.compile(r'dotabuff.com/players/(\d+)'),
    re.compile(r'opendota.com/players/(\d+)'),
    re.compile(r'(\d+)'),
)


def _parse_dotabuff_id(message: str) -> Optional[str]:
    for r in DOTA_ID_REGEXES:
        match = r.search(message)
        if match:
            return match.group(1)
    return None


def parse_dotabuff_id_from_message(target_variable: str):
    async def _fn(context: Context):
        dotabuff_id = _parse_dotabuff_id(str(context.message.content))

        if not dotabuff_id:
            return False

        context.local[target_variable] = dotabuff_id
        return True
    return _fn
