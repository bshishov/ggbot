import os
from pprint import pprint

from ggbot.steam import *


async def _test():
    import logging
    logging.basicConfig(level=logging.DEBUG)
    steam_api_key = os.environ['STEAM_WEB_API_KEY']
    steam_api = SteamApi(api_key=steam_api_key, language='ru')

    result = await steam_api.get_player_summary(to_steam_id_64(99526321))
    #result = await steam_api.get_player_summary(76561198003451613)
    #result = await steam_api.get_dota_match_details(5949242155)

    pprint(result)


if __name__ == '__main__':
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_test())
