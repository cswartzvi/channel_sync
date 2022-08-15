import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Set

import pytest
import yaml

from conda_replicate.adapters.channel import CondaChannel
from conda_replicate.adapters.channel import LocalCondaChannel
from tests.utils import get_test_data_path


@dataclass
class TestData:
    path: Path
    subdirs: List[str] = field(default_factory=list)

    def get_package_filenames(self) -> Set[str]:
        filenames = set()
        for subdir in self.subdirs:
            repodata = self.path / subdir / "repodata.json"
            with repodata.open("rt") as file:
                data = json.load(file)
            filenames.update(data["packages"].keys())
        return filenames


@pytest.fixture
def testdata(request) -> TestData:
    path = get_test_data_path() / "channels" / request.param
    config = path / "config.yml"
    with config.open("rt") as file:
        contents = yaml.load(file, Loader=yaml.CLoader)
    return TestData(path=path, subdirs=contents["subdirs"])


def test_conda_channel_name_property():
    channel = CondaChannel("conda-forge")
    assert channel.name == "conda-forge"


def test_conda_channel_url_property():
    channel = CondaChannel("conda-forge")
    assert channel.url == "https://conda.anaconda.org/conda-forge"


def test_conda_channel_is_queryable_property():
    channel = CondaChannel("conda-forge")
    assert channel.is_queryable


@pytest.mark.parametrize(
    "testdata", ["complete_nopython", "complete_python"], indirect=True
)
def tests_conda_channel_find_subdirs(testdata: TestData):
    path = testdata.path
    channel = CondaChannel(path.as_uri())
    actual = set(channel.find_subdirs())
    expected = set(item.name for item in path.iterdir() if item.is_dir())
    assert actual == expected


@pytest.mark.parametrize(
    "testdata", ["complete_nopython", "complete_python"], indirect=True
)
def tests_conda_channel_iter_packages(testdata: TestData):
    path = testdata.path
    channel = CondaChannel(path.as_uri())
    actual = set(pkg.fn for pkg in channel.iter_packages(["noarch", "win-64"]))
    expected = testdata.get_package_filenames()
    assert actual == expected


@pytest.mark.parametrize(
    ("testdata", "query"),
    [
        ("complete_nopython", "python"),
        ("complete_python", "python"),
        ("complete_nopython", "sqlite"),
        ("complete_python", "sqlite"),
    ],
    indirect=["testdata"],
)
def tests_conda_channel_query_packages(testdata: TestData, query: str):
    path = testdata.path
    channel = CondaChannel(path.as_uri())
    actual = set(pkg.fn for pkg in channel.query_packages(query, ["noarch", "win-64"]))
    expected = set(
        fn for fn in testdata.get_package_filenames() if fn.startswith(query + "-")
    )
    assert actual == expected
