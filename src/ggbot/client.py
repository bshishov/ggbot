import logging

import discord

from .conversation import *


_logger = logging.getLogger(__name__)

__all__ = ["Client"]


class Client(discord.Client):
    def __init__(self, conversation_manager: ConversationManager):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.cm = conversation_manager

    def is_mentioned(self, message: discord.Message):
        for mention in message.mentions:
            if mention == self.user:
                return True
        return False

    async def on_ready(self):
        _logger.info("Ready")

    async def on_message(self, message: discord.Message):
        if message.author == self.user:
            return

        if (
            isinstance(message.channel, discord.DMChannel)
            or (
                isinstance(message.channel, discord.TextChannel)
                and message.channel.name == "gg-bot-test"
            )
            or self.is_mentioned(message)
        ):
            _logger.debug("Handling mentioned message")
            await self.cm.handle_mentioned_message(message)

    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        await self.cm.handle_added_reaction(reaction, user)
