from typing import Any, Optional

import pickledb

from .context import Context, BotContext
from .component import BotComponent

__all__ = [
    'BaseStorage',
    'DictStorage',
    'PickleDbStorage',
    'Memory'
]


class BaseStorage:
    def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError

    def set(self, key: str, value: Any):
        raise NotImplementedError

    def contains_key(self, key: str) -> bool:
        raise NotImplementedError


class DictStorage(BaseStorage):
    def __init__(self, data: Optional[dict] = None):
        self.data = data if data is not None else {}

    def get(self, key: str) -> Optional[Any]:
        return self.data.get(key)

    def set(self, key: str, value: Any):
        self.data[key] = value

    def contains_key(self, key: str) -> bool:
        return key in self.data


class PickleDbStorage(BaseStorage):
    def __init__(self, filename: set = 'storage.db'):
        self.db = pickledb.load(filename, auto_dump=True)

    def get(self, key: str) -> Optional[Any]:
        return self.db.get(key)

    def set(self, key: str, value: Any):
        self.db.set(key, value)

    def contains_key(self, key: str) -> bool:
        return self.db.exists(key)


class Memory(BotComponent):
    def __init__(self, storage: BaseStorage):
        self.storage = storage

    async def init(self, context: BotContext):
        context.template_env.globals['has_memory'] = self.storage.contains_key
        context.template_env.globals['set_memory'] = self.storage.set
        context.template_env.globals['get_memory'] = self.storage.get

    def save_global_var(self, key: str, value: str):
        async def _fn(context: Context):
            nonlocal self
            self.storage.set(
                key=context.render_template(key),
                value=context.render_template(value)
            )
            return True
        return _fn

    def check_global_var_exists(self, key: str):
        async def _fn(context: Context):
            nonlocal self
            return self.storage.contains_key(context.render_template(key))
        return _fn

    def set_user_var(self, key: str, value: str):
        async def _fn(context: Context):
            nonlocal self
            self.storage.set(
                key=context.render_template(f'{context.author.member.id}-{key}'),
                value=context.render_template(value)
            )
            return True

        return _fn

    def check_user_var_exists(self, key: str):
        async def _fn(context: Context):
            nonlocal self
            return self.storage.contains_key(f'{context.author.member.id}-{key}')
        return _fn

    def copy_user_var_to_local(self, key: str, target_var: str):
        async def _fn(context: Context):
            nonlocal self
            user_key = f'{context.author.member.id}-{key}'
            if self.storage.contains_key(user_key):
                context.local[target_var] = self.storage.get(user_key)
            return True
        return _fn
