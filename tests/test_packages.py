from pathlib import Path

import pytest
from conda.exports import MatchSpec

from isoconda.packages import solve
from isoconda.repo import fetch_local_records


def test_package_filtering():
    expected = set(fetch_local_records(Path("./tests/data/expected")))
    packages = fetch_local_records(Path("./tests/data/pool"))
    actual = solve(
        [MatchSpec("python >=3.8,<=3.9.0a0"), MatchSpec("numpy >=1.20")], packages
    )
    assert expected == actual


@pytest.mark.slow
def test_solver_satisfies_packages_specs():
    pass
