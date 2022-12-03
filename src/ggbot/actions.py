from typing import Optional, Dict, TypeVar
import logging
import asyncio
import time
from dataclasses import dataclass

import discord

from ggbot.context import *
from ggbot.btdata import Const
from ggbot.bttypes import *


__all__ = [
    "message_intent_is",
    "reply_to_message",
    "reply_to_message2",
    "wait_for_message_from_user",
    "wait_for_message_from_user_with_intents",
    "wait_for_message_from_channel",
    "send_message_to_channel",
    "send_message_to_channel2",
    "edit_last_answer",
    "SendEmbed",
    "add_reaction_to_reply_message",
    "add_reaction_to_request_message",
]

_logger = logging.getLogger(__name__)


class TimedEventMessageExpectation(MessageExpectation):
    def __init__(self, timeout: float, priority: float):
        self.timeout = timeout
        self.expire_at = time.time() + timeout
        self.event = asyncio.Event()
        self.priority = priority

    def get_priority(self) -> float:
        return self.priority

    def is_active(self) -> bool:
        if self.event.is_set():
            return False
        return time.time() < self.expire_at

    async def can_be_satisfied(
        self, message: discord.Message, context: Context, nlu
    ) -> bool:
        raise NotImplementedError

    async def satisfy(self, message: discord.Message, context: Context) -> None:
        raise NotImplementedError

    async def wait_for_event(self):
        await asyncio.wait_for(self.event.wait(), timeout=self.timeout)


class MessageFromUserExpectation(TimedEventMessageExpectation):
    def __init__(self, expected_user_id: int, timeout: float, priority: float = 1.0):
        super().__init__(timeout=timeout, priority=priority)
        self.expected_user_id = expected_user_id

    def __post_init__(self):
        _logger.debug(f"Waiting for message from {self.expected_user_id}")

    async def can_be_satisfied(
        self, message: discord.Message, context: Context, nlu
    ) -> bool:
        _logger.debug(
            f"Checking if message.author.id "
            f"expected_user_id={self.expected_user_id} "
            f"message.author.id={message.author.id} ({message.author.name})"
            f"context.author.member.id={context.author.member.id} "
            f"ctx={context.name}"
        )
        return message.author.id == self.expected_user_id

    async def satisfy(self, message: discord.Message, context: Context) -> None:
        _logger.debug(
            f"Satisfying {self.__class__.__name__} expectation "
            f"expected_user_id={self.expected_user_id} "
            f"message.author.id={message.author.id} ({message.author.name})"
            f"context.author.member.id={context.author.member.id} "
            f"ctx={context.name}"
        )
        context.message = message
        self.event.set()


@dataclass
class MessageFromUserWithIntentExpectation(TimedEventMessageExpectation):
    def __init__(
        self,
        expected_user_id: int,
        intents: list[str],
        timeout: float,
        priority: float = 1.0,
    ):
        super().__init__(timeout=timeout, priority=priority)
        self.expected_user_id = expected_user_id
        self.intents = intents

    async def can_be_satisfied(
        self, message: discord.Message, context: Context, nlu
    ) -> bool:
        if not message.author.id == self.expected_user_id:
            return False

        match = nlu.match_intent_one_of(message.content, intents=self.intents)
        if not match:
            return False

        context.match = match
        return True

    async def satisfy(self, message: discord.Message, context: Context):
        context.message = message
        self.event.set()


class MessageFromChannelExpectation(TimedEventMessageExpectation):
    def __init__(self, expected_channel_id: int, timeout: float, priority: float = 0.5):
        super().__init__(timeout=timeout, priority=priority)
        self.expected_channel_id = expected_channel_id

    async def can_be_satisfied(
        self, message: discord.Message, context: "Context", nlu
    ) -> bool:
        _logger.debug(
            f"Checking {self.__class__.__name__} "
            f"expected_channel={self.expected_channel_id} "
            f"message.channel.id={message.channel.id} ({message.channel.name})"
            f"ctx={context.name}"
        )
        return message.channel.id == self.expected_channel_id

    async def satisfy(self, message: discord.Message, context: "Context"):
        _logger.debug(
            f"Satisfying {self.__class__.__name__} expectation "
            f"expected_channel={self.expected_channel_id} "
            f"message.channel.id={message.channel.id} ({message.channel.name})"
            f"ctx={context.name}"
        )
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
        expectation = MessageFromUserWithIntentExpectation(
            expected_user_id=ctx.message.author.id, intents=intents, timeout=seconds
        )
        ctx.expect(expectation)
        try:
            await expectation.wait_for_event()
            return True
        except asyncio.TimeoutError:
            return False

    return _fn


def wait_for_message_from_user(seconds: float = 7):
    async def _fn(ctx: Context):
        expectation = MessageFromUserExpectation(ctx.message.author.id, timeout=seconds)
        ctx.expect(expectation)
        try:
            await expectation.wait_for_event()
            return True
        except asyncio.TimeoutError:
            return False

    return _fn


def wait_for_message_from_channel(seconds: float = 7):
    async def _fn(ctx: Context):
        expectation = MessageFromChannelExpectation(
            ctx.message.channel.id, timeout=seconds
        )
        ctx.expect(expectation)
        try:
            await expectation.wait_for_event()
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


def send_message_to_channel2(msg: IExpression[str]):
    async def _fn(context: Context):
        message = msg.evaluate(context)
        if message:
            answer_message = await context.message.channel.send(message)
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


def reply_to_message2(msg: IExpression[str]):
    async def _fn(context: Context):
        value = msg.evaluate(context)
        if value:
            if isinstance(context.message.channel, discord.DMChannel):
                # DM doesnt need reply
                answer_message = await context.message.channel.send(value)
            else:
                answer_message = await context.message.reply(value)
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
            await context.bot.last_answer.add_reaction(
                context.render_template(reaction)
            )
        return True

    return _fn


def _fix_url(url: str):
    if url and url.startswith("//"):
        return f"https:{url}"
    return url


T = TypeVar("T")


def _eval(x: Optional[IExpression[T]], context: Context) -> Optional[T]:
    if x:
        return x.evaluate(context)


@dataclass
class SendEmbed:
    title: IExpression[str]
    type: IExpression[str] = Const(STRING, "rich")
    description: Optional[IExpression[str]] = None
    url: Optional[IExpression[str]] = None
    thumbnail: Optional[IExpression[str]] = None
    image: Optional[IExpression[str]] = None
    footer: Optional[IExpression[str]] = None
    fields: Optional[IExpression[Dict[str, str]]] = None
    video_url: Optional[IExpression[str]] = None
    video_height: Optional[IExpression[str]] = None
    video_width: Optional[IExpression[str]] = None

    async def __call__(self, context: Context) -> bool:
        title = self.title.evaluate(context)
        embed_type = self.type.evaluate(context)
        description = _eval(self.description, context)
        url = _eval(self.url, context)
        thumbnail = _eval(self.thumbnail, context)
        image = _eval(self.image, context)
        fields = _eval(self.fields, context)
        footer = _eval(self.footer, context)
        video_url = _eval(self.video_url, context)
        video_height = _eval(self.video_height, context)
        video_width = _eval(self.video_width, context)

        embed = discord.Embed(title=title, type=embed_type)

        if description:
            embed.description = description

        if url:
            embed.url = _fix_url(url)

        if thumbnail:
            embed.set_thumbnail(url=_fix_url(thumbnail))

        if image:
            embed.set_image(url=_fix_url(image))

        if fields:
            for field_name, field_value in fields.items():
                field_value = context.render_template(field_value)
                field_name = context.render_template(field_name)
                if field_name and field_value is not None:
                    embed.add_field(name=field_name, value=field_value)

        if footer:
            embed.set_footer(text=footer)

        if video_url:
            embed.video.url = _fix_url(video_url)

            if video_height:
                embed.video.height = video_height

            if video_width:
                embed.video.width = video_width

        await context.message.channel.send(embed=embed)
        return True
