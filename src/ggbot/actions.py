from typing import Optional, Any
import logging
import asyncio
from dataclasses import dataclass, field

import discord

from ggbot.context import *


__all__ = [
    'message_intent_is',
    'reply_to_message',
    'wait_for_message_from_user',
    'wait_for_message_from_user_with_intents',
    'wait_for_message_from_channel',
    'send_message_to_channel',
    'edit_last_answer',
    'SendEmbed',
    'add_reaction_to_reply_message',
    'add_reaction_to_request_message'
]

_logger = logging.getLogger(__name__)


@dataclass
class MessageFromUserExpectation(MessageExpectation):
    expected_user_id: int
    priority: float = 1
    event: asyncio.Event = field(default_factory=asyncio.Event)

    def __post_init__(self):
        _logger.debug(f'Waiting for message from {self.expected_user_id}')

    async def get_priority(self) -> float:
        return self.priority

    async def can_be_satisfied(self, message: discord.Message, context: 'Context', nlu) -> bool:
        _logger.debug(f'Checking if message.author.id '
                      f'expected_user_id={self.expected_user_id} '
                      f'message.author.id={message.author.id} ({message.author.name})'
                      f'context.author.member.id={context.author.member.id} '
                      f'ctx={context.name}')
        return message.author.id == self.expected_user_id

    async def satisfy(self, message: discord.Message, context: 'Context'):
        _logger.debug(f'Satisfying {self.__class__.__name__} expectation '
                      f'expected_user_id={self.expected_user_id} '
                      f'message.author.id={message.author.id} ({message.author.name})'
                      f'context.author.member.id={context.author.member.id} '
                      f'ctx={context.name}')
        context.message = message
        self.event.set()


@dataclass
class MessageFromUserWithIntentExpectation(MessageExpectation):
    expected_user_id: int
    intents: list[str]
    priority: float = 1
    event: asyncio.Event = field(default_factory=asyncio.Event)

    async def get_priority(self) -> float:
        return self.priority

    async def can_be_satisfied(self, message: discord.Message, context: 'Context', nlu) -> bool:
        if not message.author.id == self.expected_user_id:
            return False

        match = nlu.match_intent_one_of(message.content, intents=self.intents)
        if not match:
            return False

        context.match = match
        return True

    async def satisfy(self, message: discord.Message, context: 'Context'):
        context.message = message
        self.event.set()


@dataclass
class MessageFromChannelExpectation(MessageExpectation):
    expected_channel: int
    priority: float = 0.5
    event: asyncio.Event = field(default_factory=asyncio.Event)

    def __post_init__(self):
        _logger.debug(f'Waiting for message from channel {self.expected_channel}')

    async def get_priority(self) -> float:
        return self.priority

    async def can_be_satisfied(self, message: discord.Message, context: 'Context', nlu) -> bool:
        _logger.debug(f'Checking {self.__class__.__name__} '
                      f'expected_channel={self.expected_channel} '
                      f'message.channel.id={message.channel.id} ({message.channel.name})'
                      f'ctx={context.name}')
        return message.channel.id == self.expected_channel

    async def satisfy(self, message: discord.Message, context: 'Context'):
        _logger.debug(f'Satisfying {self.__class__.__name__} expectation '
                      f'expected_channel={self.expected_channel} '
                      f'message.channel.id={message.channel.id} ({message.channel.name})'
                      f'ctx={context.name}')
        context.message = message
        self.event.set()


def message_intent_is(intent: str):
    async def _fn(context: Context):
        if not context.match:
            return False
        return context.match.get_intent() == intent
    return _fn


def wait_for_message_from_user_with_intents(intents: list[str], seconds: float = 7):
    async def _fn(ctx: Context):
        expectation = MessageFromUserWithIntentExpectation(ctx.message.author.id, intents)
        ctx.expectations.append(expectation)
        try:
            await asyncio.wait_for(expectation.event.wait(), timeout=seconds)
            return True
        except asyncio.TimeoutError:
            return False
    return _fn


def wait_for_message_from_user(seconds: float = 7):
    async def _fn(ctx: Context):
        expectation = MessageFromUserExpectation(ctx.message.author.id)
        ctx.expectations.append(expectation)
        try:
            await asyncio.wait_for(expectation.event.wait(), timeout=seconds)
            return True
        except asyncio.TimeoutError:
            return False
    return _fn


def wait_for_message_from_channel(seconds: float = 7):
    async def _fn(ctx: Context):
        expectation = MessageFromChannelExpectation(ctx.message.channel.id)
        ctx.expectations.append(expectation)
        try:
            await asyncio.wait_for(expectation.event.wait(), timeout=seconds)
            return True
        except asyncio.TimeoutError:
            return False
    return _fn


def send_message_to_channel(msg: str):
    async def _fn(context: Context):
        if msg:
            rendered = context.render_template(msg)
            answer_message = await context.message.channel.send(rendered)
            context.bot.last_answer = answer_message
        return True
    return _fn


def reply_to_message(msg: str):
    async def _fn(context: Context):
        if msg:
            rendered = context.render_template(msg)
            if isinstance(context.message.channel, discord.DMChannel):
                # DM doesnt need reply
                answer_message = await context.message.channel.send(rendered)
            else:
                answer_message = await context.message.reply(rendered)
            context.bot.last_answer = answer_message
        return True
    return _fn


def edit_last_answer(msg: str):
    async def _fn(context: Context):
        if msg:
            rendered = context.render_template(msg)
            await context.bot.last_answer.edit(content=rendered)
        return True
    return _fn


def add_reaction_to_request_message(reaction: str):
    async def _fn(context: Context):
        if reaction:
            await context.message.add_reaction(context.render_template(reaction))
        return True
    return _fn


def add_reaction_to_reply_message(reaction: str):
    async def _fn(context: Context):
        if reaction and context.bot.last_answer:
            await context.bot.last_answer.add_reaction(context.render_template(reaction))
        return True
    return _fn


def _fix_url(url: str):
    if url and url.startswith('//'):
        return f'https:{url}'
    return url


@dataclass
class SendEmbed:
    title: str
    type: str = 'rich'
    description: Optional[str] = None
    url: Optional[str] = None
    thumbnail: Optional[str] = None
    image: Optional[str] = None
    footer: Optional[str] = None
    fields: Optional[dict[str, Any]] = None
    video_url: Optional[str] = None
    video_height: Optional[str] = None
    video_width: Optional[str] = None

    async def __call__(self, context: Context) -> bool:
        title = context.render_template(self.title)
        embed = discord.Embed(title=title, type=self.type)

        if self.description:
            embed.description = context.render_template(self.description)

        if self.url:
            url = context.render_template(self.url)
            embed.url = _fix_url(url)

        if self.thumbnail:
            thumbnail = context.render_template(self.thumbnail)
            embed.set_thumbnail(url=_fix_url(thumbnail))

        if self.image:
            image = context.render_template(self.image)
            embed.set_image(url=_fix_url(image))

        if self.fields:
            for field_name, field_value in self.fields.items():
                field_value = context.render_template(field_value)
                if field_name and field_value is not None:
                    embed.add_field(name=field_name, value=field_value)

        if self.footer:
            footer = context.render_template(self.footer)
            if footer:
                embed.set_footer(text=footer)

        if self.video_url:
            video_url = context.render_template(self.footer)
            embed.video.url = _fix_url(video_url)

            if self.video_height:
                video_height = context.render_template(self.video_height)
                embed.video.height = video_height

            if self.video_width:
                video_width = context.render_template(self.video_width)
                embed.video.width = video_width

        await context.message.channel.send(embed=embed)
        return True
