from typing import Set

import click
from pydantic import BaseSettings
from pydantic import Field


class AppState(BaseSettings):
    """Persistent application state."""

    channel: str = "conda-forge"
    target: str = ""
    latest_versions: bool = False
    latest_builds: bool = False
    latest_roots: bool = False
    debug: bool = False
    quiet: bool = False
    requirements: Set[str] = Field(default_factory=set)
    exclusions: Set[str] = Field(default_factory=set)
    disposables: Set[str] = Field(default_factory=set)
    subdirs: Set[str] = Field(default_factory=set)


pass_state = click.make_pass_decorator(AppState, ensure=True)


class ConfigurationState(BaseSettings):
    """The current state of configuration file settings."""

    channel: str = ""
    target: str = ""
    requirements: Set[str] = Field(default_factory=set)
    exclusions: Set[str] = Field(default_factory=set)
    disposables: Set[str] = Field(default_factory=set)
    subdirs: Set[str] = Field(default_factory=set)
    latest_versions: bool = False
    latest_builds: bool = False
    latest_roots: bool = False
    quiet: bool = False
