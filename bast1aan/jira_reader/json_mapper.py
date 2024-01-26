import types
from collections import defaultdict
from dataclasses import is_dataclass, Field, fields
from datetime import datetime
from functools import cached_property, reduce
from typing import TypeVar, Generic, Mapping, Any, get_args, get_origin
import dateutil.parser

T = TypeVar('T')

class _FieldWrapper(Generic[T]):
    cls: type[T]

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
    return _FieldWrapper(cls)


class JsonMapper(Generic[T]):
    mapping: dict
    _init_kwargs = dict[type, dict[str, Any]]

    def __init__(self, mapping: dict):
        self.mapping = mapping
        self._init_kwargs = defaultdict(dict)

    def _build(self, cls: type) -> object:
        try:
            return cls(**self._init_kwargs.pop(cls))
        except KeyError:
            print(self._init_kwargs)
            print(cls)
            raise
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
            raise NoneTypeError(f'instance of {t} must not be None')
        return t(input)

    def _walk(self, mapping: dict | list | tuple, input: object) -> None:
        if isinstance(mapping, list):
            if not isinstance(input, list):
                raise DecodingError('list mismatch')
            result_objects = []
            if len(mapping) == 1:
                # we got a primitive type
                list_type = mapping[0][1].type.__args__[0]
                result_objects = [self._factory(list_type, item) for item in input]
            elif len(mapping) == 2:
                # we got a compound type
                import pprint

                try:

                    list_type = mapping[1][1].type.__args__[0]
                    print('WERKT')
                except AttributeError:
                    pprint.pprint(mapping[1][1].type)
                    pprint.pprint(eval(mapping[1][1].type, globals(), locals()))
                    raise
                for item in input:
                    self._walk(mapping[0], item)
                    result_objects.append(self._build(list_type))
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
            cls: type
            field: Field
            from pprint import pprint
            try:
                cls, field = mapping
            except TypeError:
                pprint(mapping)
                raise
            try:
                self._init_kwargs[cls][field.name] = self._factory(field.type, input)
            except NoneTypeError as e:
                raise NoneTypeError(f'{field.name} of {cls} must not be None') from e
            return

    def __call__(self, input: object) -> T:
        self._walk(self.mapping, input)
        cls = next(iter(self._init_kwargs.keys()))
        return self._build(cls)

class DecodingError(Exception): pass

class NoneTypeError(TypeError): pass
