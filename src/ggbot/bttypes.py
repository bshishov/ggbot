from typing import Generic, TypeVar, Union, Dict, List, Any, Callable, Type, Literal
from abc import ABCMeta, abstractmethod
from decimal import Decimal
from inspect import signature, isclass

__all__ = [
    "IType",
    "TInternal",
    "Serializable",
    "NUMBER",
    "STRING",
    "NULL_TYPE",
    "ONEOF",
    "ARRAY",
    "MAP",
    "STRUCT",
    "BOOLEAN",
    "ANY",
    "make_struct_from_python_type",
]

TInternal = TypeVar("TInternal")
Serializable = Union[
    None, str, int, float, Dict[str, "Serializable"], List["Serializable"]
]
InternalNumber = Union[int, float, Decimal]


class IType(Generic[TInternal], metaclass=ABCMeta):
    @abstractmethod
    def get_name(self) -> str:
        ...

    @abstractmethod
    def can_accept(self, other: "IType") -> bool:
        ...

    # @abstractmethod
    # def load(self, value: Serializable) -> TInternal: ...

    # @abstractmethod
    # def dump(self, value: TInternal) -> Serializable: ...

    def __str__(self):
        return self.get_name()


class _NumberType(IType[Decimal]):
    def get_name(self) -> str:
        return "Number"

    def can_accept(self, other: IType) -> bool:
        return isinstance(other, _NumberType)


class _StringType(IType[Decimal]):
    def get_name(self) -> str:
        return "String"

    def can_accept(self, other: IType) -> bool:
        return isinstance(other, _StringType)


class _BooleanType(IType[bool]):
    def get_name(self) -> str:
        return "Bool"

    def can_accept(self, other: IType) -> bool:
        return isinstance(other, _BooleanType)


class _NullType(IType[None]):
    def get_name(self) -> str:
        return "Null"

    def can_accept(self, other: IType) -> bool:
        return isinstance(other, _NullType)


class _AnyType(IType[Any]):
    def get_name(self) -> str:
        return "*"

    def can_accept(self, other: IType) -> bool:
        return True


class _OneOfType(IType):
    __slots__ = "_types"

    def __init__(self, *types: IType):
        self._types = set(types)

    def get_name(self) -> str:
        fmt = ", ".join(t.get_name() for t in self._types)
        return f"OneOf<{fmt}>"

    def can_accept(self, other: IType) -> bool:
        if isinstance(other, _OneOfType):
            return self._types == other._types
        for t in self._types:
            if t.can_accept(other):
                return True
        return False


def _make_oneof(first: IType, *rest: IType) -> _OneOfType:
    # TODO: FLATTEN
    return _OneOfType(first, *rest)


class _ArrayType(IType):
    __slots__ = "_item_type"

    def __init__(self, item_type: IType):
        self._item_type = item_type

    def get_item_type(self) -> IType:
        return self._item_type

    def get_name(self) -> str:
        return f"Array<{self._item_type.get_name()}>"

    def can_accept(self, other: "IType") -> bool:
        if isinstance(other, _ArrayType):
            return self._item_type.can_accept(other._item_type)
        return False


class _MapType(IType):
    __slots__ = "_k_type", "_v_type"

    def __init__(self, key_type: IType, value_type: IType):
        self._k_type = key_type
        self._v_type = value_type

    def get_name(self) -> str:
        return f"Map<{self._k_type.get_name()}, {self._v_type.get_name()}>"

    def get_key_type(self) -> IType:
        return self._k_type

    def get_value_type(self) -> IType:
        return self._v_type

    def can_accept(self, other: "IType") -> bool:
        if isinstance(other, _MapType):
            return self._k_type.can_accept(other._k_type) and self._v_type.can_accept(
                other._v_type
            )
        return False


class _StructType(IType):
    __slots__ = "_name", "_attributes"

    def __init__(self, __struct_name: str, **attributes: IType):
        self._name = __struct_name
        self._attributes = attributes

    def get_name(self) -> str:
        return self._name

    def get_attr_type(self, attr: str) -> IType:
        return self._attributes[attr]

    def can_accept(self, other: "IType") -> bool:
        if isinstance(other, _StructType):
            return self._name == other._name and self._attributes == other._attributes
        return False

    def __str__(self):
        return self.get_name()


NUMBER = _NumberType()
STRING = _StringType()
NULL_TYPE = _NullType()
BOOLEAN = _BooleanType()
ANY = _AnyType()
ONEOF = _make_oneof
ARRAY = _ArrayType
MAP = _MapType
STRUCT = _StructType


def _resolve_type_from_py_annotation(annotation) -> IType:
    if annotation == str:
        return STRING
    elif annotation in {int, float, Decimal}:
        return NUMBER
    elif annotation == bool:
        return BOOLEAN
    elif annotation is type(None):
        return NULL_TYPE

    origin = getattr(annotation, "__origin__", None)
    args = getattr(annotation, "__args__", ())

    if origin is not None:
        if origin == Literal and len(args) == 1:
            return _resolve_type_from_py_annotation(type(args[0]))

        args = [_resolve_type_from_py_annotation(a) for a in args]

        if origin == list and len(args) == 1:
            return ARRAY(args[0])
        if origin == Union and len(args) > 0:
            return ONEOF(*args)
        if origin == dict and len(args) == 2:
            return MAP(args[0], args[1])

    if isclass(annotation):
        return make_struct_from_python_type(annotation)

    raise TypeError(f"Cannot convert annotation {annotation} to type")


def make_struct_from_python_type(tp: Type) -> STRUCT:
    attrs = {}
    for param_name, param in signature(tp).parameters.items():
        attrs[param_name] = _resolve_type_from_py_annotation(param.annotation)
    return STRUCT("PY:" + tp.__name__, **attrs)


def _test():
    assert NUMBER.can_accept(NUMBER)
    assert STRING.can_accept(STRING)
    assert NULL_TYPE.can_accept(NULL_TYPE)

    assert not NUMBER.can_accept(NULL_TYPE)
    assert not NUMBER.can_accept(STRING)

    assert not STRING.can_accept(NULL_TYPE)
    assert not STRING.can_accept(NUMBER)

    assert not NULL_TYPE.can_accept(STRING)
    assert not NULL_TYPE.can_accept(NUMBER)

    # Unions
    optional_numeric = ONEOF(NUMBER, NULL_TYPE)
    assert optional_numeric.can_accept(NUMBER)
    assert optional_numeric.can_accept(NULL_TYPE)
    assert optional_numeric.can_accept(optional_numeric)
    assert not optional_numeric.can_accept(STRING)

    numeric_or_string = ONEOF(NUMBER, STRING)
    assert numeric_or_string.can_accept(numeric_or_string)
    assert numeric_or_string.can_accept(NUMBER)
    assert numeric_or_string.can_accept(STRING)
    assert not numeric_or_string.can_accept(NULL_TYPE)
    assert not numeric_or_string.can_accept(optional_numeric)

    # Array
    array_of_numbers = ARRAY(NUMBER)
    assert array_of_numbers.can_accept(array_of_numbers)
    assert not array_of_numbers.can_accept(ARRAY(STRING))
    assert not array_of_numbers.can_accept(NULL_TYPE)

    # Covariance
    array_of_optional_strings = ARRAY(ONEOF(NULL_TYPE, STRING))
    assert array_of_optional_strings.can_accept(ARRAY(NULL_TYPE))
    assert array_of_optional_strings.can_accept(ARRAY(STRING))
    assert array_of_optional_strings.can_accept(array_of_optional_strings)

    # Any
    assert ANY.can_accept(NUMBER)
    assert ANY.can_accept(NULL_TYPE)
    assert ANY.can_accept(STRING)
    assert ANY.can_accept(array_of_optional_strings)
    assert ANY.can_accept(array_of_numbers)
    assert ANY.can_accept(numeric_or_string)
    assert ANY.can_accept(optional_numeric)

    # Structs
    class A:
        def __init__(self, a: str, b: Dict[str, Union[str, int]]):
            self.a = a
            self.b = b

    s = make_struct_from_python_type(A)

    assert s.get_attr_type("a").can_accept(STRING)
    assert s.get_attr_type("b").can_accept(MAP(STRING, NUMBER))
    print(s.get_name())


if __name__ == "__main__":
    _test()
