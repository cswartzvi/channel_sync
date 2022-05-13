from pathlib import Path
from typing import List

import pytest

from conda_local import api
from conda_local.external import (
    compute_relative_complements_of_records,
    get_default_subdirs,
    query_channel,
)


def fetch_local_specs(channel) -> List[str]:
    channel = Path(channel)
    file = channel / "specs.txt"
    lines = file.read_text().split("\n")
    return lines


@pytest.mark.parametrize(
    "name",
    [
        "query01",
        "query02",
        "query03",
        "query04",
        "query05",
        "query06",
        "query07",
        "query08",
        "query09",
        "query10",
        "query11",
    ],
)
def test_query_on_example_channels(datadir, subdirs, name):
    base = datadir / name
    specs = fetch_local_specs(base)
    expected = api.iterate((base / "expected").as_uri(), subdirs=subdirs)
    actual = api.query((base / "all").as_uri(), specs, subdirs=subdirs)
    added, removed = compute_relative_complements_of_records(actual, expected)
    assert not added
    assert not removed


def test_python_query_on_current_system():
    subdirs = get_default_subdirs()
    records = api.query("conda-forge", "python")
    actual = (record for record in records if record.name == "python")
    expected = query_channel("conda-forge", subdirs=subdirs, spec="python")
    added, removed = compute_relative_complements_of_records(actual, expected)
    assert not added
    assert not removed
