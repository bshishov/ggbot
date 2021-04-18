from abc import ABCMeta, abstractmethod

from .context import BotContext

__all__ = [
    'BotComponent'
]


class BotComponent(metaclass=ABCMeta):
    @abstractmethod
    async def init(self, context: BotContext): ...
