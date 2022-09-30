import pathlib
from typing import Iterable, Union

from conda_replicate.adapters.channel import CondaChannel
from conda_replicate.adapters.channel import LocalCondaChannel

ChannelSource = Union[str, pathlib.Path, CondaChannel]
LocalChannelSource = Union[str, pathlib.Path, LocalCondaChannel]

Spec = str
Specs = Iterable[Spec]

Subdir = str
Subdirs = Iterable[Subdir]

Latest = str
