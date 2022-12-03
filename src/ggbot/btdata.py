from typing import Dict, Union, TypeVar, Optional, List, Callable, Any, Generic
import random

from attr import dataclass

from ggbot.bttypes import *
from ggbot.context import Context, IVariable, IExpression


__all__ = [
    "Attr",
    "Const",
    "Factory",
    "NULL",
    "TRUE",
    "FALSE",
    "StringDictionary",
    "Item",
    "Template",
    "AsString",
    "Formatted",
    "SlotExpression",
    "NumberSlotExpression",
    "Fallback",
    "set_var_from",
    "Divided",
    "Sum",
    "Rounded",
    "Filtered",
    "SelectFromArray",
    "SelectFromMap",
    "JoinedString",
    "RandomElementOf",
]


TVar = TypeVar("TVar")
T = TypeVar("T")
TResult = TypeVar("TResult")


@dataclass(slots=True, frozen=True)
class Const(IExpression[T]):
    _type: IType
    _value: T

    def evaluate(self, ctx) -> T:
        return self._value

    def get_return_type(self) -> IType:
        return self._type


@dataclass(slots=True, frozen=True)
class Factory(IExpression[T]):
    _type: IType
    _value: Callable[[], T]

    def evaluate(self, ctx) -> T:
        return self._value()

    def get_return_type(self) -> IType:
        return self._type


NULL = Const(NULL_TYPE, None)
TRUE = Const(BOOLEAN, True)
FALSE = Const(BOOLEAN, False)


@dataclass(slots=True, frozen=True)
class Attr(IExpression[Any]):
    object: IExpression
    attr: str

    def __attrs_post_init__(self) -> None:
        obj = self.object.get_return_type()
        assert isinstance(obj, STRUCT), f"Struct type expected, got {obj}"
        assert obj.get_attr_type(self.attr)

    def evaluate(self, context: Context) -> Any:
        return getattr(self.object.evaluate(context), self.attr)

    def get_return_type(self) -> IType:
        obj = self.object.get_return_type()
        assert isinstance(obj, STRUCT)
        return obj.get_attr_type(self.attr)


@dataclass(slots=True, frozen=True)
class StringDictionary(IExpression[Dict[str, str]]):
    value: Dict[str, IExpression[str]]

    def __attrs_post_init__(self):
        for value in self.value.values():
            assert STRING.can_accept(value.get_return_type())

    def evaluate(self, context: Context) -> Dict[str, str]:
        return {k: v.evaluate(context) for k, v in self.value.items()}

    def get_return_type(self) -> IType:
        return MAP(STRING, STRING)


@dataclass(slots=True, frozen=True)
class Item(IExpression[Optional[TVar]]):
    map: IExpression[Dict[str, TVar]]
    key: IExpression[str]

    def __attrs_post_init__(self):
        map_type = self.map.get_return_type()
        assert isinstance(map_type, MAP)
        map_type.get_key_type().can_accept(self.key.get_return_type())

    def evaluate(self, context: Context) -> Optional[TVar]:
        v_map = self.map.evaluate(context)
        v_key = self.key.evaluate(context)
        return v_map.get(v_key)

    def get_return_type(self) -> IType:
        map_type = self.map.get_return_type()
        assert isinstance(map_type, MAP)
        return ONEOF(map_type.get_value_type(), NULL_TYPE)


@dataclass(slots=True, frozen=True)
class Template(IExpression[str]):
    template: str
    resolve_emoji: bool = True

    def evaluate(self, context: Context) -> str:
        return context.render_template(self.template, resolve_emoji=self.resolve_emoji)

    def get_return_type(self) -> IType:
        return STRING


@dataclass(slots=True, frozen=True)
class AsString(IExpression[str]):
    value: IExpression

    def evaluate(self, context: Context) -> str:
        return str(self.value.evaluate(context))

    def get_return_type(self) -> IType:
        return STRING


class Formatted(IExpression[str]):
    def __init__(self, template: str, **kwargs: IExpression[Any]):
        self.template = template
        self.kwargs = kwargs
        fake_kwargs = {k: "foo" for k, v in self.kwargs.items()}
        assert self.template.format(
            **fake_kwargs
        ), f"Error in string format {self.template}"

    def evaluate(self, context: Context) -> str:
        kwargs = {k: v.evaluate(context) for k, v in self.kwargs.items()}
        return self.template.format(**kwargs)

    def get_return_type(self) -> IType:
        return STRING


@dataclass(frozen=True)
class SlotExpression(IExpression[str]):
    slot_name: str

    def evaluate(self, context: Context) -> str:
        return context.match.get_slot_value(self.slot_name)

    def get_return_type(self) -> IType:
        return STRING


@dataclass(frozen=True)
class NumberSlotExpression(IExpression[int]):
    slot_name: str

    def evaluate(self, context: Context) -> int:
        value = context.match.get_slot_value(self.slot_name)
        assert isinstance(value, int)
        return value

    def get_return_type(self) -> IType:
        return NUMBER


class Fallback(IExpression):
    def __init__(
        self, tp: IType, value: IExpression[Optional[TVar]], fallback_value: IExpression[TVar]
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


def set_var_from(var: IVariable[TVar], value: IExpression[TVar]):
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
class Divided(IExpression[float]):
    a: Union[IExpression[float], IExpression[int]]
    b: Union[IExpression[float], IExpression[int]]

    def __attrs_post_init__(self):
        assert NUMBER.can_accept(self.a.get_return_type())
        assert NUMBER.can_accept(self.b.get_return_type())

    def evaluate(self, context: Context) -> float:
        return self.a.evaluate(context) / self.b.evaluate(context)

    def get_return_type(self) -> IType:
        return NUMBER


@dataclass(frozen=True)
class Sum(IExpression[float]):
    a: Union[IExpression[float], IExpression[int]]
    b: Union[IExpression[float], IExpression[int]]

    def __attrs_post_init__(self):
        assert NUMBER.can_accept(self.a.get_return_type())
        assert NUMBER.can_accept(self.b.get_return_type())

    def evaluate(self, context: Context) -> float:
        return self.a.evaluate(context) + self.b.evaluate(context)

    def get_return_type(self) -> IType:
        return NUMBER


@dataclass(frozen=True)
class Rounded(IExpression[int]):
    a: Union[IExpression[float]]

    def __attrs_post_init__(self):
        assert NUMBER.can_accept(self.a.get_return_type())

    def evaluate(self, context: Context) -> int:
        return round(self.a.evaluate(context))

    def get_return_type(self) -> IType:
        return NUMBER


@dataclass
class Filtered(IExpression[List[T]]):
    collection: IExpression[List[T]]
    x: IVariable[T]  # local var
    fn: IExpression[T]

    def __attrs_post_init__(self):
        assert self.collection.get_return_type().can_accept(
            ARRAY(self.x.get_return_type())
        )
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
class SelectFromArray(Generic[T, TResult], IExpression[List[TResult]]):
    collection: IExpression[List[T]]
    x: IVariable[T]  # local var
    fn: IExpression[TResult]

    def __attrs_post_init__(self):
        assert self.collection.get_return_type().can_accept(
            ARRAY(self.x.get_return_type())
        )

    def evaluate(self, context: Context) -> List[TResult]:
        result = []
        for item in self.collection.evaluate(context):
            context.set_variable(self.x, item)  # VIOLATES PURE FUNCTIONS!
            result.append(self.fn.evaluate(context))
        return result

    def get_return_type(self) -> IType:
        return ARRAY(self.fn.get_return_type())


@dataclass
class SelectFromMap(Generic[T, TVar, TResult], IExpression[List[TResult]]):
    collection: IExpression[Dict[T, TVar]]
    key: IVariable[T]
    value: IVariable[TVar]
    fn: IExpression[TResult]

    def __attrs_post_init__(self):
        map_type = MAP(self.key.get_return_type(), self.value.get_return_type())
        assert self.collection.get_return_type().can_accept(map_type)

    def evaluate(self, context: Context) -> List[TResult]:
        result = []
        for k, v in self.collection.evaluate(context).items():
            context.set_variable(self.key, k)  # VIOLATES PURE FUNCTIONS!
            context.set_variable(self.value, v)  # VIOLATES PURE FUNCTIONS!
            result.append(self.fn.evaluate(context))
        return result

    def get_return_type(self) -> IType:
        return ARRAY(self.fn.get_return_type())


@dataclass
class JoinedString(IExpression[str]):
    join_by: str
    collection: IExpression[List[str]]

    def __attrs_post_init__(self):
        assert ARRAY(STRING).can_accept(self.collection.get_return_type())

    def evaluate(self, context: Context) -> str:
        items = self.collection.evaluate(context)
        return self.join_by.join(items)

    def get_return_type(self) -> IType:
        return STRING


@dataclass
class RandomElementOf(IExpression[Optional[TVar]]):
    collection: IExpression[List[TVar]]

    def __attrs_post_init__(self):
        assert isinstance(self.collection.get_return_type(), ARRAY)

    def evaluate(self, context: Context) -> Optional[TVar]:
        collection = self.collection.evaluate(context)
        if len(collection) > 0:
            return random.choice(collection)
        return None

    def get_return_type(self) -> IType:
        collection_type = self.collection.get_return_type()
        assert isinstance(collection_type, ARRAY)
        return ONEOF(NULL_TYPE, collection_type.get_item_type())
