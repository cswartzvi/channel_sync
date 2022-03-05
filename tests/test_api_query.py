from pathlib import Path
from typing import List

import pytest

from conda_local import api
from conda_local.external import compare_records


def fetch_local_specs(channel) -> List[str]:
    channel = Path(channel)
    file = channel / "specs.txt"
    lines = file.read_text().split("\n")
    return lines


@pytest.mark.parametrize(
    "name",
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
def test_query_of_packages(datadir, subdirs, name):
    channel = datadir / name
    specs = fetch_local_specs(channel)
    expected = api.iterate(str(channel), subdirs)
    actual = api.query(str(datadir / "all"), specs, subdirs=subdirs)
    added, removed = compare_records(actual, expected)
    assert not added
    assert not removed


def test_contradiction_query(datadir, subdirs):
    channel = datadir / "all"
    result = set(
        api.query(str(channel), ["python <3.8.0", "python >3.8.0"], subdirs=subdirs)
    )
    assert len(result) == 0
