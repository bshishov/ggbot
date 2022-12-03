from typing import Iterable, Optional, List, Dict
import re
import logging
import time
import aiohttp
import ctor

from attr import dataclass

from ggbot.context import BotContext, Context, IVariable, IExpression
from ggbot.component import BotComponent
from ggbot.assets import *
from ggbot.utils import local_time_cache
from ggbot.opendota import OpenDotaApi, DotaMatch, Player, PlayerRanking, HeroMatchup
from ggbot.dota.phrases import PhraseGenerator
from ggbot.dota.medals import *
from ggbot.dota.predicates import find_player_by_steam_id, Just
from ggbot.bttypes import *


__all__ = [
    "DOTA_MATCH",
    "DOTA_MATCH_PLAYER",
    "DOTA_PLAYER_RANKING",
    "DOTA_HERO_MATCHUP",
    "DOTA_PLAYER_MEDAL",
    "OPENDOTA_API_URL",
    "Dota",
    "RequestOpenDotaAction",
    "RequestPlayerRankings",
    "RequestTopHeroMatchups",
    "CountMatchupsAction",
    "GeneratePhraseForPlayer",
    "parse_steam_id_from_message",
    "RequestMatch",
    "FetchLastMatchId",
    "CheckMatchIsParsed",
    "RequestParseMatch",
    "CalculateMedals",
    "AssignPlayerMedals",
    "FormattedMedals",
    "MedalFromId",
    "HeroName",
    "MatchPlayer",
    "MatchDurationMinutes",
    "PlayerHeroId",
    "MatchPlayerResultString",
    "PlayerHeroIconUrl",
    "CheckSecondsSinceRecentMatchGreaterThan",
]

_logger = logging.getLogger(__name__)


SKILL_BRACKETS = {"1": "Normal", "2": "High", "3": "Very High"}

OPENDOTA_API_URL = "https://api.opendota.com/api/"
DOTA_MATCH = make_struct_from_python_type(DotaMatch)
DOTA_MATCH_PLAYER = make_struct_from_python_type(Player)
DOTA_PLAYER_RANKING = make_struct_from_python_type(PlayerRanking)
DOTA_HERO_MATCHUP = make_struct_from_python_type(HeroMatchup)
DOTA_PLAYER_MEDAL = make_struct_from_python_type(PlayerMedal)


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
        return {h["id"]: h for h in data}

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
            JsonAsset(Cached(UrlSource(f"{OPENDOTA_API_URL}heroes")))
        )
        self.phrase_generator = phrase_generator

    def hero_id_to_name(self, id: int):
        return self.heroes.get_item_by_index(id)["name"]

    def hero_id_to_localized_name(self, id: int):
        return self.heroes.get_item_by_index(id)["localized_name"]

    async def init(self, context: BotContext):
        context.template_env.filters["dota_hero_id_to_name"] = self.hero_id_to_name
        context.template_env.filters[
            "dota_hero_id_to_localized_name"
        ] = self.hero_id_to_localized_name
        context.template_env.filters["dota_skill_id_to_name"] = skill_id_to_name
        context.template_env.filters["dota_slot_is_radiant"] = player_slot_is_radiant
        context.template_env.filters["dota_slot_is_dire"] = player_slot_is_dire


@dataclass
class RequestOpenDotaAction:
    api_key: str
    query: IExpression[str]

    def __attrs_post_init__(self):
        assert STRING.can_accept(self.query.get_return_type())

    async def __call__(self, context: Context) -> bool:
        query = self.query.evaluate(context)
        async with aiohttp.ClientSession() as session:
            response = await session.get(
                f"{OPENDOTA_API_URL}{query}",
                params={
                    "api_key": self.api_key,
                },
            )
            result = await response.json()
            _logger.debug(f"Received data url={response.url} response={result}")
            context.local["result"] = result

            if response.status == 200:
                return True
        return False


@dataclass
class CountMatchupsAction:
    async def __call__(self, context: Context) -> bool:
        result = context.local["result"]
        total_games_played = 0

        for item in result:
            item["winrate"] = item["wins"] / item["games_played"]
            total_games_played += item["games_played"]

        avg_games_played = total_games_played / len(result)
        result = (x for x in result if x["games_played"] >= avg_games_played)

        result = list(sorted(result, key=lambda x: x["winrate"], reverse=True))
        context.local["result"] = result
        return True


@dataclass
class GeneratePhraseForPlayer:
    phrase_generator: PhraseGenerator
    match_player: IExpression[Player]
    result: IVariable
    dota: Dota

    def __attrs_post_init__(self):
        assert DOTA_MATCH_PLAYER.can_accept(self.match_player.get_return_type())
        assert self.result.get_return_type().can_accept(STRING)

    async def __call__(self, context: Context) -> bool:
        player = self.match_player.evaluate(context)
        hero_name = self.dota.hero_id_to_localized_name(player.hero_id)
        match_data = ctor.dump(player)  # backwards compatibility

        phrase = self.phrase_generator.generate_phrase(
            match=match_data,
            player_name=context.author.member.display_name,
            hero_name=hero_name,
        )
        context.set_variable(self.result, phrase)
        return True


STEAM_ID_REGEXES = (
    re.compile(r"dotabuff.com/players/(\d+)"),
    re.compile(r"opendota.com/players/(\d+)"),
    re.compile(r"(\d+)"),
)


def _parse_steam_id(message: str) -> Optional[str]:
    for r in STEAM_ID_REGEXES:
        match = r.search(message)
        if match:
            return match.group(1)
    return None


def parse_steam_id_from_message(target_variable: IVariable[int]):
    assert target_variable.get_return_type().can_accept(NUMBER)

    async def _fn(context: Context):
        steam_id = _parse_steam_id(str(context.message.content))

        if not steam_id:
            return False

        try:
            steam_id = int(steam_id)
        except ValueError:
            return False

        context.set_variable(target_variable, steam_id)
        return True

    return _fn


@dataclass
class FetchLastMatchId:
    api: OpenDotaApi
    steam_id: IExpression[int]
    result: IVariable[int]

    def __attrs_post_init__(self):
        assert NUMBER.can_accept(self.steam_id.get_return_type())
        assert self.result.get_return_type().can_accept(NUMBER)

    async def __call__(self, context: Context) -> bool:
        steam_id = self.steam_id.evaluate(context)
        if not steam_id:
            return False

        matches = await self.api.get_player_recent_matches(steam_id)
        if not matches:
            return False

        last_match = matches[0]
        context.set_variable(self.result, last_match.match_id)
        return True


@dataclass
class RequestPlayerRankings:
    api: OpenDotaApi
    steam_id: IExpression[int]
    result: IVariable[List[PlayerRanking]]
    limit: int

    def __attrs_post_init__(self):
        assert NUMBER.can_accept(self.steam_id.get_return_type())
        assert self.result.get_return_type().can_accept(ARRAY(DOTA_PLAYER_RANKING))

    async def __call__(self, context: Context) -> bool:
        steam_id = self.steam_id.evaluate(context)
        rankings = await self.api.get_player_rankings(steam_id)
        rankings = sorted(
            rankings, key=lambda ranking: ranking.percent_rank, reverse=False
        )
        context.set_variable(self.result, rankings[: self.limit])
        return True


def _win_rate(m: HeroMatchup) -> float:
    return m.wins / m.games_played


@dataclass
class RequestTopHeroMatchups:
    api: OpenDotaApi
    hero_id: IExpression[int]
    result: IVariable[List[HeroMatchup]]
    limit: int

    def __attrs_post_init__(self):
        assert NUMBER.can_accept(self.hero_id.get_return_type())
        assert self.result.get_return_type().can_accept(ARRAY(DOTA_HERO_MATCHUP))

    async def __call__(self, context: Context) -> bool:
        hero_id = self.hero_id.evaluate(context)
        result = await self.api.get_hero_matchups(hero_id)

        total_games_played = 0
        for matchup in result:
            total_games_played += matchup.games_played

        avg_games_played = total_games_played / len(result)
        result = (x for x in result if x.games_played >= avg_games_played)
        result = list(sorted(result, key=_win_rate, reverse=True))[: self.limit]
        context.set_variable(self.result, result)
        return True


@dataclass
class CheckSecondsSinceRecentMatchGreaterThan:
    api: OpenDotaApi
    steam_id: IExpression[int]
    seconds: IExpression[int]

    def __attrs_post_init__(self):
        assert NUMBER.can_accept(self.steam_id.get_return_type())
        assert NUMBER.can_accept(self.seconds.get_return_type())

    async def __call__(self, context: Context) -> bool:
        steam_id = self.steam_id.evaluate(context)
        if not steam_id:
            return False

        matches = await self.api.get_player_recent_matches(steam_id)
        if matches is None:
            return False

        if len(matches) == 0:
            return True

        last_match = matches[0]
        end_time = last_match.start_time + last_match.duration
        threshold = self.seconds.evaluate(context)
        return time.time() - end_time > threshold


@dataclass
class RequestMatch:
    api: OpenDotaApi
    match_id: IExpression[int]
    result: IVariable[DotaMatch]
    use_cached_if_younger_than: float = 24 * 60 * 60

    def __attrs_post_init__(self):
        assert NUMBER.can_accept(self.match_id.get_return_type())
        assert self.result.get_return_type().can_accept(DOTA_MATCH)

    async def __call__(self, context: Context) -> bool:
        match_id = self.match_id.evaluate(context)
        if not match_id:
            return False

        match = await self.api.get_match(
            match_id, cache_lifetime=self.use_cached_if_younger_than
        )
        context.set_variable(self.result, match)
        return True


@dataclass
class CheckMatchIsParsed:
    match: IExpression[DotaMatch]

    def __attrs_post_init__(self):
        assert DOTA_MATCH.can_accept(self.match.get_return_type())

    async def __call__(self, context: Context) -> bool:
        match = self.match.evaluate(context)

        if match.radiant_gold_adv is None:
            # Missing field that is available only after match is parsed completely
            return False

        return True


@dataclass
class RequestParseMatch:
    api: OpenDotaApi
    match_id: IExpression[int]
    result_job_id: Optional[IVariable[int]] = None

    def __attrs_post_init__(self):
        assert NUMBER.can_accept(self.match_id.get_return_type())
        if self.result_job_id:
            assert self.result_job_id.get_return_type().can_accept(NUMBER)

    async def __call__(self, context: Context) -> bool:
        match_id = self.match_id.evaluate(context)
        job = await self.api.request_match_parse(match_id)

        if self.result_job_id is not None:
            context.set_variable(self.result_job_id, job.job.jobId)
        return True


@dataclass
class CalculateMedals:
    match: IExpression[DotaMatch]
    steam_id: IExpression[int]
    result: IVariable[List[PlayerMedal]]

    def __attrs_post_init__(self):
        assert NUMBER.can_accept(self.steam_id.get_return_type())
        assert DOTA_MATCH.can_accept(self.match.get_return_type())
        assert self.result.get_return_type().can_accept(ARRAY(DOTA_PLAYER_MEDAL))

    async def __call__(self, context: Context) -> bool:
        steam_id = self.steam_id.evaluate(context)
        match = self.match.evaluate(context)
        player = find_player_by_steam_id(match, steam_id)

        if not player:
            # No player in that match
            return False

        medals = []
        for medal in PLAYER_MEDALS:
            if medal.predicate.check(match, player):
                medals.append(medal)

        context.set_variable(self.result, medals)
        return True


@dataclass
class AssignPlayerMedals:
    match_medals: IExpression[List[PlayerMedal]]
    match_id: IExpression[int]
    player_medal_matches: IVariable[List[int]]
    player_medals: IVariable[Dict[str, int]]

    def __attrs_post_init__(self):
        assert ARRAY(DOTA_PLAYER_MEDAL).can_accept(self.match_medals.get_return_type())
        assert NUMBER.can_accept(self.match_id.get_return_type())
        assert ARRAY(NUMBER).can_accept(self.player_medal_matches.get_return_type())

    async def __call__(self, context: Context) -> bool:
        match_id = self.match_id.evaluate(context)
        medal_matches = self.player_medal_matches.evaluate(context)
        if match_id in medal_matches:
            # Medal was already assigned
            return False

        match_medals = self.match_medals.evaluate(context)
        player_medals = self.player_medals.evaluate(context)

        for medal in match_medals:
            player_medals[medal.id] = player_medals.get(medal.id, 0) + 1

        medal_matches.append(match_id)
        context.set_variable(self.player_medal_matches, medal_matches)
        context.set_variable(self.player_medals, player_medals)
        return True


@dataclass
class FormattedMedals(IExpression[str]):
    medals_ids: IExpression[List[PlayerMedal]]

    def __attrs_post_init__(self):
        assert ARRAY(DOTA_PLAYER_MEDAL).can_accept(self.medals_ids.get_return_type())

    def evaluate(self, context: Context) -> str:
        result = ""
        for medal in self.medals_ids.evaluate(context):
            result += f"{medal.icon} **{medal.name}** *{medal.description}*\n"
        return result

    def get_return_type(self) -> IType:
        return STRING


@dataclass
class MedalFromId(IExpression[PlayerMedal]):
    medal_id: IExpression[str]

    def __attrs_post_init__(self):
        assert STRING.can_accept(self.medal_id.get_return_type())

    def evaluate(self, context: Context) -> PlayerMedal:
        medal_id = self.medal_id.evaluate(context)
        medal = PLAYER_MEDALS_DICT.get(medal_id)
        if medal:
            return medal
        return PlayerMedal(id="non-existent", name="non-existent", predicate=Just(True))

    def get_return_type(self) -> IType:
        return DOTA_PLAYER_MEDAL


@dataclass
class HeroName(IExpression[str]):
    hero_id: IExpression[int]
    dota: Dota

    def __attrs_post_init__(self):
        assert NUMBER.can_accept(self.hero_id.get_return_type())

    def evaluate(self, context: Context) -> str:
        hero_id = self.hero_id.evaluate(context)
        return self.dota.hero_id_to_localized_name(hero_id)

    def get_return_type(self) -> IType:
        return STRING


@dataclass
class MatchPlayer(IExpression[Optional[Player]]):
    match: IExpression[DotaMatch]
    steam_id: IExpression[int]

    def __attrs_post_init__(self):
        assert DOTA_MATCH.can_accept(self.match.get_return_type())
        assert NUMBER.can_accept(self.steam_id.get_return_type())

    def evaluate(self, context: Context) -> Optional[Player]:
        match = self.match.evaluate(context)
        steam_id = self.steam_id.evaluate(context)
        player = find_player_by_steam_id(match, steam_id)
        return player

    def get_return_type(self) -> IType:
        return ONEOF(NULL_TYPE, DOTA_MATCH_PLAYER)


@dataclass
class PlayerHeroId(IExpression[int]):
    player: IExpression[Player]

    def __attrs_post_init__(self):
        assert DOTA_MATCH_PLAYER.can_accept(self.player.get_return_type())

    def evaluate(self, context: Context) -> int:
        player = self.player.evaluate(context)
        return player.hero_id

    def get_return_type(self) -> IType:
        return NUMBER


@dataclass
class MatchDurationMinutes(IExpression[int]):
    match: IExpression[DotaMatch]

    def __attrs_post_init__(self):
        assert DOTA_MATCH.can_accept(self.match.get_return_type())

    def evaluate(self, context: Context) -> int:
        match = self.match.evaluate(context)
        return round(match.duration / 60)

    def get_return_type(self) -> IType:
        return NUMBER


@dataclass
class MatchPlayerResultString(IExpression[str]):
    player: IExpression[Player]

    def __attrs_post_init__(self):
        assert DOTA_MATCH_PLAYER.can_accept(self.player.get_return_type())

    def evaluate(self, context: Context) -> str:
        player = self.player.evaluate(context)
        if player.isRadiant == player.radiant_win:
            return "Победа"
        return "Поражение"

    def get_return_type(self) -> IType:
        return STRING


@dataclass
class PlayerHeroIconUrl(IExpression[str]):
    player: IExpression[Player]
    dota: Dota

    def __attrs_post_init__(self):
        assert DOTA_MATCH_PLAYER.can_accept(self.player.get_return_type())

    def evaluate(self, context: Context) -> str:
        player = self.player.evaluate(context)
        hero_name = self.dota.hero_id_to_name(player.hero_id)[14:]
        return f"https://cdn.origin.steamstatic.com/apps/dota2/images/heroes/{hero_name}_icon.png"

    def get_return_type(self) -> IType:
        return STRING
