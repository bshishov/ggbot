from typing import *
import inspect
import sys
from enum import Enum, EnumMeta
from datetime import datetime

from attr import attrs, attrib
from .typing_utils import (
    Annotated,
    ForwardRef,
    eval_type,
    get_origin,
    get_args,
    is_subtype,
    strip_annotated,
)

__all__ = [
    # Common
    'NOT_PROVIDED',
    'dump',
    'load',
    'SerializationOptions',
    'AnyLoadingPolicy',
    'AnyDumpPolicy',
    'MissingAnnotationsPolicy',
    'format_spec_error',

    # Annotations
    'annotate',
    'Annotated',
    'Alias',
    'Getter',
    
    # Converters
    'Converter',
    'ExactConverter',
    'PrimitiveTypeConverter',
    'NoneConverter',
    'AnyConverter',
    'DatetimeTimestampConverter',
    'SetConverter',
    'ListConverter',
    'DictConverter',
    'UnionTypeConverter',
    'TupleConverter',
    'SpecObjectConverter',
    'EnumConverter',

    # Factories
    'ConverterFactory',
    'DiscriminatedConverterFactory',
    'EnumConverterFactory'
]


class _NotProvided:
    def __bool__(self):
        return False

    def __copy__(self):
        return self

    def __deepcopy__(self, _):
        return self

    def __str__(self):
        return "<NOT_PROVIDED>"

    def __repr__(self):
        return "<NOT_PROVIDED>"


NOT_PROVIDED = _NotProvided()


TPrimitive = Union[str, int, float, bool, None]
TSerialized = Union[Dict[TPrimitive, 'TSerialized'], List['TSerialized'], TPrimitive]
T = TypeVar('T')


def _lookup(data: Mapping[str, Any], key: str, aliases: Union[None, str, Iterable[str]]) -> Any:
    if key in data:
        return data[key]
    if aliases is not None:
        if isinstance(aliases, str):
            if aliases in data:
                return data[aliases]
        else:
            for alias in aliases:
                if alias in data:
                    return data[alias]
    return NOT_PROVIDED


def _wrap_error(
        e: Exception,
        message: str,
        key: Optional[str] = None,
        converter: Optional['Converter'] = None
) -> Exception:
    inner = getattr(e, 'spec', {
            'message': e,
            'inner': None
        }
    )
    setattr(e, 'spec', {
        'message': message,
        'key': key,
        'converter': converter.__class__.__qualname__ if converter else None,
        'inner': inner
    })
    return e


def exception_to_str(exception: Union[str, Exception], indent: int = 0) -> str:
    if isinstance(exception, str):
        return exception

    if hasattr(exception, "format_error"):
        return exception.format_error(indent=indent)

    return str(exception)


def format_spec_error(e: Exception) -> str:
    if not hasattr(e, 'spec'):
        return exception_to_str(e)

    def _fmt(err: Dict[str, Any], _indent: int):
        inner = err.get('inner')
        key = err.get('key')
        if inner:
            inner_fmt = _fmt(inner, _indent + 1)
        else:
            inner_fmt = ''

        if key:
            msg = f'{key}: {exception_to_str(err["message"], _indent)}\n'
        else:
            msg = f'{exception_to_str(err["message"], _indent)}\n'

        return ''.join((
            '\t' * _indent,
            msg,
            inner_fmt
        ))

    return _fmt(e.spec, 0)


def annotate(attr: str, *annotations, init=True):
    """Annotates arguments of a callable with `annotations`.
    Annotation is based on special Annotated type-hint, introduced in PEP-593.
    Annotated was first introduced in python 3.9. In older version (3.6+) it is available
    via backported version in typing_extensions.

    This decorator allows usage of Annotated type-hints in older versions. Please use
    true Annotated if possible.

    If the decorator is used against class - an __init__ method would be annotated
    """

    def _annotate(o):
        o = inspect.unwrap(o)
        hints = getattr(o, '__annotations__', {})
        hints[attr] = Annotated[(hints.get(attr, Any), *annotations)]
        o.__annotations__ = hints

    def _decorator(fn_or_cls):
        _annotate(fn_or_cls)
        if isinstance(fn_or_cls, type) and init:
            _annotate(fn_or_cls.__init__)
        return fn_or_cls
    return _decorator


class AnyLoadingPolicy(Enum):
    RAISE_ERROR = 0
    LOAD_AS_IS = 1


class AnyDumpPolicy(Enum):
    RAISE_ERROR = 0
    DUMP_AS_IS = 1


class MissingAnnotationsPolicy(Enum):
    RAISE_ERROR = 0
    USE_ANY = 1
    FROM_DEFAULT = 2


@attrs(auto_attribs=True, slots=True, hash=True)
class Alias:
    """Specifies an addition key in data dictionary to get if original attr-name is not
    present is data. Multiple Alias allowed
    """
    alias: str
    deprecated: Union[bool, str] = False


@attrs(auto_attribs=True, slots=True, hash=True)
class Getter:
    attr_or_getter: Union[str, Callable[[Any], Any]]

    def __attrs_post_init__(self):
        if isinstance(self.attr_or_getter, str):
            attr_name = self.attr_or_getter
            self.attr_or_getter = lambda o: getattr(o, attr_name)

    def get_value(self, obj):
        return self.attr_or_getter(obj)


class InjectKey:
    pass


@attrs(auto_attribs=True, slots=True, hash=True)
class Extras:
    allow: Optional[Set] = None
    deny: Optional[Set] = None

    def __attrs_post_init__(self):
        if self.allow and self.deny:
            raise AttributeError('Specify "allow" or "deny" attributes, but not both')


class Converter(Generic[T]):
    def dump(self, obj: T, options: 'SerializationOptions') -> TSerialized:
        raise NotImplementedError

    def load(self, data: TSerialized, key, options: 'SerializationOptions') -> T:
        raise NotImplementedError


class ConverterFactory:
    def can_convert(self, typ: Type) -> bool:
        raise NotImplementedError

    def create_converter(self, typ: Type, options: 'SerializationOptions') -> Converter:
        raise NotImplementedError


class Provider(Generic[T]):
    def provide(self, options: 'SerializationOptions') -> T:
        raise NotImplementedError


class ProviderFactory:
    def can_provide(self, typ: Type) -> bool:
        raise NotImplementedError

    def create_provider(self, typ: Type, options: 'SerializationOptions') -> Provider:
        raise NotImplementedError


class ExactConverter(Converter[T]):
    def dump(self, obj: T, options: 'SerializationOptions') -> TSerialized:
        return obj

    def load(self, data: TSerialized, key, options: 'SerializationOptions') -> T:
        return data


class DatetimeTimestampConverter(Converter[datetime]):
    def dump(self, obj: datetime, options: 'SerializationOptions') -> TSerialized:
        return obj.timestamp()

    def load(self, data: TSerialized, key, options: 'SerializationOptions') -> datetime:
        return datetime.fromtimestamp(data)


@attrs(auto_attribs=True, slots=True)
class AttrDefinition:
    name: str
    data_key: str
    aliases: List[str]
    extras: bool
    inject_key: bool
    provider: Optional[Provider]
    converter: Optional[Converter]
    value_getter: Optional[Callable]


def lookup_dict(data, *keys):
    for k in keys:
        if k in data:
            return data[k]
    return NOT_PROVIDED


@attrs(auto_attribs=True, slots=True)
class SpecObjectConverter(Converter[T]):
    attributes: List[AttrDefinition]
    target: Type[T]
    dump_none_values: bool = True

    _data_keys: Set[str] = attrib(factory=set, init=False)
    _extra_attributes: Set[str] = attrib(factory=set, init=False)

    def __attrs_post_init__(self):
        for a in self.attributes:
            self._data_keys.add(a.data_key)
            self._data_keys.update(a.aliases)
            if a.extras:
                self._extra_attributes.add(a.name)

    def load(self, data: TSerialized, key, options: 'SerializationOptions') -> T:
        if data is None:
            raise TypeError('Cannot load a None object')

        kwargs = {}
        for attr in self.attributes:
            raw_value = lookup_dict(data, attr.data_key, *attr.aliases)
            if raw_value is not NOT_PROVIDED and attr.converter:
                try:
                    value = attr.converter.load(raw_value, attr.name, options)
                except TypeError as e:
                    raise _wrap_error(e, message=f'Failed to load {self.target}',
                                      converter=attr.converter, key=key)
            elif attr.provider:
                value = attr.provider.provide(options)
            elif attr.inject_key and key is not NOT_PROVIDED:
                value = key
            else:
                # Can't resolve a value for the attribute, skipping
                # Later a default from ctor call will be used, or a native missing attribute will
                # be raised
                continue
            kwargs[attr.name] = value

        extra_data = {}
        for k, value in data.items():
            if k not in self._data_keys:
                extra_data[k] = value

        for attr_name in self._extra_attributes:
            kwargs[attr_name] = extra_data

        try:
            return self.target(**kwargs)
        except TypeError as e:
            raise _wrap_error(e,
                              message=f"Failed to create instance of {self.target.__qualname__}",
                              key=key)

    def dump(self, obj: T, options: 'SerializationOptions') -> TSerialized:
        if obj is None:
            raise TypeError('Cannot dump a None object')

        data = {}
        for attr in self.attributes:
            if not attr.value_getter and not attr.converter:
                # Unable to get a value for the attribute (might be a load-only attr), skipping
                continue
            value = attr.value_getter(obj)
            if value is NOT_PROVIDED:
                continue
            try:
                raw_value = attr.converter.dump(value, options)
            except TypeError as e:
                raise _wrap_error(e, f'Failed to dump object {obj!r}',
                                  key=attr.name, converter=attr.converter)
            if raw_value is None and not self.dump_none_values:
                continue
            data[attr.data_key] = raw_value
        return data


def build_attr_definition(
        param_name: str,
        param_type: Type,
        options: 'SerializationOptions'
) -> AttrDefinition:
    aliases = set()
    is_extras = False
    inject_key = False
    converter: Optional[Converter] = None
    provider: Optional[Provider] = None
    getter = None

    # Parameter annotations handling
    # Annotated types must have the __metadata__ field
    param_type, annotations = strip_annotated(param_type)
    for annotation in annotations:
        if isinstance(annotation, Alias):
            aliases.add(annotation.alias)
        elif isinstance(annotation, InjectKey):
            inject_key = True
        elif isinstance(annotation, Extras):
            is_extras = True
        elif isinstance(annotation, Getter):
            getter = annotation.get_value

    getter = getter or (lambda o: getattr(o, param_name, NOT_PROVIDED))
    provider = provider or options.get_provider(param_type)

    if not provider:
        converter = converter or options.get_converter(param_type)

    return AttrDefinition(
        name=param_name,
        data_key=param_name,
        aliases=list(aliases),
        extras=is_extras,
        inject_key=inject_key,
        converter=converter,
        provider=provider,
        value_getter=getter
    )


class DiscriminatedConverter(Converter[T]):
    def __init__(
            self,
            converters: List[Tuple[str, Type, Converter]],
            discriminator_key: str = 'type'
    ):
        self.discriminator_key = discriminator_key
        self.load_map = {}
        self.dump_map = {}

        for discriminator_value, typ, converter in converters:
            self.load_map[discriminator_value] = converter
            self.dump_map[typ] = (discriminator_value, converter)

    def dump(self, obj: T, options: 'SerializationOptions') -> TSerialized:
        typ = type(obj)
        try:
            discriminator_value, converter = self.dump_map[typ]
        except KeyError:
            raise TypeError(f'Cannot dump object {obj}. '
                            f'Cant determine discriminator value for type: {typ}')
        data = converter.dump(obj, options)
        data[self.discriminator_key] = discriminator_value
        return data

    def load(self, data: TSerialized, key, options: 'SerializationOptions') -> T:
        if data is None:
            data = {}
        discriminator_value = data.get(self.discriminator_key)
        if discriminator_value not in self.load_map:
            raise TypeError(f'No registered converter found for discriminator '
                            f'{self.discriminator_key}={discriminator_value}')
        converter = self.load_map[discriminator_value]
        return converter.load(data, key, options)


class SpecObjectConverterFactory(ConverterFactory):
    def can_convert(self, typ: Type):
        return inspect.isclass(typ) or inspect.isfunction(typ)

    def create_converter(self, typ: Type[T], options: 'SerializationOptions') -> Converter:
        type_hints = {}
        signature = inspect.signature(typ)
        definitions = []
        for param_name, param in signature.parameters.items():
            param_type = param.annotation
            if param_type is inspect.Parameter.empty:
                param_type = None
            if param_type is None:
                if options.missing_annotations_policy == MissingAnnotationsPolicy.RAISE_ERROR:
                    raise TypeError(f'Missing type annotation for type \'{typ}\' '
                                    f'for parameter \'{param_name}\'')
                elif options.missing_annotations_policy == MissingAnnotationsPolicy.USE_ANY:
                    param_type = Any
                elif (
                    options.missing_annotations_policy == MissingAnnotationsPolicy.FROM_DEFAULT
                    and param.default is not inspect.Parameter.empty
                ):
                    param_type = type(param.default)
                else:
                    raise RuntimeError(f'Invalid MissingAnnotationsPolicy: '
                                       f'{options.missing_annotations_policy}')
            if isinstance(param_type, str):
                param_type = ForwardRef(param_type)

            param_type = eval_type(param_type, globals(), sys.modules[typ.__module__].__dict__)
            type_hints[param_name] = param_type
            definitions.append(build_attr_definition(param_name, param_type, options))

        return SpecObjectConverter(
            attributes=definitions,
            target=typ,
            dump_none_values=options.dump_none_values
        )


@attrs(slots=True, auto_attribs=True)
class DiscriminatedConverterFactory(ConverterFactory):

    discriminator_type_map: Dict[str, Type]
    converter_factory: ConverterFactory = SpecObjectConverterFactory()
    discriminator_key: str = "type"

    def can_convert(self, typ: Type) -> bool:
        return typ in self.discriminator_type_map.values()

    def create_converter(self, typ: Type, options: 'SerializationOptions') -> Converter:
        converters = []
        for discriminator, typ in self.discriminator_type_map.items():
            converter = self.converter_factory.create_converter(typ, options)
            converters.append((discriminator, typ, converter))
        return DiscriminatedConverter(converters, discriminator_key=self.discriminator_key)


class ListConverter(Converter[List[T]]):
    __slots__ = 'item_converter'

    def __init__(self, item_converter: Converter[T]):
        self.item_converter = item_converter

    def dump(self, obj: T, options: 'SerializationOptions') -> TSerialized:
        return [self.item_converter.dump(v, options) for v in obj]

    def load(self, data: TSerialized, key, options: 'SerializationOptions') -> T:
        if data is None:
            raise TypeError('Expected dict, got None')

        def _try_load(value, index):
            try:
                return self.item_converter.load(value, index, options)
            except TypeError as e:
                raise _wrap_error(e,
                                  message=f'Failed to load list element at index "{index}"',
                                  converter=self.item_converter,
                                  key=key)

        return [_try_load(value, index) for index, value in enumerate(data)]


class SetConverter(Converter[List[T]]):
    __slots__ = 'item_converter'

    def __init__(self, item_converter: Converter[T]):
        self.item_converter = item_converter

    def dump(self, obj: T, options: 'SerializationOptions') -> TSerialized:
        return [self.item_converter.dump(v, options) for v in obj]

    def load(self, data: TSerialized, key, options: 'SerializationOptions') -> T:
        return {self.item_converter.load(value, index, options) for index, value in enumerate(data)}


class DictConverter(Converter[Mapping]):
    __slots__ = 'value_converter',

    def __init__(self, value_converter: Converter):
        self.value_converter = value_converter

    def dump(self, obj: T, options: 'SerializationOptions') -> TSerialized:
        return {k: self.value_converter.dump(v, options) for k, v in obj.items()}

    def load(self, data: TSerialized, key, options: 'SerializationOptions') -> T:
        def _try_load(value, k):
            try:
                return self.value_converter.load(value, k, options)
            except TypeError as e:
                raise _wrap_error(e, message=f'Failed to load dict value of key "{k}"',
                                  converter=self.value_converter,
                                  key=key)
        return {k: _try_load(v, k) for k, v in data.items()}


class TupleConverter(Converter):
    __slots__ = 'converters'

    def __init__(self, *converters: Converter):
        self.converters = converters

    def dump(self, obj: Tuple, options: 'SerializationOptions') -> TSerialized:
        return [
            converter.dump(value, options)
            for converter, value
            in zip(self.converters, obj)
        ]

    def load(self, data: TSerialized, key, options: 'SerializationOptions') -> Tuple:
        if len(self.converters) != len(data):
            raise TypeError(f'Expected {len(self.converters)} values in tuple, got {len(data)}')
        return tuple(
            converter.load(value, key=i, options=options)
            for i, (converter, value)
            in enumerate(zip(self.converters, data))
        )


@attrs(auto_attribs=True, slots=True)
class AnyConverter(Converter[Mapping]):
    any_dump_policy: AnyDumpPolicy = AnyDumpPolicy.DUMP_AS_IS
    any_load_policy: AnyLoadingPolicy = AnyLoadingPolicy.LOAD_AS_IS

    def dump(self, obj: T, options: 'SerializationOptions') -> TSerialized:
        if self.any_dump_policy == AnyDumpPolicy.RAISE_ERROR:
            raise TypeError('Cannot dump "Any" type. Make sure you specified types correctly.')
        elif self.any_dump_policy == AnyDumpPolicy.DUMP_AS_IS:
            return obj
        raise RuntimeError(f'Unknown AnyDumpPolicy: {self.any_dump_policy}')
        # Get converter of object at runtime
        # converter = options.get_converter(type(obj))
        # return converter.dump(obj, options)

    def load(self, data: TSerialized, key, options: 'SerializationOptions') -> T:
        if self.any_load_policy == AnyLoadingPolicy.RAISE_ERROR:
            raise TypeError('Cannot load "Any" type. Make sure you specified types correctly.')
        elif self.any_load_policy == AnyLoadingPolicy.LOAD_AS_IS:
            return data
        raise RuntimeError(f'Unknown AnyLoadingPolicy: {self.any_load_policy}')


class ListConverterFactory(ConverterFactory):
    def can_convert(self, typ: Type):
        return is_subtype(typ, Sequence)

    def create_converter(self, typ: Type, options: 'SerializationOptions') -> Converter:
        args = get_args(typ)
        if args:
            item_type = args[0]
            item_converter = options.get_converter(item_type)
            return ListConverter(item_converter)
        raise TypeError(f'Non-generic type expected, got {typ}')


class TupleConverterFactory(ConverterFactory):
    def can_convert(self, typ: Type):
        return is_subtype(typ, Tuple)

    def create_converter(self, typ: Type, options: 'SerializationOptions') -> Converter:
        args = get_args(typ)
        if args:
            converters = []
            for arg in args:
                converters.append(options.get_converter(arg))
            return TupleConverter(*converters)
        raise TypeError(f'Non-generic Tuple expected, got {typ}')


class SetConverterFactory(ConverterFactory):
    def can_convert(self, typ: Type):
        return is_subtype(typ, AbstractSet)

    def create_converter(self, typ: Type, options: 'SerializationOptions') -> Converter:
        args = get_args(typ)
        if args:
            item_type = args[0]
            item_converter = options.get_converter(item_type)
            return SetConverter(item_converter)
        raise TypeError(f'Non-generic type expected, got {typ}')


class DictConverterFactory(ConverterFactory):
    def can_convert(self, typ: Type):
        return is_subtype(typ, Mapping)

    def create_converter(self, typ: Type, options: 'SerializationOptions') -> Converter:
        args = get_args(typ)
        if args:
            value_type = args[1]  # e.g. typing.Dict[str, T]
            value_converter = options.get_converter(value_type)
            return DictConverter(value_converter)
        raise TypeError(f'Non-generic type expected, got {typ}')


class CompositeTypeError(Exception):

    def __init__(self, errors: List[Exception], data: Any, key: str):
        self.errors = errors
        self.data = data
        self.key = key

    def format_error(self, indent: int = 0) -> str:
        error_info = [f'Error union type key is "{self.key}" current type: {type(self.data)}:']
        for e in self.errors:
            error_text = "\t - " * indent + str(e)
            error_info.append(error_text)
        return "\n".join(error_info)

    def __str__(self):
        return self.format_error(1)


class UnionTypeConverter(Converter):
    __slots__ = 'converters',

    def __init__(self, *converters: Converter):
        self.converters = converters

    def dump(self, obj: T, options: 'SerializationOptions') -> TSerialized:
        for converter in self.converters:
            try:
                return converter.dump(obj, options)
            except (AttributeError, TypeError, ValueError):
                pass
        raise TypeError(f'Unable to dump union type: no suitable converter found')

    def load(self, data: TSerialized, key, options: 'SerializationOptions') -> T:
        errors = []
        for converter in self.converters:
            try:
                return converter.load(data, key, options)
            except (AttributeError, TypeError, ValueError, CompositeTypeError) as e:
                errors.append(e)
        raise _wrap_error(
            CompositeTypeError(errors=errors, data=data, key=key),
            message=f'Unable to load union type key, current type: {type(data)}',
            key=key
        )


class UnionTypeConverterFactory(ConverterFactory):
    def can_convert(self, typ: Type):
        return get_origin(typ) == Union

    def create_converter(self, typ: Type, options: 'SerializationOptions') -> Converter:
        args = get_args(typ)
        if args:
            converters = []
            for arg in args:
                converters.append(options.get_converter(arg))
            return UnionTypeConverter(*converters)
        raise TypeError('The type must be a Union with with type arguments')


class EnumConverterFactory(ConverterFactory):
    def can_convert(self, typ: Type) -> bool:
        return isinstance(typ, EnumMeta)

    def create_converter(self, typ: EnumMeta, options: 'SerializationOptions') -> Converter:
        return EnumConverter(typ)


class EnumConverter(Converter):
    __slots__ = 'enum_class'

    def __init__(self, enum_class: EnumMeta):
        self.enum_class = enum_class

    def dump(self, obj: Enum, options: 'SerializationOptions') -> TSerialized:
        return obj.value

    def load(self, data: TSerialized, key, options: 'SerializationOptions'):
        try:
            return self.enum_class(data)
        except ValueError as err:
            raise TypeError(str(err)) from err


class LiteralConverterFactory(ConverterFactory):
    def can_convert(self, typ: Type) -> bool:
        return get_origin(typ) == Literal

    def create_converter(self, typ: EnumMeta, options: 'SerializationOptions') -> Converter:
        value = get_args(typ)[0]
        return LiteralConverter(value)


class LiteralConverter(Converter):
    def __init__(self, value):
        self._value = value

    def dump(self, obj, options: 'SerializationOptions') -> TSerialized:
        return obj

    def load(self, data: TSerialized, key, options: 'SerializationOptions'):
        if data != self._value:
            raise TypeError(f'Invalid literal value: expected {self._value}, got {data}')
        return data


class PrimitiveTypeConverter(Converter):
    __slots__ = 'typ', 'args'

    def __init__(self, typ: Type, *args: Type):
        self.typ = typ
        self.args = args

    def dump(self, obj: T, options: 'SerializationOptions') -> TSerialized:
        return obj

    def load(self, data: TSerialized, key, options: 'SerializationOptions') -> T:
        if not isinstance(data, (self.typ, *self.args)):
            raise TypeError(f"Value must be of type {self.typ} or {self.args}, " 
                            f"got {type(data)} with value {data} for key: {key}")
        return self.typ(data)


class NoneConverter(Converter):
    def dump(self, obj: T, options: 'SerializationOptions') -> TSerialized:
        return obj

    def load(self, data: TSerialized, key, options: 'SerializationOptions') -> T:
        if data is not None:
            raise TypeError(f"Expected a None value, got {data}")
        return None


class BytesConverter(Converter):
    __slots__ = 'encoding',

    def __init__(self, encoding: str = 'utf-8'):
        self.encoding = encoding

    def dump(self, obj: T, options: 'SerializationOptions') -> TSerialized:
        return obj.decode(encoding=self.encoding)

    def load(self, data: TSerialized, key, options: 'SerializationOptions') -> T:
        return bytes(data, encoding=self.encoding)


def default_converters() -> Mapping[Type, Converter]:
    return {
        int: PrimitiveTypeConverter(int, float),
        float: PrimitiveTypeConverter(float, int),
        str: PrimitiveTypeConverter(str, bytes),
        bool: PrimitiveTypeConverter(bool),
        bytes: BytesConverter(),
        type(None): NoneConverter(),
        datetime: DatetimeTimestampConverter(),
        Any: AnyConverter()
    }


def default_dynamic_converters() -> List[ConverterFactory]:
    return [
        TupleConverterFactory(),
        ListConverterFactory(),
        DictConverterFactory(),
        SetConverterFactory(),
        EnumConverterFactory(),
        SpecObjectConverterFactory(),
        UnionTypeConverterFactory(),
        LiteralConverterFactory()
    ]


@attrs(auto_attribs=True)
class _ProxyConverter(Converter):
    typ: Type[T]

    def dump(self, obj: T, options: 'SerializationOptions') -> TSerialized:
        converter = options.converters[self.typ]
        setattr(self, 'dump', converter.dump)
        return converter.dump(obj, options)

    def load(self, data: TSerialized, key, options: 'SerializationOptions') -> T:
        converter = options.converters[self.typ]
        setattr(self, 'load', converter.load)
        return converter.load(data, key, options)


@attrs(auto_attribs=True, slots=True, repr=False)
class SerializationOptions:
    converters: Dict[Type, Converter] = attrib(factory=default_converters)
    converter_factories: List[ConverterFactory] = attrib(factory=default_dynamic_converters)
    providers: Dict[Type, Provider] = attrib(factory=dict)
    provider_factories: List[ProviderFactory] = attrib(factory=list)
    missing_annotations_policy: MissingAnnotationsPolicy = MissingAnnotationsPolicy.RAISE_ERROR
    dump_none_values: bool = True

    # Типы конвертеров которые резолвятся в рамках вызова get_converter
    # необходимо для решения циклических импортов
    _request_stack: Set[Type] = attrib(factory=set)

    def get_converter(self, typ: Type[T]) -> Converter[T]:
        converter = self.converters.get(typ)

        if converter:
            return converter

        if typ in self._request_stack:
            # Возвращаем прокси конвертер чтобы избежать рекурсивного создания конвертеров
            # в случаях рекурсивных типов, например:
            #    class A:
            #       a: A
            return _ProxyConverter(typ)
        self._request_stack.add(typ)

        for factory in self.converter_factories:
            if factory.can_convert(typ):
                converter = factory.create_converter(typ, self)
                self.converters[typ] = converter
                return converter

        self._request_stack.remove(typ)
        raise TypeError(f'No converter found for type: {typ}')

    def get_provider(self, typ: Type[T]) -> Optional[Provider[T]]:
        provider = self.providers.get(typ)

        if provider is not None:
            return provider

        for factory in self.provider_factories:
            if factory.can_provide(typ):
                provider = factory.create_provider(typ, self)
                self.providers[typ] = provider
                return provider

        return None


_DEFAULT_OPTIONS = SerializationOptions()


def dump(obj: Any, options: SerializationOptions = _DEFAULT_OPTIONS) -> TSerialized:
    """ Выполняет сериализацию - преобразование объекта `obj` в разложенное представление,
     состоящее из базовых типов (списков, словарей, строк, чисел и т.п)

    :param obj: Исходный объект
    :param options: Параметры и контекст сериализации

    :raise TypeError: В случае невозможности выполнить преобразования:
    не существует подходящих конвертеров.

    :returns: Разложенное представление объекта

    Пример::

        class MyClass:
            def __init__(x: int)
                self.x = x

        data = dump(MyClass(42)) # {'x': 42}

    """
    converter = options.get_converter(type(obj))
    return converter.dump(obj, options)


def load(
        typ: Type[T],
        data: Dict[str, Any],
        *,
        key: Union[TPrimitive, _NotProvided] = NOT_PROVIDED,
        options: SerializationOptions = _DEFAULT_OPTIONS
) -> T:
    """ Выполняет десериализацию (создание) объекта типа `typ` из данных `data`

    :param typ: Целевой тип объекта
    :param data: Представление объекта в виде базовых типов (словарей, списков, строк, ...)
    :param key: Ключ объекта в родительской коллекции (если имеется)
    :param options: Параметры и контекст десериализацию

    :raise TypeError: В случае невозможности создать объект: отсутсвуют необходимые поля,
                      либо типы данных не соответствуют целевым.

    :returns: Готовый объект запрашиваемого типа

    Пример::

        class MyClass:
            def __init__(x: int)
                self.x = x

        obj = load(MyClass, {'x': 42})  # MyClass(42)

    """
    converter = options.get_converter(typ)
    return converter.load(data, key=key, options=options)

