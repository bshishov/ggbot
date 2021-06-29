import logging
import os

from ggbot.opendota import OpenDotaApi
from ggbot.dota.medals import *


async def _main():
    opendota_api_key = os.environ['OPENDOTA_API_KEY']
    logging.basicConfig(level=logging.DEBUG)
    api = OpenDotaApi(api_key=opendota_api_key)

    # job = await api.request_match_parse(6059014813)
    # if await api.parse_job_is_complete(job['job']['jobId']):

    #match = await api.get_match(5949242155)
    #match = await api.get_match(6055615801)  # Junk Tapes на снайпере
    #match = await api.get_match(6054262211)
    #match = await api.get_match(6058991340)
    #match = await api.get_match(6059014813)
    #match = await api.get_match(6051297617)
    #match = await api.get_match(6062351322)
    #match = await api.get_match(6062424956)
    match = await api.get_match(6062476014)

    for player in match.players:
        print(f'\n[{player.player_slot}] {player.personaname} {player.account_id}')
        for medal in PLAYER_MEDALS:
            result = medal.predicate.check(match, player)
            if result:
                print(f'\t{medal.icon} {medal.name}')


if __name__ == '__main__':
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_main())
