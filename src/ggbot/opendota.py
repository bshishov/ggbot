import typing
from typing import Union, Literal, Optional
import aiohttp

from attr import dataclass, attrib
import ctor

from ggbot.utils import get_url_json_with_file_cache


__all__ = [
    "DotaMatch",
    "FirstBloodObjective",
    "PlayerRecentMatch",
    "Player",
    "PlayerRanking",
    "HeroMatchup",
    "DotaItem",
    "DotaItemAttrib",
    "get_items",
    "get_item_ids",
    "OpenDotaApi",
]


OPEN_DOTA_API_URL = "https://api.opendota.com/api"
StrOrInt = Union[str, int]


@dataclass(slots=True, frozen=True)
class ChatEvent:
    time: Optional[int] = None
    type: Optional[str] = None
    key: Optional[str] = None
    slot: Optional[int] = None
    player_slot: Optional[int] = None


@dataclass(slots=True, frozen=True)
class DraftTiming:
    order: int
    pick: bool
    active_team: int
    hero_id: int
    player_slot: Optional[int]
    extra_time: int
    total_time_taken: int


class BaseObjective(typing.Protocol):
    time: int
    type: str


@dataclass(slots=True, frozen=True)
class FirstBloodObjective(BaseObjective):
    time: int
    type: Literal["CHAT_MESSAGE_FIRSTBLOOD"]
    slot: int
    key: int
    player_slot: int


@dataclass(slots=True, frozen=True)
class CourierLostObjective(BaseObjective):
    time: int
    type: Literal["CHAT_MESSAGE_COURIER_LOST"]
    team: int


@dataclass(slots=True, frozen=True)
class BuildingKillObjective(BaseObjective):
    time: int
    type: Literal["building_kill"]
    unit: str
    key: str
    slot: Optional[int] = None
    player_slot: Optional[int] = None


@dataclass(slots=True, frozen=True)
class RoshanKillObjective(BaseObjective):
    time: int
    type: Literal["CHAT_MESSAGE_ROSHAN_KILL"]
    team: int


@dataclass(slots=True, frozen=True)
class AegisObjective(BaseObjective):
    time: int
    type: Literal["CHAT_MESSAGE_AEGIS"]
    slot: int
    player_slot: int


@dataclass(slots=True, frozen=True)
class AegisStolenObjective(BaseObjective):
    time: int
    type: Literal["CHAT_MESSAGE_AEGIS_STOLEN"]
    slot: int
    player_slot: int


OneOfObjectives = Union[
    FirstBloodObjective,
    CourierLostObjective,
    BuildingKillObjective,
    RoshanKillObjective,
    AegisObjective,
    AegisStolenObjective,
]


@dataclass(slots=True, frozen=True)
class PickBan:
    is_pick: bool
    hero_id: int
    team: int
    order: int


@dataclass(slots=True, frozen=True, repr=False)
class TeamFightPlayer:
    deaths_pos: dict[str, dict[str, int]]
    ability_uses: dict[str, int]
    ability_targets: dict[str, dict[str, int]]
    item_uses: dict[str, int]
    killed: dict[str, int]
    deaths: int
    buybacks: int
    damage: int
    healing: int
    gold_delta: int
    xp_delta: int
    xp_start: Optional[int] = None
    xp_end: Optional[int] = None


@dataclass(slots=True, frozen=True, repr=False)
class TeamFight:
    start: Optional[int] = None
    end: Optional[int] = None
    last_death: Optional[int] = None
    deaths: Optional[int] = None
    players: Optional[list[TeamFightPlayer]] = None


@dataclass(slots=True, frozen=True)
class PlayerBuybackEvent:
    time: Optional[int] = None
    slot: Optional[int] = None
    type: Optional[Literal["buyback_log"]] = None
    player_slot: Optional[int] = None


@dataclass(slots=True, frozen=True)
class BenchmarkValue:
    raw: Optional[float] = None
    pct: Optional[float] = None


@dataclass(slots=True, frozen=True)
class PermanentBuffState:
    permanent_buff: Optional[int] = None
    stack_count: Optional[int] = None


@dataclass(slots=True, frozen=True)
class RunePickupEvent:
    time: Optional[int] = None
    key: Optional[int] = None


# https://docs.opendota.com/#tag/matches/operation/get_matches_by_match_id
@dataclass(slots=True, frozen=True, repr=False)
class Player:
    hero_id: int
    player_slot: int
    assists: Optional[int] = None
    deaths: Optional[int] = None
    denies: Optional[int] = None
    gold: Optional[int] = None
    gold_per_min: Optional[int] = None
    gold_spent: Optional[int] = None
    hero_damage: int = 0
    hero_healing: int = 0
    item_0: Optional[int] = None
    item_1: Optional[int] = None
    item_2: Optional[int] = None
    item_3: Optional[int] = None
    item_4: Optional[int] = None
    item_5: Optional[int] = None
    item_neutral: Optional[int] = None
    kills: Optional[int] = None
    last_hits: Optional[int] = None
    leaver_status: Optional[int] = None
    level: Optional[int] = None
    tower_damage: int = 0
    courier_kills: int = 0
    xp_per_min: Optional[int] = None
    radiant_win: Optional[bool] = None
    start_time: Optional[int] = None
    duration: Optional[int] = None
    cluster: Optional[int] = None
    lobby_type: Optional[int] = None
    game_mode: Optional[int] = None
    patch: Optional[int] = None
    isRadiant: Optional[bool] = None
    win: Optional[int] = None
    lose: Optional[int] = None
    total_gold: Optional[int] = None
    total_xp: Optional[int] = None
    abandons: Optional[int] = None
    rank_tier: Optional[int] = None
    account_id: Optional[int] = None
    camps_stacked: Optional[int] = None
    creeps_stacked: Optional[int] = None
    damage: Optional[dict[str, int]] = None
    damage_taken: Optional[dict[str, int]] = None
    dn_t: Optional[list[int]] = None
    firstblood_claimed: Optional[int] = None
    net_worth: Optional[int] = None
    obs_placed: Optional[int] = None
    pred_vict: Optional[bool] = None
    randomed: Optional[bool] = None
    roshans_killed: Optional[int] = None
    rune_pickups: Optional[int] = None
    sen_placed: Optional[int] = None
    stuns: Optional[float] = None
    towers_killed: Optional[int] = None
    observer_uses: Optional[int] = None
    sentry_uses: Optional[int] = None
    item_win: Optional[dict[str, int]] = None
    item_usage: Optional[dict[str, int]] = None
    actions_per_min: Optional[int] = None
    life_state_dead: Optional[int] = None
    neutral_kills: Optional[int] = None
    kills_per_min: Optional[float] = None
    personaname: Optional[str] = None
    region: Optional[int] = None
    purchase_ward_observer: Optional[int] = None
    purchase_ward_sentry: Optional[int] = None
    purchase_tpscroll: Optional[int] = None
    pings: Optional[int] = None
    teamfight_participation: Optional[float] = None
    party_id: Optional[int] = None
    item_uses: Optional[dict[str, int]] = None
    first_purchase_time: Optional[dict[str, int]] = None
    lh_t: Optional[list[int]] = None
    permanent_buffs: Optional[list[PermanentBuffState]] = None
    runes: Optional[dict[str, int]] = None
    buyback_count: Optional[int] = None


@dataclass(slots=True, frozen=True, repr=False)
class DotaMatch:
    match_id: int
    start_time: int
    game_mode: int
    duration: int
    barracks_status_dire: Optional[int] = None
    barracks_status_radiant: Optional[int] = None
    cluster: Optional[int] = None
    dire_score: Optional[int] = None
    engine: Optional[int] = None
    first_blood_time: Optional[int] = None
    human_players: Optional[int] = None
    leagueid: Optional[int] = None
    lobby_type: Optional[int] = None
    match_seq_num: Optional[int] = None
    radiant_score: Optional[int] = None
    radiant_win: Optional[bool] = None
    tower_status_dire: Optional[int] = None
    tower_status_radiant: Optional[int] = None
    players: list[Player] = attrib(factory=list)
    patch: Optional[int] = None
    skill: Optional[int] = None
    version: Optional[int] = None
    dire_team_id: Optional[int] = None
    radiant_gold_adv: Optional[list[int]] = None
    radiant_team_id: Optional[int] = None
    radiant_xp_adv: Optional[list[int]] = None
    chat: Optional[list[ChatEvent]] = None
    replay_url: Optional[str] = None
    region: Optional[int] = None
    throw: Optional[int] = None
    loss: Optional[int] = None
    replay_salt: Optional[int] = None
    series_id: Optional[int] = None
    series_type: Optional[int] = None
    objectives: Optional[list[OneOfObjectives]] = None


@dataclass(slots=True, frozen=True)
class PlayerRecentMatch:
    match_id: int
    player_slot: int
    radiant_win: bool
    duration: int
    game_mode: int
    lobby_type: int
    hero_id: int
    start_time: int
    kills: int
    deaths: int
    assists: int
    xp_per_min: int
    gold_per_min: int
    hero_damage: int
    tower_damage: int
    hero_healing: int
    last_hits: int
    cluster: int
    leaver_status: int
    version: Optional[int] = None
    lane: Optional[int] = None
    lane_role: Optional[int] = None
    is_roaming: Optional[bool] = None
    party_size: Optional[int] = None
    skill: Optional[int] = None


@dataclass(slots=True, frozen=True)
class JobStatus:
    @dataclass(slots=True, frozen=True)
    class JobInfo:
        jobId: int

    job: JobInfo


@dataclass(slots=True)
class DotaItemAttrib:
    key: str
    header: str
    value: Union[str, list[str]]
    footer: str = ""


@dataclass(slots=True)
class DotaItem:
    id: int
    img: str

    cost: Optional[int]
    notes: str
    attrib: list[DotaItemAttrib]
    mc: Union[bool, int]
    cd: int
    lore: str
    components: Optional[list[str]]
    created: bool

    dname: str = ""
    qual: str = ""
    hint: Optional[list[str]] = None
    charges: Union[bool, int] = False


@dataclass(slots=True, frozen=True)
class PlayerRanking:
    hero_id: int
    score: float
    percent_rank: float
    card: int


@dataclass(slots=True, frozen=True)
class HeroMatchup:
    hero_id: int
    games_played: int
    wins: int


async def get_items() -> dict[str, DotaItem]:
    data = await get_url_json_with_file_cache(
        "https://raw.githubusercontent.com/odota/dotaconstants/master/build/items.json"
    )
    return ctor.load(dict[str, DotaItem], data)


async def get_item_ids() -> dict[str, str]:
    data = await get_url_json_with_file_cache(
        "https://raw.githubusercontent.com/odota/dotaconstants/master/build/item_ids.json"
    )
    return ctor.load(dict[str, str], data)


class OpenDotaApi:
    """OpenDota API

    SEE: https://docs.opendota.com/#section/Introduction
    """

    def __init__(self, api_key: str):
        self.key = api_key
        self._params = {"api_key": self.key}

    async def get_match(
        self, match_id: StrOrInt, cache_lifetime: float = 24 * 60 * 60
    ) -> DotaMatch:
        """GET /matches/{match_id}  (cached)

        https://docs.opendota.com/#tag/matches%2Fpaths%2F~1matches~1%7Bmatch_id%7D%2Fget
        """
        url = f"{OPEN_DOTA_API_URL}/matches/{match_id}"
        data = await get_url_json_with_file_cache(
            url, params=self._params, lifetime=cache_lifetime
        )
        return ctor.load(DotaMatch, data)

    async def get_player_recent_matches(
        self, account_id: StrOrInt
    ) -> list[PlayerRecentMatch]:
        """GET /players/{account_id}/recentMatches

        https://docs.opendota.com/#tag/players%2Fpaths%2F~1players~1%7Baccount_id%7D~1recentMatches%2Fget
        """
        url = f"{OPEN_DOTA_API_URL}/players/{account_id}/recentMatches"
        data = await get_url_json_with_file_cache(
            url, params=self._params, lifetime=5 * 60
        )
        return ctor.load(list[PlayerRecentMatch], data)

    async def get_player_rankings(self, account_id: StrOrInt) -> list[PlayerRanking]:
        """GET /players/{account_id}/recentMatches

        https://docs.opendota.com/#tag/players%2Fpaths%2F~1players~1%7Baccount_id%7D~1recentMatches%2Fget
        https://blog.opendota.com/2016/09/30/explaining-rankings/
        """
        url = f"{OPEN_DOTA_API_URL}/players/{account_id}/rankings"
        data = await get_url_json_with_file_cache(
            url, params=self._params, lifetime=5 * 60 * 60
        )
        return ctor.load(list[PlayerRanking], data)

    async def get_hero_matchups(self, hero_id: StrOrInt) -> list[HeroMatchup]:
        """GET /heroes/{hero_id}/matchups

        https://docs.opendota.com/#tag/heroes%2Fpaths%2F~1heroes~1%7Bhero_id%7D~1matchups%2Fget
        https://blog.opendota.com/2016/09/30/explaining-rankings/
        """
        url = f"{OPEN_DOTA_API_URL}/heroes/{hero_id}/matchups"
        data = await get_url_json_with_file_cache(
            url, params=self._params, lifetime=3 * 24 * 60 * 60
        )
        return ctor.load(list[HeroMatchup], data)

    async def request_match_parse(self, match_id: StrOrInt) -> JobStatus:
        """POST /request/{match_id}

        https://docs.opendota.com/#tag/request%2Fpaths%2F~1request~1%7Bmatch_id%7D%2Fpost
        """
        url = f"{OPEN_DOTA_API_URL}/request/{match_id}"
        async with aiohttp.ClientSession() as session:
            resp = await session.post(url, params=self._params)
            data = await resp.json(encoding="utf-8")
            return ctor.load(JobStatus, data)

    async def parse_job_is_complete(self, job_id: StrOrInt) -> bool:
        """GET /request/{jobId}

        https://docs.opendota.com/#tag/request%2Fpaths%2F~1request~1%7BjobId%7D%2Fget
        """
        url = f"{OPEN_DOTA_API_URL}/request/{job_id}"
        async with aiohttp.ClientSession() as session:
            resp = await session.get(url, params=self._params)
            # data = await resp.json(encoding='utf-8')
            return resp.status == 200

    def __repr__(self):
        return "<Open Dota API>"
