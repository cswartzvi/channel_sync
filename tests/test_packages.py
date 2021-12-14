from isoconda.packages import solve
from isoconda.repo import fetch_local_records
from isoconda._vendor.conda.models.match_spec import MatchSpec


def test_package_filtering():
    expected = set(fetch_local_records("./tests/data/expected"))
    packages = fetch_local_records("./tests/data/pool")
    actual = solve(
        [MatchSpec("python >=3.8,<=3.9.0a0"), MatchSpec("numpy >=1.20")], packages
    )
    assert expected == actual
