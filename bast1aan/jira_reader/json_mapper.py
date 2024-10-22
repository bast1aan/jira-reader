import json
import types
from collections import defaultdict
from dataclasses import is_dataclass, Field, fields, asdict
from datetime import datetime
from functools import cached_property
from typing import TypeVar, Generic, Mapping, Any, get_args, get_origin, ClassVar, get_type_hints, NamedTuple
from typing_extensions import Self
import dateutil.parser

T = TypeVar('T')


def _fix_field_types(cls):
    hints = get_type_hints(cls, globalns=None, localns=None)
    for field in fields(cls):
        field.type = hints[field.name]


class _FieldWrapper(Generic[T]):
    cls: type[T]

    _instances: ClassVar[dict[type, Self]] = {}

    @classmethod
    def for_cls(cls, cls_: type[T]) -> Self:
        if cls_ not in cls._instances:
            cls._instances[cls_] = cls(cls_)
        return cls._instances[cls_]

    def __init__(self, cls: type[T]):
        if not is_dataclass(cls):
            raise TypeError('cls of FieldWrapper needs to be a dataclass')
        self.cls = cls

    @cached_property
    def _fields(self) -> Mapping[str, Field]:
        return {f.name: f for f in fields(self.cls)}

    def __getattr__(self, item: str) -> tuple[type[T], Field]:
        if item not in self._fields:
            raise AttributeError(f'{item} not an attribute of {self.cls}')
        return self.cls, self._fields[item]


def into(cls: type[T]) -> T:
    return _FieldWrapper.for_cls(cls)


class JsonMapper(Generic[T]):
    class _MappingItem(NamedTuple):
        cls: type
        field: Field

    @classmethod
    def _mapping_item(cls, cls_: type | str, field: Field) -> _MappingItem:
        # constructor for _MappingItem (NamedTuples can't have an __init__)
        if isinstance(field.type, str):
            # convert deferred type hint strings to real types for this dataclass
            _fix_field_types(cls_)
        return cls._MappingItem(cls_, field)

    _init_kwargs = dict[type, dict[str, Any]]

    mapping: dict

    def __init__(self, mapping: dict, convert_null_to_empty_value=False):
        self.mapping = mapping
        self._init_kwargs = defaultdict(dict)
        self._convert_null_to_empty_value = convert_null_to_empty_value

    def _build(self, cls: type) -> object:
        return cls(**self._init_kwargs.pop(cls))

    def _factory(self, t: type, input: Any) -> Any:
        if t is datetime:
            return dateutil.parser.parse(input)
        if get_origin(t) is types.UnionType:
            # handle optional types (str | None)
            args = get_args(t)
            if len(args) == 2 and types.NoneType in args:
                # type is optional
                if input is None:
                    return None
                t = args[0] if args[1] is types.NoneType else args[1]
        if input is None:
            if self._convert_null_to_empty_value:
                return t()
            raise NoneTypeError(f'instance of {t} must not be None')
        return t(input)

    def _walk(self, mapping: dict | list | tuple, input: object) -> None:
        if isinstance(mapping, list):
            if not isinstance(input, list):
                raise DecodingError('list mismatch')
            result_objects = []
            if len(mapping) == 1:
                # we got a primitive type
                mapping_item = self._mapping_item(*mapping[0])
                type_in_list = get_args(mapping_item.field.type)[0]
                result_objects = [self._factory(type_in_list, item) for item in input]
            elif len(mapping) == 2:
                # we got a compound type
                mapping_item = self._mapping_item(*mapping[1])
                type_in_list = get_args(mapping_item.field.type)[0]
                for item in input:
                    self._walk(mapping[0], item)
                    result_objects.append(self._build(type_in_list))
            else:
                raise DecodingError('Wrong list size')
            self._walk(mapping[1], result_objects)
        elif isinstance(mapping, dict):
            if not isinstance(input, dict):
                raise DecodingError('dict mismatch')
            for k, v in mapping.items():
                self._walk(v, input.get(k))
        else:
            # we got a field
            mapping_item = self._mapping_item(*mapping)
            try:
                self._init_kwargs[mapping_item.cls][mapping_item.field.name] = self._factory(mapping_item.field.type, input)
            except NoneTypeError as e:
                raise NoneTypeError(f'{mapping_item.field.name} of {mapping_item.cls} must not be None') from e
            return

    def __call__(self, input: object) -> T:
        self._walk(self.mapping, input)
        cls = next(iter(self._init_kwargs.keys()))
        return self._build(cls)


class DecodingError(Exception): pass

class NoneTypeError(TypeError): pass

class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if is_dataclass(o):
            return asdict(o)
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)

def dumps(o: object) -> str:
    return json.dumps(o, cls=JSONEncoder)

def asdataclass(t: type[T], data: dict[str, Any]) -> T:
    # convert deferred type hint strings to real types for this dataclass
    _fix_field_types(t)

    t_fields = {f.name: f for f in fields(t)}
    converted = {}
    for k, v in data.items():
        field_type = t_fields[k].type
        converted[k] = _convert_to_type(field_type, v)
    return t(**converted)

def _convert_to_type(t: type[T], data: object) -> T:
    if t_not_none := _is_optional(t):
        if data is None:
            return None
        else:
            t = t_not_none
    if is_dataclass(t):
        return asdataclass(t, data)
    elif t is datetime:
        return datetime.fromisoformat(data)
    elif get_origin(t) is list:
        type_in_list = get_args(t)[0]
        result = []
        for item in data:
            result.append(_convert_to_type(type_in_list, item))
        return result
    return t(data)

def _is_optional(t: type) -> type | None:
    args = get_args(t)
    if type(None) in args:
        return (set(args) - {type(None)}).pop()
