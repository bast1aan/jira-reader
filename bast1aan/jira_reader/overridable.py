from dataclasses import is_dataclass, astuple
from typing import TypeVar

T = TypeVar('T')

def overridable(cls: type[T]) -> type[T]:
    """ Override the comparison behaviour to allow subclasses """
    if not is_dataclass(cls):
        raise TypeError(f'{cls} must be dataclass')

    def __eq__(self: T, other: T) -> bool:
        return is_dataclass(other) and (self is other or astuple(self) == astuple(other))

    cls.__eq__ = __eq__
    return cls
