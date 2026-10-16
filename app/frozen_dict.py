from __future__ import annotations

from collections import UserDict
from typing import Any


class FrozenValuesDictionary(UserDict[str, Any]):
    """
        A dictionary where new key:value pairs can be added,
        but changing the value for an existing key raises
        a TypeError

        `UserDict` sends every write (including `__init__` and `update`)
        through `__setitem__`, so that is the only method that needs to check.
    """
    def __setitem__(self, key: str, value: Any) -> None:
        if key in self:
            msg = 'key {!r} already exists with value {!r}'
            raise TypeError(msg.format(key, self[key]))
        super().__setitem__(key, value)
