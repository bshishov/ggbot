import os
from pprint import pprint

from ggbot.opendota import *


async def _test():
    import logging
    opendota_api_key = os.environ['OPENDOTA_API_KEY']
    logging.basicConfig(level=logging.DEBUG)
    api = OpenDotaApi(api_key=opendota_api_key)
    result = await api.get_match(5949242155)

    """
    #job_id = await api.request_match_parse(5949242155)['job']['jobId']    
    job_id = 148981408
    result = await api.parse_job_is_complete(job_id)
    """

    pprint(result)


if __name__ == '__main__':
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_test())
