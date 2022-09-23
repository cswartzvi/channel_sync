from typing import Tuple

from conda.base.context import context


def get_default_subdirs() -> Tuple[str, ...]:
    return tuple(context.subdirs)


def get_known_subdirs() -> Tuple[str, ...]:
    return tuple(context.known_subdirs)
