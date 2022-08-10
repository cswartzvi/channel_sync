from typing import List

from conda.base.context import context


def get_default_subdirs() -> List[str]:
    return list(context.subdirs)


def get_known_subdirs() -> List[str]:
    return list(context.known_subdirs)
