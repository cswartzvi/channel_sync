from __future__ import annotations

import json
import shlex
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import List, Set

import pytest
import yaml
from click.testing import CliRunner

from conda_replicate.cli import query
from tests.utils import get_test_data_path
from tests.utils import make_arguments
from tests.utils import make_options


@pytest.fixture(scope="module")
def lookup():
    return QueryDataLookup(get_test_data_path() / "channels" / "repodata_only")


class QueryDataLookup:
    """Provides a lookup of test data for the query sub-command."""

    __test__ = False

    def __init__(self, path: Path) -> None:
        self.path = path

    def get(self, name: str) -> QueryData:
        path = self.path / name

        config = path / "config.yml"
        with config.open("rt") as file:
            contents = yaml.load(file, Loader=yaml.CLoader)

        return QueryData(
            path=path,
            subdirs=contents["subdirs"],
            requirements=contents["requirements"],
            exclusions=contents.get("exclusions", []),
            disposables=contents.get("disposables", []),
        )


@dataclass(frozen=True)
class QueryData:
    """Encapsulates test data for the query sub-command."""

    __test__ = False

    path: Path
    subdirs: List[str]
    requirements: List[str]
    exclusions: List[str] = field(default_factory=list)
    disposables: List[str] = field(default_factory=list)

    def get_package_filenames(self) -> Set[str]:
        filenames = set()
        for subdir in self.subdirs:
            repodata = self.path / subdir / "repodata.json"
            with repodata.open("rt") as file:
                data = json.load(file)
            filenames.update(data["packages"].keys())
        return filenames


@pytest.mark.parametrize(
    "name",
    [
        "original",
        "selected1",
        "selected2",
        "selected1_exclude",
    ],
)
def test_query_round_trips_channel_contents(
    runner: CliRunner, lookup: QueryDataLookup, name: str
):
    data = lookup.get(name)

    parameters = shlex.split(
        f"""
        --channel {data.path.as_uri()}
        {make_arguments(*data.requirements)}
        {make_options("exclude", *data.exclusions)}
        {make_options("dispose", *data.disposables)}
        {make_options("subdir", *data.subdirs)}
        --output json
        --quiet
        """
    )
    result = runner.invoke(query, parameters)
    contents = json.loads(result.output, strict=False)
    actual = set(record["fn"] for record in contents["add"])

    expected = data.get_package_filenames()

    assert result.exit_code == 0
    assert actual == expected


@pytest.mark.parametrize(
    ("baseline", "subset"),
    [
        ("original", "selected1"),
        ("original", "selected2"),
        ("original", "selected1_exclude"),
        ("original", "selected1_dispose"),
    ],
)
def test_query_selects_correct_subset_of_a_channel(
    runner: CliRunner, lookup: QueryDataLookup, baseline: str, subset: str
):
    baseline_data = lookup.get(baseline)
    subset_data = lookup.get(subset)

    parameters = shlex.split(
        f"""
        --channel {baseline_data.path.as_uri()}
        {make_arguments(*subset_data.requirements)}
        {make_options("exclude", *subset_data.exclusions)}
        {make_options("dispose", *subset_data.disposables)}
        {make_options("subdir", *subset_data.subdirs)}
        --output json
        --quiet
        """
    )

    result = runner.invoke(query, parameters)
    contents = json.loads(result.output, strict=False)
    actual = set(record["fn"] for record in contents["add"])

    expected = subset_data.get_package_filenames()

    assert result.exit_code == 0
    assert actual == expected


@pytest.mark.parametrize(
    ("baseline", "target", "subset"),
    [
        ("original", "selected2", "selected1"),
        ("original", "selected1", "selected1_exclude"),
        ("original", "selected1", "selected1_dispose"),
    ],
)
def test_query_selects_correct_subset_with_target(
    runner: CliRunner, lookup: QueryDataLookup, baseline: str, target: str, subset: str
):
    baseline_data = lookup.get(baseline)
    target_data = lookup.get(target)
    subset_data = lookup.get(subset)

    parameters = shlex.split(
        f"""
        --channel {baseline_data.path.as_uri()}
        {make_arguments(*subset_data.requirements)}
        {make_options("exclude", *subset_data.exclusions)}
        {make_options("dispose", *subset_data.disposables)}
        {make_options("subdir", *subset_data.subdirs)}
        {make_options("target", target_data.path)}
        --output json
        --quiet
        """
    )

    result = runner.invoke(query, parameters)
    contents = json.loads(result.output, strict=False)
    actual = set(record["fn"] for record in contents["remove"])

    subset_filenames = subset_data.get_package_filenames()
    target_filenames = target_data.get_package_filenames()
    expected = subset_filenames - target_filenames

    assert result.exit_code == 0
    assert actual == expected
