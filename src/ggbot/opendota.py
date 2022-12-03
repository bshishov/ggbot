from typing import Union, Literal, Dict, List, Optional
import aiohttp

from attr import dataclass
import ctor

from ggbot.utils import get_url_json_with_file_cache


__all__ = [
    "DotaMatch",
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
    time: int
    type: str
    key: str
    slot: int
    player_slot: int


@dataclass(slots=True, frozen=True)
class DraftTiming:
    order: int
    pick: bool
    active_team: int
    hero_id: int
    player_slot: Optional[int]
    extra_time: int
    total_time_taken: int


@dataclass(slots=True, frozen=True)
class BaseObjective:
    time: int
    type: str


@dataclass(slots=True, frozen=True)
class FirstBloodObjective(BaseObjective):
    type: Literal["CHAT_MESSAGE_FIRSTBLOOD"]
    slot: int
    key: int
    player_slot: int


@dataclass(slots=True, frozen=True)
class CourierLostObjective(BaseObjective):
    type: Literal["CHAT_MESSAGE_COURIER_LOST"]
    team: int


@dataclass(slots=True, frozen=True)
class BuildingKillObjective(BaseObjective):
    type: Literal["building_kill"]
    unit: str
    key: str
    slot: Optional[int] = None
    player_slot: Optional[int] = None


@dataclass(slots=True, frozen=True)
class RoshanKillObjective(BaseObjective):
    type: Literal["CHAT_MESSAGE_ROSHAN_KILL"]
    team: int


@dataclass(slots=True, frozen=True)
class AegisObjective(BaseObjective):
    type: Literal["CHAT_MESSAGE_AEGIS"]
    slot: int
    player_slot: int


@dataclass(slots=True, frozen=True)
class AegisStolenObjective(BaseObjective):
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
    deaths_pos: Dict[str, Dict[str, int]]
    ability_uses: Dict[str, int]
    ability_targets: Dict[str, Dict[str, int]]
    item_uses: Dict[str, int]
    killed: Dict[str, int]
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
    start: int
    end: int
    last_death: int
    deaths: int
    players: List[TeamFightPlayer]


@dataclass(slots=True, frozen=True)
class PlayerBuybackEvent:
    time: int
    slot: int
    type: Literal["buyback_log"]
    player_slot: int


@dataclass(slots=True, frozen=True)
class BenchmarkValue:
    raw: Optional[float] = None
    pct: Optional[float] = None


@dataclass(slots=True, frozen=True)
class PermanentBuffState:
    permanent_buff: int
    stack_count: int


@dataclass(slots=True, frozen=True)
class RunePickupEvent:
    time: int
    key: int


@dataclass(slots=True, frozen=True, repr=False)
class Player:
    match_id: int
    player_slot: int
    ability_targets: Optional[Dict[str, Dict[str, int]]]
    ability_upgrades_arr: List[int]
    ability_uses: Optional[Dict[str, int]]
    account_id: Optional[int]
    actions: Optional[Dict[str, int]]
    # additional_units: ???
    assists: int
    backpack_0: int
    backpack_1: int
    backpack_2: int
    backpack_3: Optional[int]
    buyback_log: Optional[List[PlayerBuybackEvent]]
    camps_stacked: Optional[int]
    # connection_log: int
    creeps_stacked: Optional[int]
    # damage
    # damage_inflictor
    # damage_inflictor_received
    # damage_taken
    # damage_targets
    deaths: int
    denies: int
    dn_t: Optional[List[int]]
    firstblood_claimed: Optional[int]
    gold: int
    gold_per_min: int
    gold_reasons: Optional[Dict[str, int]]
    gold_spent: int
    gold_t: Optional[List[int]]
    hero_damage: int
    hero_healing: int
    hero_hits: Optional[Dict[str, int]]
    hero_id: int
    item_0: int
    item_1: int
    item_2: int
    item_3: int
    item_4: int
    item_5: int
    item_neutral: int
    item_uses: Optional[Dict[str, int]]
    # kill_streaks
    killed: Optional[Dict[str, int]]
    killed_by: Optional[Dict[str, int]]
    kills: int
    # kills_log
    # lane_pos
    last_hits: int
    leaver_status: int
    level: int
    lh_t: Optional[List[int]]
    # life_state
    # max_hero_hit
    # multi_kills
    net_worth: Optional[int]
    # obs
    # obs_left_log
    # obs_log
    obs_placed: Optional[int]
    party_id: Optional[int]
    party_size: Optional[int]
    performance_others: Optional[Dict[str, int]]
    permanent_buffs: Optional[List[PermanentBuffState]]
    pred_vict: Optional[bool]
    purchase: Optional[Dict[str, int]]
    # purchase_log
    randomed: Optional[bool]
    # repicked: ???
    roshans_killed: Optional[int]
    rune_pickups: Optional[int]
    runes: Optional[Dict[str, int]]
    runes_log: Optional[List[RunePickupEvent]]
    # sen
    # sen_left_log
    # sen_log
    # sen_log
    sen_placed: Optional[int]
    stuns: Optional[float]
    teamfight_participation: Optional[float]
    times: Optional[List[int]]
    tower_damage: int
    towers_killed: Optional[int]
    xp_per_min: int
    xp_reasons: Optional[Dict[str, int]]
    xp_t: Optional[List[int]]
    radiant_win: bool
    start_time: int
    duration: int
    cluster: int
    lobby_type: int
    game_mode: int
    is_contributor: bool
    patch: int
    isRadiant: bool
    win: int
    lose: int
    total_gold: int
    total_xp: int
    abandons: int
    # rank_tier: Optional[int] ???
    # cosmetics
    benchmarks: Dict[str, BenchmarkValue]
    tower_kills: Optional[int] = None
    courier_kills: Optional[int] = None
    lane_kills: Optional[int] = None
    hero_kills: Optional[int] = None
    observer_kills: Optional[int] = None
    sentry_kills: Optional[int] = None
    roshan_kills: Optional[int] = None
    necronomicon_kills: Optional[int] = None
    ancient_kills: Optional[int] = None
    buyback_count: Optional[int] = None
    observer_uses: Optional[int] = None
    sentry_uses: Optional[int] = None
    lane_efficiency: Optional[float] = None
    lane_efficiency_pct: Optional[int] = None
    lane: Optional[int] = None
    lane_role: Optional[int] = None
    is_roaming: Optional[bool] = None
    purchase_time: Optional[Dict[str, int]] = None
    first_purchase_time: Optional[Dict[str, int]] = None
    item_win: Optional[Dict[str, int]] = None
    item_usage: Optional[Dict[str, int]] = None
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


@dataclass(slots=True, frozen=True, repr=False)
class DotaMatch:
    match_id: int
    barracks_status_dire: int
    barracks_status_radiant: int
    chat: Optional[List[ChatEvent]]
    cluster: int
    cosmetics: Optional[Dict[str, int]]
    dire_score: int
    dire_team_id: Optional[int]
    draft_timings: Optional[List[DraftTiming]]
    duration: int
    engine: int
    first_blood_time: int
    game_mode: int
    human_players: int
    leagueid: int
    lobby_type: int
    match_seq_num: int
    negative_votes: int
    objectives: Optional[List[OneOfObjectives]]
    picks_bans: Optional[List[PickBan]]
    positive_votes: int
    radiant_gold_adv: Optional[List[int]]
    radiant_score: int
    radiant_team_id: Optional[int]
    radiant_win: bool
    radiant_xp_adv: Optional[List[int]]
    skill: Optional[int]
    start_time: int
    teamfights: Optional[List[TeamFight]]
    tower_status_dire: int
    tower_status_radiant: int
    version: Optional[int]
    players: List[Player]
    patch: int

    all_word_counts: Optional[Dict[str, int]] = None
    my_word_counts: Optional[Dict[str, int]] = None
    replay_url: Optional[str] = None
    region: Optional[int] = None
    throw: Optional[int] = None
    loss: Optional[int] = None
    replay_salt: Optional[int] = None
    series_id: Optional[int] = None
    series_type: Optional[int] = None


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
    version: Optional[int]
    kills: int
    deaths: int
    assists: int
    skill: Optional[int]
    xp_per_min: int
    gold_per_min: int
    hero_damage: int
    tower_damage: int
    hero_healing: int
    last_hits: int
    lane: Optional[int]
    lane_role: Optional[int]
    is_roaming: Optional[bool]
    cluster: int
    leaver_status: int
    party_size: Optional[int]


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
    value: Union[str, List[str]]
    footer: str = ""


@dataclass(slots=True)
class DotaItem:
    id: int
    img: str

    cost: Optional[int]
    notes: str
    attrib: List[DotaItemAttrib]
    mc: Union[bool, int]
    cd: int
    lore: str
    components: Optional[List[str]]
    created: bool

    dname: str = ""
    qual: str = ""
    hint: Optional[List[str]] = None
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


async def get_items() -> Dict[str, DotaItem]:
    data = await get_url_json_with_file_cache(
        "https://raw.githubusercontent.com/odota/dotaconstants/master/build/items.json"
    )
    return ctor.load(Dict[str, DotaItem], data)


async def get_item_ids() -> Dict[str, str]:
    data = await get_url_json_with_file_cache(
        "https://raw.githubusercontent.com/odota/dotaconstants/master/build/item_ids.json"
    )
    return ctor.load(Dict[str, str], data)


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
    ) -> List[PlayerRecentMatch]:
        """GET /players/{account_id}/recentMatches

        https://docs.opendota.com/#tag/players%2Fpaths%2F~1players~1%7Baccount_id%7D~1recentMatches%2Fget
        """
        url = f"{OPEN_DOTA_API_URL}/players/{account_id}/recentMatches"
        data = await get_url_json_with_file_cache(
            url, params=self._params, lifetime=5 * 60
        )
        return ctor.load(List[PlayerRecentMatch], data)

    async def get_player_rankings(self, account_id: StrOrInt) -> List[PlayerRanking]:
        """GET /players/{account_id}/recentMatches

        https://docs.opendota.com/#tag/players%2Fpaths%2F~1players~1%7Baccount_id%7D~1recentMatches%2Fget
        https://blog.opendota.com/2016/09/30/explaining-rankings/
        """
        url = f"{OPEN_DOTA_API_URL}/players/{account_id}/rankings"
        data = await get_url_json_with_file_cache(
            url, params=self._params, lifetime=5 * 60 * 60
        )
        return ctor.load(List[PlayerRanking], data)

    async def get_hero_matchups(self, hero_id: StrOrInt) -> List[HeroMatchup]:
        """GET /heroes/{hero_id}/matchups

        https://docs.opendota.com/#tag/heroes%2Fpaths%2F~1heroes~1%7Bhero_id%7D~1matchups%2Fget
        https://blog.opendota.com/2016/09/30/explaining-rankings/
        """
        url = f"{OPEN_DOTA_API_URL}/heroes/{hero_id}/matchups"
        data = await get_url_json_with_file_cache(
            url, params=self._params, lifetime=3 * 24 * 60 * 60
        )
        return ctor.load(List[HeroMatchup], data)

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
