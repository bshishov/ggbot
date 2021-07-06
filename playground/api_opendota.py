import os

from ggbot.opendota import *


async def _test():
    import logging
    opendota_api_key = os.environ['OPENDOTA_API_KEY']
    logging.basicConfig(level=logging.DEBUG)
    api = OpenDotaApi(api_key=opendota_api_key)

    """
    items = await get_items()
    item_ids = await get_item_ids()
    for item in items.values():
        print(item.id, item_ids.get(str(item.id)))
    """

    # result = await api.get_player_recent_matches(55136643) # NOT Found
    #result = await api.get_player_recent_matches(874832039)
    #result = await api.get_match(5949242155)
    result = await api.get_match(6076689179)

    """
    #job_id = await api.request_match_parse(5949242155)['job']['jobId']    
    job_id = 148981408
    result = await api.parse_job_is_complete(job_id)
    """
    print(result)


if __name__ == '__main__':
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_test())
