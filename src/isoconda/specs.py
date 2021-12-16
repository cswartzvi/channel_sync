from typing import Iterable, Iterator
from conda.exports import MatchSpec


def get_specs(items: Iterable[str]) -> Iterator[MatchSpec]:
    for item in items:
        yield MatchSpec(item)
