from typing import Optional, Callable, Awaitable, List
from dataclasses import dataclass
import logging
import asyncio

import discord

from ggbot.text import NluBase
from ggbot.context import *


__all__ = ["ConversationManager", "IntentHandler", "ScenarioHandler"]

_logger = logging.getLogger(__name__)


class IntentHandler:
    async def run(self, context: Context) -> bool:
        raise NotImplementedError


@dataclass
class ScenarioHandler(IntentHandler):
    action: Callable[[Context], Awaitable[bool]]

    async def run(self, context: Context) -> bool:
        return await self.action(context)


@dataclass
class ConversationTask:
    task: asyncio.Task
    context: Context

    def is_active(self) -> bool:
        return not self.task.done()


async def try_run(coroutine):
    try:
        return await coroutine
    except Exception as err:
        logging.exception(err)


class ConversationManager:
    def __init__(
        self,
        nlu: NluBase,
        intent_handlers: dict[str, IntentHandler],
        context: BotContext,
    ):
        self.nlu = nlu
        self.intent_handlers = intent_handlers
        self.context_free_intents = [
            k for k in intent_handlers if k.startswith("intent")
        ]
        self.bot_context = context
        self.conversations = []  # type: List[ConversationTask]

    async def handle_mentioned_message(self, message: discord.Message):
        # Filter out inactive conversations
        self.conversations = [conv for conv in self.conversations if conv.is_active()]

        # Try to continue active conversations if possible
        if self.conversations:
            expectations = []  # type: List[tuple[MessageExpectation, float, Context]]
            for conversation in self.conversations:
                for e in conversation.context.get_active_message_expectations():
                    expectations.append((e, e.get_priority(), conversation.context))

            # Order expectations by priority
            expectations = sorted(expectations, key=lambda _: _[1], reverse=True)

            # Try match expectations
            for e, priority, ctx in expectations:
                if await e.can_be_satisfied(message, ctx, self.nlu):
                    await e.satisfy(message, ctx)
                    return

        # Begin new conversation if possible
        match = self.nlu.match_intent_one_of(message.content, self.context_free_intents)
        if match is not None and match.get_confidence() > 0.49:
            intent = match.get_intent()
        else:
            intent = "mismatch"

        _logger.info(f"Intent: {intent}")
        handler = self.get_handler(intent)
        if handler:
            _logger.info(f"Starting new conversation with intent: {intent}")
            context = Context(
                bot=self.bot_context,
                message=message,
                author=UserContext(member=message.author),
                match=match,
            )

            task = asyncio.create_task(try_run(handler.run(context)), name=context.name)
            dialog = ConversationTask(task=task, context=context)
            self.conversations.append(dialog)

    async def handle_added_reaction(
        self, reaction: discord.Reaction, user: discord.User
    ):
        # TODO: Add Reaction Expectation handling
        pass

    def get_handler(self, intent: str) -> Optional[IntentHandler]:
        if intent in self.intent_handlers:
            return self.intent_handlers[intent]
        if "no-handler" in self.intent_handlers:
            return self.intent_handlers["no-handler"]
        return None
