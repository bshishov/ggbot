from abc import ABCMeta, abstractmethod
from typing import Optional, Iterable, Set

from attr import dataclass

from ggbot.opendota import DotaMatch, Player, FirstBloodObjective


__all__ = [
    # Basic
    "IPlayerPredicate",
    "IPlayersQuery",
    "IPlayerNumericParamQuery",
    "Just",
    "And",
    "Or",
    "Not",
    "find_player_by_slot",
    "find_player_by_steam_id",
    # Logic
    "AllPlayersInMatch",
    "PlayersInTheSameTeam",
    "PlayersInTheSameParty",
    "HasHighestParamValue",
    "HasLowestParamValue",
    "ParamHigherThan",
    "ParamLowerThan",
    "ParamEqual",
    "PurchasedItemAfter",
    "UsedItemTimesMoreThan",
    "PredictedVictory",
    "HasItemInInventory",
    "HasAtLeastNItemsInInventory",
    "LastHitsInTGreaterThan",
    "DeniesInTGreaterThan",
    "PurchasedItemEarlierThan",
    "PhrasesInChatMoreThan",
    "PermanentBuffStacksMoreThan",
    "IsToxicChat",
    "PickedUpRuneTimesMoreThan",
    "BuybackedMoreThan",
    "MatchShorterThan",
    "MatchLongerThan",
    "ClaimedObjectiveOfType",
    "DiedOfFirstBloodBefore",
    # Players query
    "IN_PARTY",
    "IN_TEAM",
    "IN_MATCH",
    # Param queries
    "P_KILLS",
    "P_DEATHS",
    "P_HEALING",
    "P_ASSISTS",
    "P_NET_WORTH",
    "P_COURIER_KILLS",
    "P_DENIES",
    "P_HERO_DAMAGE",
    "P_APM",
    "P_XPM",
    "P_GPM",
    "P_TOWER_DAMAGE",
    "P_STUNS",
    "P_TEAMFIGHT_PARTICIPATION",
    "P_OBS_PLACED",
    "P_SEN_PLACED",
    "P_CAMPS_STACKED",
    "P_ANCIENT_KILLS",
    # Common predicates:
    "PLAYER_WON",
    "PLAYER_LOST",
    "STOLEN_AEGIS",
    "PICKED_AEGIS",
    "KILLED_ROSHAN",
]


class IPlayerPredicate(metaclass=ABCMeta):
    @abstractmethod
    def check(self, match: DotaMatch, player: Player) -> bool: ...


class IPlayersQuery(metaclass=ABCMeta):
    @abstractmethod
    def iter_players(
        self, match: DotaMatch, subject_player: Player
    ) -> Iterable[Player]: ...


class Just(IPlayerPredicate):
    def __init__(self, value: bool) -> None:
        self._value = value

    def check(self, match: DotaMatch, player: Player) -> bool:
        return self._value


class And(IPlayerPredicate):
    def __init__(self, *predicates: IPlayerPredicate):
        self._predicates = list(predicates)

    def check(self, match: DotaMatch, player: Player) -> bool:
        for predicate in self._predicates:
            if not predicate.check(match, player):
                return False
        return True


class Or(IPlayerPredicate):
    def __init__(self, *predicates: IPlayerPredicate):
        self._predicates = list(predicates)

    def check(self, match: DotaMatch, player: Player) -> bool:
        for predicate in self._predicates:
            if predicate.check(match, player):
                return True
        return False


class Not(IPlayerPredicate):
    def __init__(self, predicate: IPlayerPredicate):
        self._predicate = predicate

    def check(self, match: DotaMatch, player: Player) -> bool:
        return not self._predicate.check(match, player)


class AllPlayersInMatch(IPlayersQuery):
    def iter_players(
        self, match: DotaMatch, subject_player: Player
    ) -> Iterable[Player]:
        return match.players


class PlayersInTheSameTeam(IPlayersQuery):
    def iter_players(
        self, match: DotaMatch, subject_player: Player
    ) -> Iterable[Player]:
        for other in match.players:
            if other.isRadiant == subject_player.isRadiant:
                yield other


class PlayersInTheSameParty(IPlayersQuery):
    def iter_players(
        self, match: DotaMatch, subject_player: Player
    ) -> Iterable[Player]:
        for other in match.players:
            if other.party_id == subject_player.party_id:
                yield other


def find_player_by_slot(match: DotaMatch, player_slot: int) -> Optional[Player]:
    for player in match.players:
        if player.player_slot == player_slot:
            return player
    return None


def find_player_by_steam_id(match: DotaMatch, steam_id: int) -> Optional[Player]:
    for player in match.players:
        if player.account_id == steam_id:
            return player
    return None


class IPlayerNumericParamQuery(metaclass=ABCMeta):
    @abstractmethod
    def get_value(self, player: Player) -> float: ...


@dataclass
class _ParamQuery(IPlayerNumericParamQuery):
    attr: str

    def __post_init__(self):
        assert (
            self.attr in Player.__annotations__
        ), f"No such player attribute: {self.attr}"

    def get_value(self, player: Player) -> float:
        return getattr(player, self.attr, 0) or 0


@dataclass
class HasHighestParamValue(IPlayerPredicate):
    param: IPlayerNumericParamQuery
    players: IPlayersQuery

    def check(self, match: DotaMatch, player: Player) -> bool:
        self_value = self.param.get_value(player)
        for other in self.players.iter_players(match, player):
            if other.player_slot != player.player_slot:  # exclude player
                other_value = self.param.get_value(other)
                if other_value > self_value:
                    return False
        return True


@dataclass
class HasLowestParamValue(IPlayerPredicate):
    players: IPlayersQuery
    param: IPlayerNumericParamQuery

    def check(self, match: DotaMatch, player: Player) -> bool:
        self_value = self.param.get_value(player)
        for other in self.players.iter_players(match, player):
            if other.player_slot != player.player_slot:  # exclude player
                other_value = self.param.get_value(other)
                if other_value < self_value:
                    return False
        return True


@dataclass
class ParamHigherThan(IPlayerPredicate):
    param: IPlayerNumericParamQuery
    value: float

    def check(self, match: DotaMatch, player: Player) -> bool:
        return self.param.get_value(player) > self.value


@dataclass
class ParamLowerThan(IPlayerPredicate):
    param: IPlayerNumericParamQuery
    value: float

    def check(self, match: DotaMatch, player: Player) -> bool:
        return self.param.get_value(player) < self.value


@dataclass
class ParamEqual(IPlayerPredicate):
    param: IPlayerNumericParamQuery
    value: float

    def check(self, match: DotaMatch, player: Player) -> bool:
        return self.param.get_value(player) == self.value


@dataclass
class HeroIsOneOf(IPlayerPredicate):
    hero_ids: Set[int]

    def check(self, match: DotaMatch, player: Player) -> bool:
        return player.hero_id in self.hero_ids


@dataclass
class HasItemInInventory(IPlayerPredicate):
    item: int

    def check(self, match: DotaMatch, player: Player) -> bool:
        return (
            self.item == player.item_0
            or self.item == player.item_1
            or self.item == player.item_2
            or self.item == player.item_3
            or self.item == player.item_4
            or self.item == player.item_5
            or self.item == player.item_neutral
        )


@dataclass
class HasAtLeastNItemsInInventory(IPlayerPredicate):
    item: int
    minimum: int

    def check(self, match: DotaMatch, player: Player) -> bool:
        number_of_items = 0
        for item_in_inventory in (
            player.item_0,
            player.item_1,
            player.item_2,
            player.item_3,
            player.item_4,
            player.item_5,
            player.item_neutral,
        ):
            if item_in_inventory == self.item:
                number_of_items += 1

        return number_of_items >= self.minimum


@dataclass
class UsedItemTimesMoreThan(IPlayerPredicate):
    item: str
    times: int

    def check(self, match: DotaMatch, player: Player) -> bool:
        if player.item_uses is None:
            return False

        return player.item_uses.get(self.item, 0) > self.times


@dataclass
class PurchasedItemEarlierThan(IPlayerPredicate):
    item: str
    time: int

    def check(self, match: DotaMatch, player: Player) -> bool:
        if player.first_purchase_time is None:
            return False
        purchase_time = player.first_purchase_time.get(self.item)
        if purchase_time is None:
            return False
        return purchase_time < self.time


@dataclass
class PurchasedItemAfter(IPlayerPredicate):
    item: str
    time: int

    def check(self, match: DotaMatch, player: Player) -> bool:
        if not player.first_purchase_time:
            return False

        purchase_time = player.first_purchase_time.get(self.item)
        if purchase_time is None:
            return False
        return purchase_time > self.time


@dataclass
class PlayerWon(IPlayerPredicate):
    def check(self, match: DotaMatch, player: Player) -> bool:
        return match.radiant_win == player.isRadiant


@dataclass
class PlayerLost(IPlayerPredicate):
    def check(self, match: DotaMatch, player: Player) -> bool:
        return match.radiant_win != player.isRadiant


@dataclass
class MatchLongerThan(IPlayerPredicate):
    seconds: int

    def check(self, match: DotaMatch, player: Player) -> bool:
        if match.duration is None:
            return False

        return match.duration > self.seconds


@dataclass
class MatchShorterThan(IPlayerPredicate):
    seconds: int

    def check(self, match: DotaMatch, player: Player) -> bool:
        if match.duration is None:
            return False

        return match.duration < self.seconds


@dataclass
class PredictedVictory(IPlayerPredicate):
    def check(self, match: DotaMatch, player: Player) -> bool:
        if player.pred_vict is None:
            return False

        return player.pred_vict


@dataclass
class LastHitsInTGreaterThan(IPlayerPredicate):
    value: int
    match_minutes: int = 10

    def check(self, match: DotaMatch, player: Player) -> bool:
        if not player.lh_t:
            return False

        index = min(self.match_minutes, len(player.lh_t)) - 1
        return player.lh_t[index] > self.value


@dataclass
class DeniesInTGreaterThan(IPlayerPredicate):
    value: int
    match_minutes: int = 10

    def check(self, match: DotaMatch, player: Player) -> bool:
        if not player.dn_t:
            return False

        index = min(self.match_minutes, len(player.dn_t)) - 1
        return player.dn_t[index] > self.value


@dataclass
class PhrasesInChatMoreThan(IPlayerPredicate):
    amount: int

    def check(self, match: DotaMatch, player: Player) -> bool:
        if not match.chat:
            return False
        chat_messages = 0
        for chat_event in match.chat:
            if (
                chat_event.player_slot == player.player_slot
                and chat_event.type == "chat"
            ):
                chat_messages += 1
        return chat_messages > self.amount


@dataclass
class PermanentBuffStacksMoreThan(IPlayerPredicate):
    buff_id: int
    stacks: int

    def check(self, match: DotaMatch, player: Player) -> bool:
        if not player.permanent_buffs:
            return False

        for buff in player.permanent_buffs:
            if buff.permanent_buff is None:
                continue

            if buff.stack_count is None:
                continue

            if buff.permanent_buff == self.buff_id and buff.stack_count > self.stacks:
                return True

        return False


@dataclass
class PickedUpRuneTimesMoreThan(IPlayerPredicate):
    rune_key: int
    amount: int

    def check(self, match: DotaMatch, player: Player) -> bool:
        if not player.runes:
            return False

        runes_count = player.runes.get(str(self.rune_key), 0)
        return runes_count > self.amount


TOXIC_PARTS = {"изи", "ez", "изейшая", "изян", "ебан", "шлюха", "саси", "соси", "долб"}

TOXIC_PHRASES = {
    "?",
    "??",
    "???",
    "nice hate",
}


def _is_toxic(chat_message: str) -> bool:
    chat_message = chat_message.strip().lower()
    if chat_message in TOXIC_PHRASES:
        return True
    for part in TOXIC_PARTS:
        if part in chat_message:
            return True
    return False


@dataclass
class IsToxicChat(IPlayerPredicate):
    min_messages: int = 0

    def check(self, match: DotaMatch, player: Player) -> bool:
        if not match.chat:
            return False
        toxic_messages = 0
        for chat_event in match.chat:
            if chat_event.key is None:
                continue

            if (
                chat_event.player_slot == player.player_slot
                and chat_event.type == "chat"
                and _is_toxic(chat_event.key)
            ):
                toxic_messages += 1
        return toxic_messages > self.min_messages


@dataclass
class BuybackedMoreThan(IPlayerPredicate):
    times: int

    def check(self, match: DotaMatch, player: Player) -> bool:
        if player.buyback_count is None:
            return False
        return player.buyback_count > self.times


@dataclass
class ClaimedObjectiveOfType(IPlayerPredicate):
    type: str
    before: int = 9999999

    def check(self, match: DotaMatch, player: Player) -> bool:
        if not match.objectives:
            return False

        for objective in match.objectives:
            if (
                objective.type == self.type
                and objective.time < self.before
                and getattr(objective, "player_slot", -1) == player.player_slot
            ):
                return True
        return False


@dataclass
class DiedOfFirstBloodBefore(IPlayerPredicate):
    before: int = 9999999

    def check(self, match: DotaMatch, player: Player) -> bool:
        if not match.objectives:
            return False

        for objective in match.objectives:
            if objective.type is None:
                continue

            if (
                objective.type == FirstBloodObjective.type
                and objective.time < self.before
                and match.players[objective.key].player_slot == player.player_slot
            ):
                return True
        return False


# Common player queries
IN_PARTY = PlayersInTheSameParty()
IN_TEAM = PlayersInTheSameTeam()
IN_MATCH = AllPlayersInMatch()


# Common attributes
P_KILLS = _ParamQuery("kills")
P_DEATHS = _ParamQuery("deaths")
P_ASSISTS = _ParamQuery("assists")
P_HEALING = _ParamQuery("hero_healing")
P_NET_WORTH = _ParamQuery("net_worth")
P_STUNS = _ParamQuery("stuns")
P_HERO_DAMAGE = _ParamQuery("hero_damage")
P_XPM = _ParamQuery("xp_per_min")
P_GPM = _ParamQuery("gold_per_min")
P_COURIER_KILLS = _ParamQuery("courier_kills")
P_DENIES = _ParamQuery("denies")
P_APM = _ParamQuery("actions_per_min")
P_TOWER_DAMAGE = _ParamQuery("tower_damage")
P_TEAMFIGHT_PARTICIPATION = _ParamQuery("teamfight_participation")
P_CAMPS_STACKED = _ParamQuery("camps_stacked")
P_OBS_PLACED = _ParamQuery("obs_placed")
P_SEN_PLACED = _ParamQuery("sen_placed")
P_ANCIENT_KILLS = _ParamQuery("ancient_kills")


# Common predicates
PLAYER_WON = PlayerWon()
PLAYER_LOST = PlayerLost()
STOLEN_AEGIS = ClaimedObjectiveOfType("CHAT_MESSAGE_AEGIS_STOLEN")
PICKED_AEGIS = ClaimedObjectiveOfType("CHAT_MESSAGE_AEGIS")
KILLED_ROSHAN = ClaimedObjectiveOfType("CHAT_MESSAGE_ROSHAN_KILL")
