from typing import List, TypeVar, Union

from attr import dataclass

from ggbot.btdata import *
from ggbot.bttypes import *
from ggbot.context import *


T = TypeVar('T')
TResult = TypeVar('TResult')


@dataclass
class GreaterThan(IValue[bool]):
    a: Union[IValue[int], IValue[float]]
    b: Union[IValue[int], IValue[float]]

    def __attrs_post_init__(self):
        assert NUMBER.can_accept(self.a.get_return_type())
        assert NUMBER.can_accept(self.b.get_return_type())

    def evaluate(self, context: Context) -> bool:
        a = self.a.evaluate(context)
        b = self.b.evaluate(context)
        return a > b

    def get_return_type(self) -> IType:
        return BOOLEAN


@dataclass
class Doubled(IValue[Union[int, float]]):
    a: Union[IValue[int], IValue[float]]

    def __attrs_post_init__(self):
        assert NUMBER.can_accept(self.a.get_return_type())

    def evaluate(self, context: Context) -> Union[int, float]:
        a = self.a.evaluate(context)
        return a * 2

    def get_return_type(self) -> IType:
        return NUMBER


def main():
    ctx = Context(None, None, None)

    x = Variable('x', NUMBER)

    array_literal = Const(ARRAY(NUMBER), list(range(10)))

    filtered = Filtered(array_literal, x, GreaterThan(x, Const(NUMBER, 5)))
    doubled = Select(filtered, x, Doubled(x))
    as_string = Select(doubled, x, Formatted("Number: {x}", x=AsString(x)))

    assert filtered.evaluate(ctx) == [6, 7, 8, 9]
    assert doubled.evaluate(ctx) == [12, 14, 16, 18]
    assert as_string.evaluate(ctx) == ["Number: 12", "Number: 14", "Number: 16", "Number: 18"]

    print(filtered.get_return_type())
    print(doubled.get_return_type())
    print(as_string.get_return_type())


if __name__ == '__main__':
    main()
