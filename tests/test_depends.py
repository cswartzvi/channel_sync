import shutil
from pathlib import Path
from typing import List, Set

import pytest

from conda_sync.depends import DependencyScout
from conda_sync.external import ChannelData, PackageRecord

TEST_PLATFORMS = ["linux-64", "noarch"]


@pytest.fixture()
def datadir(request):
    file_path = Path(request.module.__file__)
    return file_path.parent / "data"


def fetch_local_packages(channel: Path) -> Set[PackageRecord]:
    assert channel.is_dir()
    uri = channel.resolve().as_uri()
    channel_data = ChannelData(channel=uri, platforms=TEST_PLATFORMS)
    return set(channel_data.iter_records())


def fetch_local_specs(channel: Path) -> List[str]:
    assert channel.is_dir()
    file = channel / "specs.txt"
    lines = file.read_text().split("\n")
    return lines


def remove_contents(directory: Path) -> None:
    directory = Path(directory)
    for item in directory.iterdir():
        if item.is_dir():
            remove_contents(item)
        else:
            item.unlink()


@pytest.mark.parametrize(
    "test_name",
    [
        "python",
        "package1",
        "package2_all",
        "package2_select",
        "package3_all",
        "package3_select",
        "package4_all",
        "package4_select",
        "package5_all",
        "package5_select",
        "package6_all",
        "package6_select",
        "package7_all",
        "package7_select",
        "package8_all",
        "package8_select",
        "package9_all",
        "package9_select",
        "package10_all",
        "package10_select",
        "package11_all",
        "package11_select",
        "package12_all",
        "package12_select",
        "package13_all",
        "package13_select",
        "package14_all",
        "package14_select",
    ],
)
def test_explore_tmp_path_factory(datadir, tmp_path_factory, test_name):
    channel = tmp_path_factory.mktemp("channel")
    shutil.copytree(datadir / test_name, channel, dirs_exist_ok=True)
    specs = fetch_local_specs(channel)
    expected = fetch_local_packages(channel)

    remove_contents(channel)
    shutil.copytree(datadir / "all", channel, dirs_exist_ok=True)
    solver = DependencyScout(channel.resolve().as_uri(), platforms=TEST_PLATFORMS)
    solver.reload()  # required because channel is cached
    iterable, _ = solver.search(specs)
    actual = set(iterable)
    assert expected == actual


@pytest.mark.slow
@pytest.mark.parametrize("packages", [("python >=3.8,<3.9.0a0", "numpy >=1.20")])
def test_packages_are_installable(tmp_path_factory, packages):
    print(packages)
