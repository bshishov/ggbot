from typing import Union
from ggbot.utils import get_url_json_with_file_cache


__all__ = [
    'SteamApi',
    'STEAM_ID_32_TO_64_OFFSET',
    'to_steam_id_64',
    'to_steam_id_32'
]

STEAM_ID_32_TO_64_OFFSET = 76561197960265728

StrOrInt = Union[str, int]


def to_steam_id_64(steam_id: int) -> int:
    if steam_id < STEAM_ID_32_TO_64_OFFSET:
        return steam_id + STEAM_ID_32_TO_64_OFFSET
    return steam_id


def to_steam_id_32(steam_id: int) -> int:
    if steam_id > STEAM_ID_32_TO_64_OFFSET:
        return steam_id - STEAM_ID_32_TO_64_OFFSET
    return steam_id


class SteamApi:
    """Steam api

    SEE:
    https://dev.dota2.com/forum/dota-2/spectating/replays/webapi/60177-things-you-should-know-before-starting?t=58317

    Steam (TF) docs:
        https://wiki.teamfortress.com/wiki/WebAPI

    Steam Web API docs (mostly v2):
        https://partner.steamgames.com/doc/webapi
    """

    def __init__(self, api_key: str, language: str = 'en'):
        self.key = api_key
        self.language = language

    async def get_app_list(self):
        url = f'http://api.steampowered.com/ISteamApps/GetAppList/v2' \
              f'?key={self.key}' \
              f'&language={self.language}' \
              f'&format=json'
        return await get_url_json_with_file_cache(url)

    async def get_resolve_vanity_url(self, vanity_url: StrOrInt):
        url = f'http://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001' \
              f'?key={self.key}' \
              f'&vanityurl={vanity_url}' \
              f'&language={self.language}' \
              f'&format=json'
        return await get_url_json_with_file_cache(url)

    async def get_player_summary(self, steam_id_64: StrOrInt):
        url = f'http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002' \
              f'?key={self.key}' \
              f'&steamids={steam_id_64}' \
              f'&language={self.language}' \
              f'&format=json'
        return await get_url_json_with_file_cache(url)

    async def get_dota_match_details(self, match_id: StrOrInt, app_id: StrOrInt = 570):
        url = f'http://api.steampowered.com/IDOTA2Match_{app_id}/GetMatchDetails/v1' \
              f'?key={self.key}' \
              f'&match_id={match_id}' \
              f'&language={self.language}' \
              f'&format=json'
        return await get_url_json_with_file_cache(url)

    async def get_test_dota_match_details(self, match_id: StrOrInt):
        return await self.get_dota_match_details(match_id=match_id, app_id=205790)

    def __repr__(self):
        return '<Steam API>'
