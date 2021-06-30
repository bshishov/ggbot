from typing import Dict, Union, TypeVar, Optional, List

from attr import dataclass

from ggbot.bttypes import *
from ggbot.context import Context, IVariable, IValue


__all__ = [
    'Attr',
    'Const',
    'NULL',
    'TRUE',
    'FALSE',
    'StringDictionary',
    'Template',
    'AsString',
    'Formatted',
    'SlotValue',
    'NumberSlotValue',
    'Fallback',
    'set_var_from',
    'Divided',
    'Rounded',
    'Filtered',
    'Select',
    'JoinedString'
]


TVar = TypeVar('TVar')
T = TypeVar('T')
TResult = TypeVar('TResult')


class Const(IValue[TInternal]):
    def __init__(self, tp: IType, value: TInternal):
        self._type = tp
        self._value = value

    def evaluate(self, ctx) -> TInternal:
        return self._value

    def get_return_type(self) -> IType:
        return self._type


NULL = Const(NULL_TYPE, None)
TRUE = Const(BOOLEAN, True)
FALSE = Const(BOOLEAN, False)


@dataclass(frozen=True)
class Attr(IValue):
    object: IValue
    attr: str

    def __attrs_post_init__(self):
        obj = self.object.get_return_type()
        assert isinstance(obj, STRUCT), f'Struct type expected, got {obj}'
        assert obj.get_attr_type(self.attr)

    def evaluate(self, context: Context):
        return getattr(self.object.evaluate(context), self.attr)

    def get_return_type(self) -> IType:
        obj = self.object.get_return_type()
        assert isinstance(obj, STRUCT)
        return obj.get_attr_type(self.attr)


@dataclass(frozen=True)
class StringDictionary(IValue[Dict[str, str]]):
    value: Dict[str, IValue[str]]

    def __attrs_post_init__(self):
        for value in self.value.values():
            assert STRING.can_accept(value.get_return_type())

    def evaluate(self, context: Context) -> Dict[str, str]:
        return {k: v.evaluate(context) for k, v in self.value.items()}

    def get_return_type(self) -> IType:
        return MAP(STRING, STRING)


@dataclass(frozen=True)
class Template(IValue[str]):
    template: str
    resolve_emoji: bool = True

    def evaluate(self, context: Context) -> str:
        return context.render_template(self.template, resolve_emoji=self.resolve_emoji)

    def get_return_type(self) -> IType:
        return STRING


@dataclass(frozen=True)
class AsString(IValue[str]):
    value: IValue

    def evaluate(self, context: Context) -> str:
        return str(self.value.evaluate(context))

    def get_return_type(self) -> IType:
        return STRING


class Formatted(IValue[str]):
    def __init__(self, template: str, **kwargs: IValue[str]):
        self.template = template
        self.kwargs = kwargs
        fake_kwargs = {k: 'foo' for k, v in self.kwargs.items()}
        assert self.template.format(**fake_kwargs), f'Error in string format {self.template}'

    def evaluate(self, context: Context) -> str:
        kwargs = {k: v.evaluate(context) for k, v in self.kwargs.items()}
        return self.template.format(**kwargs)

    def get_return_type(self) -> IType:
        return STRING


@dataclass(frozen=True)
class SlotValue(IValue[str]):
    slot_name: str

    def evaluate(self, context: Context) -> str:
        return context.match.get_slot_value(self.slot_name)

    def get_return_type(self) -> IType:
        return STRING


@dataclass(frozen=True)
class NumberSlotValue(IValue[int]):
    slot_name: str

    def evaluate(self, context: Context) -> int:
        value = context.match.get_slot_value(self.slot_name)
        assert isinstance(value, int)
        return value

    def get_return_type(self) -> IType:
        return NUMBER


class Fallback(IValue):
    def __init__(
            self,
            tp: IType,
            value: IValue[Optional[TVar]],
            fallback_value: IValue[TVar]
    ):
        assert ONEOF(tp, NULL_TYPE).can_accept(value.get_return_type())
        assert tp.can_accept(fallback_value.get_return_type())
        self.tp = tp
        self.value = value
        self.fallback_value = fallback_value

    def evaluate(self, ctx):
        value = self.value.evaluate(ctx)
        if value is not None:
            return value
        return self.fallback_value.evaluate(ctx)

    def get_return_type(self) -> IType:
        return self.tp


def set_var_from(var: IVariable[TVar], value: IValue[TVar]):
    expected_type = ONEOF(NULL_TYPE, var.get_return_type())
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
        assert NUMBER.can_accept(self.a.get_return_type())
        assert NUMBER.can_accept(self.b.get_return_type())

    def evaluate(self, context: Context) -> float:
        return self.a.evaluate(context) / self.b.evaluate(context)

    def get_return_type(self) -> IType:
        return NUMBER


@dataclass(frozen=True)
class Rounded(IValue[int]):
    a: Union[IValue[float]]

    def __attrs_post_init__(self):
        assert NUMBER.can_accept(self.a.get_return_type())

    def evaluate(self, context: Context) -> int:
        return round(self.a.evaluate(context))

    def get_return_type(self) -> IType:
        return NUMBER


@dataclass
class Filtered(IValue[List[T]]):
    collection: IValue[List[T]]
    x: IVariable[T]  # local var
    fn: IValue[T]

    def __attrs_post_init__(self):
        assert self.collection.get_return_type().can_accept(ARRAY(self.x.get_return_type()))
        assert BOOLEAN.can_accept(self.fn.get_return_type())

    def evaluate(self, context: Context) -> List[T]:
        result = []
        for item in self.collection.evaluate(context):
            context.set_variable(self.x, item)  # VIOLATES PURE FUNCTIONS!
            if self.fn.evaluate(context):
                result.append(item)
        return result

    def get_return_type(self) -> IType:
        return ARRAY(self.x.get_return_type())


@dataclass
class Select(IValue[List[TResult]]):
    collection: IValue[List[T]]
    x: IVariable[T]  # local var
    fn: IValue[TResult]

    def __attrs_post_init__(self):
        assert self.collection.get_return_type().can_accept(ARRAY(self.x.get_return_type()))

    def evaluate(self, context: Context) -> List[TResult]:
        result = []
        for item in self.collection.evaluate(context):
            context.set_variable(self.x, item)  # VIOLATES PURE FUNCTIONS!
            result.append(self.fn.evaluate(context))
        return result

    def get_return_type(self) -> IType:
        return ARRAY(self.fn.get_return_type())


@dataclass
class JoinedString(IValue[str]):
    join_by: str
    collection: IValue[List[str]]

    def __attrs_post_init__(self):
        assert ARRAY(STRING).can_accept(self.collection.get_return_type())

    def evaluate(self, context: Context) -> str:
        items = self.collection.evaluate(context)
        return self.join_by.join(items)

    def get_return_type(self) -> IType:
        return STRING
