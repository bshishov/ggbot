import logging

import discord

from .bot import *


_logger = logging.getLogger(__name__)

__all__ = ['Client']


class Client(discord.Client):
    def __init__(self, bot: Bot):
        super(Client, self).__init__()
        self.bot = bot

    def is_mentioned(self, message: discord.Message):
        for mention in message.mentions:
            if mention == self.user:
                return True
        return False

    async def start(self, *args, **kwargs):
        await super().start(*args, **kwargs)
        for emoji in self.emojis:
            _logger.info(f"Emoji: {emoji}")

    async def on_message(self, message: discord.Message):
        if message.author == self.user:
            return

        if (
                isinstance(message.channel, discord.DMChannel)
                or message.channel.name == 'gg-bot-test'
                or self.is_mentioned(message)
        ):
            _logger.debug('Handling mentioned message')
            await self.bot.handle_mentioned_message(message)

    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        await self.bot.handle_added_reaction(reaction, user)
