from typing import Optional, Set

import click
from pydantic import BaseSettings
from pydantic import Field


class AppState(BaseSettings):
    """Persistent application state."""

    channel: str = "conda-forge"
    target: Optional[str] = None
    requirements: Set[str] = Field(default_factory=set)
    exclusions: Set[str] = Field(default_factory=set)
    disposables: Set[str] = Field(default_factory=set)
    subdirs: Set[str] = Field(default_factory=set)
    latest: Optional[str] = None
    latest_roots: bool = False
    quiet: bool = False
    debug: bool = False


pass_state = click.make_pass_decorator(AppState, ensure=True)


class ConfigurationState(BaseSettings):
    """The current state of configuration file settings."""

    channel: str = ""
    target: Optional[str] = None
    requirements: Set[str] = Field(default_factory=set)
    exclusions: Set[str] = Field(default_factory=set)
    disposables: Set[str] = Field(default_factory=set)
    subdirs: Set[str] = Field(default_factory=set)
    latest: Optional[str] = None
    latest_roots: bool = False
    quiet: bool = False
