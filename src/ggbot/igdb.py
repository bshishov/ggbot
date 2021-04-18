from typing import Callable, Awaitable

import aiohttp
import pprint
import discord
import logging
import datetime
import random

from context import BotContext
from ggbot.context import Context
from ggbot.component import BotComponent

__all__ = [
    'IgdbClient',
    'get_access_token'
]

_logger = logging.getLogger(__name__)


async def get_access_token(client_id: str, client_secret: str) -> str:
    async with aiohttp.ClientSession() as session:
        response = await session.post('https://id.twitch.tv/oauth2/token', params={
          'grant_type': 'client_credentials',
          'client_id': client_id,
          'client_secret': client_secret
        })
        data = await response.json()
        return data['access_token']


class IgdbClient(BotComponent):

    def __init__(self, client_id: str, access_token: str):
        self.client_id = client_id
        self.access_token = access_token
        self._session = None

    def get_session(self) -> aiohttp.ClientSession:
        return aiohttp.ClientSession(headers={
                'Client-ID': self.client_id,
                'Authorization': f'Bearer {self.access_token}'
            })

    async def query(self, endpoint: str, query: str):
        _logger.info(f'Query {endpoint}: {query}')
        async with self.get_session() as session:
            response = await session.post(f'https://api.igdb.com/v4/{endpoint}', data=query)
            _logger.debug(response)
            data = await response.json()
            _logger.debug(data)
        return data

    @classmethod
    async def create(cls, client_id: str, secret: str):
        token = await get_access_token(client_id, secret)
        #token = 'kb1rokms7m9cllp38d2s801dvy8zw7'
        return IgdbClient(client_id, token)

    async def action_igdb_query(
            self,
            context: Context,
            query: str,
            endpoint: str = 'games',
            success=None,
            fail=None
    ):
        if not query:
            await execute_action(context, fail)
            return

        query = context.render_template(query)
        results = await self.query(endpoint=endpoint, query=query)

        if not results:
            await execute_action(context, fail)
            return

        context.local['results'] = results
        await execute_action(context, success)

    async def action_game_embed_results(
            self,
            context: Context,
            include_video: bool = False,
            limit: int = 1,
            randomize: bool = False
    ):
        results = context.local.get('results', [])
        if randomize:
            random.shuffle(results)

        game_names = []

        for game in results[:limit]:
            game_names.append(game['name'])
            continue

            pprint.pprint(game)
            embed = discord.Embed(
                title=game['name'],
                type='rich',
                url=game['url']
            )
            if 'cover' in game:
                embed.set_thumbnail(url='https:' + game['cover']['url'])

            if 'aggregated_rating' in game:
                embed.add_field(name='Рейтинг', value=str(int(game['aggregated_rating'])))

            if 'first_release_date' in game:
                dt = datetime.datetime.fromtimestamp(game['first_release_date'])
                embed.add_field(name='Релиз', value=dt.strftime('%d.%m.%Y'))

            if 'multiplayer_modes' in game:
                mp_mode = []
                for mode in game['multiplayer_modes']:
                    platform = mode.get('platform', 6)  # PC
                    if platform != 6:
                        continue

                    campaign_coop: bool = mode.get('campaigncoop', False)
                    online_coop: bool = mode.get('onlinecoop', False)
                    online_coop_max: int = mode.get('onlinecoopmax', 0)
                    online_max: int = mode.get('onlinemax', 0)

                    if online_max > 0:
                        mp_mode.append(f'онлайн на {online_max}х')

                    if online_coop:
                        if campaign_coop:
                            s = 'кооп-кампания'
                        else:
                            s = 'кооп'
                        if online_coop_max > 0:
                            s += f' на {online_coop_max}х'
                        mp_mode.append(s)

                if mp_mode:
                    embed.add_field(name='Мультиплеер', value='\n'.join(mp_mode))
            else:
                embed.add_field(name='Мультиплеер', value='сингл онли')

            if include_video:
                for video in game.get('videos', []):
                    video_id = video.get('video_id')
                    if video_id:
                        await context.message.channel.send(f'https://youtu.be/{video_id}')
                        break

            for website in game.get('websites', []):
                if website['category'] == 13:  # steam
                    embed.url = website['url']

            embed.set_footer(text=game['summary'][:180] + '...')
            await context.message.channel.send(embed=embed)

        await context.message.channel.send('\n'.join(game_names))

    async def init(self, context: BotContext):
        pass

    def get_actions(self) -> dict[str, Callable[[Context], Awaitable[None]]]:
        return {
            'igdb-query': self.action_igdb_query,
            'igdb-game-embed-results': self.action_game_embed_results
        }
