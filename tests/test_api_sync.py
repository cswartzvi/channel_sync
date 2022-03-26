import shlex
import subprocess

import pytest

from conda_local import api


def check_record_is_installable(record, channel):
    cmd = (
        "conda create -n fake-testing-environment "
        f'"{record.name}={record.version}={record.build}" '
        "--override-channels "
        f"-c {channel} "
        "--dry-run"
    )
    result = subprocess.run(shlex.split(cmd), capture_output=True)
    return result.returncode == 0


def check_record_is_installable_with_constraints(record, channel, constraints):
    constraints = " ".join(f'"{spec}"' for spec in constraints)
    cmd = (
        "conda create -n fake-testing-environment "
        f'"{record.name}={record.version}={record.build}" '
        f"{constraints} "
        "--override-channels "
        f"-c {channel} "
        "--dry-run"
    )
    result = subprocess.run(shlex.split(cmd), capture_output=True)
    return result.returncode == 0


@pytest.mark.parametrize(
    "specs",
    [
        pytest.param(
            ("python =3.8.12", "fastapi", "sqlalchemy"), marks=pytest.mark.slow
        ),
        (
            "libstdcxx-ng =11.2",
            "libgcc-ng >=11.2",
            "libgomp =11.2",
            "llvm-openmp >=13.0,<14.0",
            "_openmp_mutex >=4.5",
        ),
    ],
)
def test_sync_installable_packages(tmp_path, subdirs, specs):
    api.synchronize(tmp_path, "conda-forge", specs=specs, subdirs=subdirs, silent=False)
    records = api.iterate(tmp_path.resolve().as_uri(), subdirs=subdirs)

    failed_installs = []
    for record in sorted(records, key=lambda rec: rec.fn):
        if check_record_is_installable(record, tmp_path.resolve().as_uri()):
            print("Passed:", record.fn)
        else:
            # NOTE: the package might not be installable on conda-forge either.
            if check_record_is_installable_with_constraints(
                record, "conda-forge", specs
            ):
                print("FAILED:", record.fn)
                failed_installs.append(record.fn)
            else:
                print("SKIPPED:", record.fn)

    assert not failed_installs
