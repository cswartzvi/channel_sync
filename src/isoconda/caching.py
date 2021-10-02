# -*- coding: utf-8 -*-


class CachedInstances(type):
    """Metaclass for caching instances by their initialization parameters."""

    def __init__(cls, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cls._cache = {}

    def __call__(cls, *args, **kwargs):
        key = tuple(args) + tuple(kwargs.items())
        if key not in cls._cache:
            cls._cache[key] = super().__call__(*args, **kwargs)
        return cls._cache[key]
