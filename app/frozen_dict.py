from collections.abc import Mapping


class FrozenValuesDictionary(dict):
    """
        A dictionary where new key:value pairs can be added,
        but changing the value for an existing key raises
        a TypeError
    """
    def __init__(self, other=None, **kwargs):
        super().__init__()
        self.update(other, **kwargs)

    def __setitem__(self, key, value):
        if key in self:
            msg = 'key {!r} already exists with value {!r}'
            raise TypeError(msg.format(key, self[key]))
        super().__setitem__(key, value)

    def update(self, other=None, **kwargs):
        if other is not None:
            for k, v in other.items() if isinstance(other, Mapping) else other:
                self[k] = v
        for k, v in kwargs.items():
            self[k] = v
