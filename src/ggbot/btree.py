from typing import Callable, Awaitable, TypeVar, Dict, Union
import asyncio
import random
import logging

from jinja2 import Template

from ggbot.bt.abc import Context, IExpression, IVariable
from ggbot.bttypes import *


__all__ = [
    "Action",
    "sequence",
    "selector",
    "always_fail",
    "always_success",
    "set_var",
    "ensure_var",
    "check_condition",
    "retry_until_success",
    "repeat_until_timer_expires",
    "inverter",
    "no_longer_than",
    "random_one_of",
    "do_action",
    "do_print",
    "ask_input",
    "wait_time",
    "log",
    "log_value",
    "set_value_in_map",
]

_logger = logging.getLogger(__name__)
Action = Callable[[Context], Awaitable[bool]]


def sequence(*child: Action) -> Action:
    async def _fn(ctx: Context):
        for f in child:
            res = await f(ctx)
            if not res:
                return False
        return True

    return _fn


def selector(*child: Action) -> Action:
    async def _fn(ctx: Context):
        for f in child:
            res = await f(ctx)
            if res:
                return True
        return False

    return _fn


def always_fail(child: Action) -> Action:
    async def _fn(ctx: Context):
        await child(ctx)
        return False

    return _fn


def always_success(child: Action) -> Action:
    async def _fn(ctx: Context):
        await child(ctx)
        return True

    return _fn


def set_var(var: str, value) -> Action:
    async def _fn(ctx: Context):
        ctx.local[var] = ctx.render_template(value)
        return True

    return _fn


def ensure_var(var: str) -> Action:
    async def _fn(ctx: Context):
        value = ctx.local.get(var)
        return bool(value)

    return _fn


def check_condition(condition: Union[str, Template]) -> Action:
    async def _fn(ctx: Context):
        return bool(ctx.render_template(condition))

    return _fn


def retry_until_success(times: int, child: Action) -> Action:
    async def _fn(ctx: Context):
        for i in range(times):
            res = await child(ctx)
            if res:
                return True
        return False

    return _fn


async def _repeat_until_failure(action: Action, ctx: Context):
    while True:
        result = await action(ctx)
        if not result:
            return False


async def _wait_then_succeed(seconds: float):
    await asyncio.sleep(seconds)
    return True


def repeat_until_timer_expires(seconds: float, action: Action) -> Action:
    async def _fn(ctx: Context):
        try:
            result = await asyncio.wait_for(
                _repeat_until_failure(action, ctx), timeout=seconds
            )
            return result
        except asyncio.TimeoutError:
            return True

    return _fn


def inverter(child: Action) -> Action:
    async def _fn(ctx: Context):
        res = await child(ctx)
        return not res

    return _fn


def no_longer_than(seconds: float, child: Action):
    async def _fn(ctx: Context):
        try:
            res = await asyncio.wait_for(child(ctx), timeout=seconds)
            return res
        except TimeoutError:
            return False

    return _fn


def random_one_of(*child: Action) -> Action:
    options = list(child)

    async def _fn(ctx: Context):
        if not options:
            return True

        option = random.choice(options)
        return await option(ctx)

    return _fn


def do_action(fn: Callable[[Context], None]) -> Action:
    async def _fn(ctx: Context):
        fn(ctx)
        return True

    return _fn


def do_print(value) -> Action:
    async def _fn(ctx: Context):
        print(ctx.render_template(value))
        return True

    return _fn


def ask_input(to: str = "input") -> Action:
    async def _fn(ctx: Context):
        value = input("> ").strip()
        if value:
            ctx.local[to] = value
            return True
        return False

    return _fn


def wait_time(seconds: float):
    async def _fn(context: Context):
        await asyncio.sleep(seconds)
        return True

    return _fn


def log(message: str):
    async def _fn(context: Context):
        _logger.info(message)
        return True

    return _fn


def log_value(value: IExpression[str]):
    async def _fn(context: Context):
        _logger.info(value.evaluate(context))
        return True

    return _fn


TKey = TypeVar("TKey")
TValue = TypeVar("TValue")


def set_value_in_map(
    var: IVariable[Dict[TKey, TValue]], key: IExpression[TKey], value: IExpression[TValue]
) -> Action:
    assert var.get_return_type().can_accept(
        MAP(key.get_return_type(), value.get_return_type())
    )

    async def _fn(ctx: Context):
        m = ctx.get_var_value(var)
        v_key = key.evaluate(ctx)
        v_value = value.evaluate(ctx)
        m[v_key] = v_value
        ctx.set_variable(var, m)
        return True

    return _fn
