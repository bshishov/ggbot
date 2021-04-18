from pprint import pprint
import os

from ggbot.igdb import *


async def _test():
    client_id = os.getenv('IGDB_CLIENT_ID')
    secret = os.getenv('IGDB_SECRET')
    assert client_id and secret
    client = await IgdbClient.create(client_id, secret)

    #await query(session, 'fields name,id; where category = 1; limit 100;', 'platforms')
    # await query(session, 'fields name,category,platforms; where category = 0 & platforms = {48, 167};)
    #await client.query('game_modes', """fields *; limit 100; """)
    result = await client.query('games', """search "terraria"; fields *; where category = 0; """)
    pprint(result)


if __name__ == '__main__':
    import logging
    import asyncio
    logging.basicConfig(level=logging.DEBUG)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_test())
