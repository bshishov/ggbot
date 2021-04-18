from typing import Union
import aiohttp

from ggbot.utils import get_url_json_with_file_cache


__all__ = ['OpenDotaApi']


OPEN_DOTA_API_URL = 'https://api.opendota.com/api/'
StrOrInt = Union[str, int]


class OpenDotaApi:
    """OpenDota API

    SEE: https://docs.opendota.com/#section/Introduction
    """

    def __init__(self, api_key: str):
        self.key = api_key
        self._params = {'api_key': self.key}

    async def get_match(self, match_id: StrOrInt) -> dict:
        """GET /matches/{match_id}  (cached)

        https://docs.opendota.com/#tag/matches%2Fpaths%2F~1matches~1%7Bmatch_id%7D%2Fget
        """
        url = f'{OPEN_DOTA_API_URL}/matches/{match_id}'
        return await get_url_json_with_file_cache(url, params=self._params)

    async def get_player_recent_matches(self, account_id: StrOrInt) -> list:
        """GET /players/{account_id}/recentMatches

         https://docs.opendota.com/#tag/players%2Fpaths%2F~1players~1%7Baccount_id%7D~1recentMatches%2Fget
        """
        url = f'{OPEN_DOTA_API_URL}/players/{account_id}/recentMatches '
        async with aiohttp.ClientSession() as session:
            resp = await session.get(url, params=self._params)
            return await resp.json(encoding='utf-8')

    async def request_match_parse(self, match_id: StrOrInt) -> dict:
        """POST /request/{match_id}

        https://docs.opendota.com/#tag/request%2Fpaths%2F~1request~1%7Bmatch_id%7D%2Fpost
        """
        url = f'{OPEN_DOTA_API_URL}/request/{match_id}'
        async with aiohttp.ClientSession() as session:
            resp = await session.post(url, params=self._params)
            return await resp.json(encoding='utf-8')

    async def parse_job_is_complete(self, job_id: StrOrInt) -> bool:
        """GET /request/{jobId}

        https://docs.opendota.com/#tag/request%2Fpaths%2F~1request~1%7BjobId%7D%2Fget
        """
        url = f'{OPEN_DOTA_API_URL}/request/{job_id}'
        async with aiohttp.ClientSession() as session:
            resp = await session.get(url, params=self._params)
            return resp.status == 200

    def __repr__(self):
        return '<Open Dota API>'
