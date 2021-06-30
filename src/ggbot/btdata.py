from typing import Dict, Union, TypeVar, Optional

from attr import dataclass

from ggbot import bttypes as types
from ggbot.context import Context, IVariable, IValue


__all__ = [
    'Attr',
    'Const',
    'NULL',
    'StringDictionary',
    'Template',
    'AsString',
    'Formatted',
    'SlotValue',
    'Fallback',
    'set_var_from',
    'Divided',
    'Rounded',
]


class Const(IValue[types.TInternal]):
    def __init__(self, tp: types.IType, value: types.TInternal):
        self._type = tp
        self._value = value

    def evaluate(self, ctx) -> types.TInternal:
        return self._value

    def get_return_type(self) -> types.IType:
        return self._type


NULL = Const(types.NULL_TYPE, None)


@dataclass(frozen=True)
class Attr(IValue):
    object: IValue
    attr: str

    def __attrs_post_init__(self):
        obj = self.object.get_return_type()
        assert isinstance(obj, types.STRUCT), f'Struct type expected, got {obj}'
        assert obj.get_attr_type(self.attr)

    def evaluate(self, context: Context):
        return getattr(self.object.evaluate(context), self.attr)

    def get_return_type(self) -> types.IType:
        obj = self.object.get_return_type()
        assert isinstance(obj, types.STRUCT)
        return obj.get_attr_type(self.attr)


@dataclass(frozen=True)
class StringDictionary(IValue[Dict[str, str]]):
    value: Dict[str, IValue[str]]

    def __attrs_post_init__(self):
        for value in self.value.values():
            assert types.STRING.can_accept(value.get_return_type())

    def evaluate(self, context: Context) -> Dict[str, str]:
        return {k: v.evaluate(context) for k, v in self.value.items()}

    def get_return_type(self) -> types.IType:
        return types.MAP(types.STRING, types.STRING)


@dataclass(frozen=True)
class Template(IValue[str]):
    template: str
    resolve_emoji: bool = True

    def evaluate(self, context: Context) -> str:
        return context.render_template(self.template, resolve_emoji=self.resolve_emoji)

    def get_return_type(self) -> types.IType:
        return types.STRING


@dataclass(frozen=True)
class AsString(IValue[str]):
    value: IValue

    def evaluate(self, context: Context) -> str:
        return str(self.value.evaluate(context))

    def get_return_type(self) -> types.IType:
        return types.STRING


class Formatted(IValue[str]):
    def __init__(self, template: str, **kwargs: IValue[str]):
        self.template = template
        self.kwargs = kwargs
        fake_kwargs = {k: 'foo' for k, v in self.kwargs.items()}
        assert self.template.format(**fake_kwargs), f'Error in string format {self.template}'

    def evaluate(self, context: Context) -> str:
        kwargs = {k: v.evaluate(context) for k, v in self.kwargs.items()}
        return self.template.format(**kwargs)

    def get_return_type(self) -> types.IType:
        return types.STRING


@dataclass(frozen=True)
class SlotValue(IValue[str]):
    slot_name: str

    def evaluate(self, context: Context) -> str:
        return context.match.get_slot_value(self.slot_name)

    def get_return_type(self) -> types.IType:
        return types.STRING


TVar = TypeVar('TVar')


class Fallback(IValue):
    def __init__(
            self,
            tp: types.IType,
            value: IValue[Optional[TVar]],
            fallback_value: IValue[TVar]
    ):
        assert types.ONEOF(tp, types.NULL_TYPE).can_accept(value.get_return_type())
        assert tp.can_accept(fallback_value.get_return_type())
        self.tp = tp
        self.value = value
        self.fallback_value = fallback_value

    def evaluate(self, ctx):
        value = self.value.evaluate(ctx)
        if value is not None:
            return value
        return self.fallback_value.evaluate(ctx)

    def get_return_type(self) -> types.IType:
        return self.tp


def set_var_from(var: IVariable[TVar], value: IValue[TVar]):
    expected_type = types.ONEOF(types.NULL_TYPE, var.get_return_type())
    assert expected_type.can_accept(value.get_return_type())

    async def _fn(context: Context):
        result = value.evaluate(context)
        if result is None:
            return False
        context.set_variable(var, result)
        return True
    return _fn


@dataclass(frozen=True)
class Divided(IValue[float]):
    a: Union[IValue[float], IValue[int]]
    b: Union[IValue[float], IValue[int]]

    def __attrs_post_init__(self):
        assert types.NUMBER.can_accept(self.a.get_return_type())
        assert types.NUMBER.can_accept(self.b.get_return_type())

    def evaluate(self, context: Context) -> float:
        return self.a.evaluate(context) / self.b.evaluate(context)

    def get_return_type(self) -> types.IType:
        return types.NUMBER


@dataclass(frozen=True)
class Rounded(IValue[int]):
    a: Union[IValue[float]]

    def __attrs_post_init__(self):
        assert types.NUMBER.can_accept(self.a.get_return_type())

    def evaluate(self, context: Context) -> int:
        return round(self.a.evaluate(context))

    def get_return_type(self) -> types.IType:
        return types.NUMBER
