from typing import Any, Dict, Union, List
from dataclasses import dataclass, field
import logging
import uuid
import re

import discord
import jinja2

from ggbot.text import IntentMatchResultBase


__all__ = [
    'StrOrTemplate',
    'BotContext',
    'UserContext',
    'Context',
    'MessageExpectation'
]

_logger = logging.getLogger(__name__)


def _generate_uuid() -> str:
    return str(uuid.uuid4())[:8]


StrOrTemplate = Union[str, jinja2.Template]

EMOJI_RE = re.compile(r':[^:\s]+:')


@dataclass
class BotContext:
    template_env: jinja2.environment.Environment
    last_answer: discord.Message = None
    client: discord.Client = None

    def make_template_from_string(self, source: str) -> jinja2.Template:
        return self.template_env.from_string(source)

    def normalize_emoji(self, emoji: str) -> str:
        if emoji.startswith('<') and emoji.endswith('>'):
            # already normalized
            return emoji

        emoji = emoji.strip(' \n\r\t:')

        found: discord.Emoji = discord.utils.get(self.client.emojis, name=emoji)
        if found:
            return str(found)

        return f':{emoji}:'

    def resolve_emojis(self, message: str) -> str:
        def _norm_emoji(match: re.Match):
            return self.normalize_emoji(match.group(0))
        return re.sub(EMOJI_RE, _norm_emoji, message)


@dataclass
class UserContext:
    member: discord.Member

    @property
    def display_name(self) -> str:
        return self.member.display_name


class MessageExpectation:
    def is_active(self) -> bool:
        raise NotImplementedError

    def get_priority(self) -> float:
        raise NotImplementedError

    async def can_be_satisfied(self, message: discord.Message, context: 'Context', nlu) -> bool:
        raise NotImplementedError

    async def satisfy(self, message: discord.Message, context: 'Context'):
        raise NotImplementedError

    def __repr__(self):
        return f'<{self.__class__.__name__}>'


@dataclass
class Context:
    bot: BotContext
    message: discord.Message
    author: UserContext  # conversation starter
    match: IntentMatchResultBase = None
    local: Dict[str, Any] = field(default_factory=dict)
    name: str = field(default_factory=_generate_uuid)
    expecting_message_from: List[discord.Message] = field(default_factory=list)
    _expectations: List[MessageExpectation] = field(default_factory=list)

    def get_template_params(self):
        params = {
            'ctx': self.name,
            'bot': self.bot,
            'message': self.message,
            'user': self.author,
            **self.local
        }

        if self.match is not None:
            params['match'] = {
                'intent': self.match.get_intent(),
                'slots': self.match.get_all_slots()
            }
        return params

    def render_template(self, template: StrOrTemplate, resolve_emoji=True):
        if isinstance(template, jinja2.Template):
            compiled = template
        else:
            compiled = self.bot.make_template_from_string(template)

        rendered = compiled.render(self.get_template_params())

        if isinstance(rendered, str) and resolve_emoji:
            rendered = self.bot.resolve_emojis(rendered)

        return rendered

    def expect(self, expectation: MessageExpectation):
        if expectation.is_active():
            self._expectations.append(expectation)

    def get_active_message_expectations(self) -> List[MessageExpectation]:
        active = []
        for exp in self._expectations:
            if exp.is_active():
                active.append(exp)
        self._expectations = active
        return active
