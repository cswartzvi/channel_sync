from __future__ import annotations

import datetime
from typing import List

import click
from pydantic import BaseSettings, Field

from conda_local.models import get_default_subdirs


def _default_patch_name() -> str:
    now = datetime.datetime.now()
    name = f"patch_{now.strftime('%Y%m%d_%H%M%S')}"
    return name


class ConfigurableState(BaseSettings):
    channel: str = "conda-forge"
    reference: str = ""
    target: str = ""
    requirements: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    disposables: List[str] = Field(default_factory=list)
    subdirs: List[str] = Field(default_factory=get_default_subdirs)
    validate_: bool = True
    latest: bool = True


class ApplicationState(ConfigurableState):
    patch_name: str = Field(default_factory=_default_patch_name)
    patch_directory: str = "."
    output: str = "summary"
    quiet: bool = False

    def update(self, configuration: ConfigurableState) -> None:
        for field in configuration.__fields_set__:
            if field not in self.__fields_set__:
                continue
            attribute = getattr(self, field)
            incoming = getattr(configuration, field)
            if isinstance(attribute, list):
                attribute.extend(incoming)
            else:
                attribute = incoming
            setattr(self, field, attribute)


pass_state = click.make_pass_decorator(ApplicationState, ensure=True)
