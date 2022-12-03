from typing import Union, Dict

from ggbot.bttypes import *


def test_types():
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
