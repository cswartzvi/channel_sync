import pytest

from conda_local.api import iterate, merge, synchronize


@pytest.mark.parametrize(
    "specs_before, specs_after",
    [
        pytest.param(
            ("python =3.8.11", "fastapi", "sqlalchemy"),
            ("python =3.8.11", "fastapi", "sqlalchemy"),
            marks=pytest.mark.slow,
        ),
        (
            (
                "libstdcxx-ng =11.2",
                "libgcc-ng =11.2",
                "libgomp =11.2",
                "llvm-openmp =13.0.1",
                "_openmp_mutex =4.5",
            ),
            (
                "libstdcxx-ng =11.1|=11.2",
                "libgcc-ng =11.1|11.2",
                "libgomp =11.1|=11.2",
                "llvm-openmp =13.0.1",
                "_openmp_mutex =4.5",
            ),
        ),
    ],
)
def test_merge_expanded_specifications(tmp_path, subdirs, specs_before, specs_after):
    actual_channel = tmp_path / "actual_channel"
    synchronize(
        actual_channel,
        "conda-forge",
        specs=specs_before,
        subdirs=subdirs,
        silent=False,
    )
    patch = tmp_path / "patch"
    synchronize(
        actual_channel,
        "conda-forge",
        specs=specs_after,
        subdirs=subdirs,
        patch=patch,
        silent=False,
    )
    merge(actual_channel, patch)

    expected_channel = tmp_path / "expected_channel"
    synchronize(
        expected_channel,
        "conda-forge",
        specs=specs_after,
        subdirs=subdirs,
        silent=False,
    )

    actual = set(rec.fn for rec in iterate(actual_channel, subdirs))
    expected = set(rec.fn for rec in iterate(expected_channel, subdirs))
    assert actual == expected


@pytest.mark.parametrize(
    "specs_before, specs_after",
    [
        pytest.param(
            ("python =3.8.11|3.8.12", "fastapi", "sqlalchemy"),
            ("python =3.8.11", "fastapi", "sqlalchemy"),
            marks=pytest.mark.slow,
        ),
        (
            (
                "libstdcxx-ng =11.1|=11.2",
                "libgcc-ng =11.1|11.2",
                "libgomp =11.1|=11.2",
                "llvm-openmp =13.0.1",
                "_openmp_mutex =4.5",
            ),
            (
                "libstdcxx-ng =11.2",
                "libgcc-ng =11.2",
                "libgomp =11.2",
                "llvm-openmp =13.0.1",
                "_openmp_mutex =4.5",
            ),
        ),
    ],
)
def test_merge_shrinking_specifications(tmp_path, subdirs, specs_before, specs_after):
    actual_channel = tmp_path / "actual_channel"
    synchronize(
        actual_channel,
        "conda-forge",
        specs=specs_before,
        subdirs=subdirs,
        silent=False,
    )
    patch = tmp_path / "patch"
    synchronize(
        actual_channel,
        "conda-forge",
        specs=specs_after,
        subdirs=subdirs,
        patch=patch,
        silent=False,
    )
    merge(actual_channel, patch)

    expected_channel = tmp_path / "expected_channel"
    synchronize(
        expected_channel,
        "conda-forge",
        specs=specs_after,
        subdirs=subdirs,
        silent=False,
    )

    actual = set(rec.fn for rec in iterate(actual_channel, subdirs))
    expected = set(rec.fn for rec in iterate(expected_channel, subdirs))
    assert actual == expected
