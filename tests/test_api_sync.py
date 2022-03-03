import shlex
import subprocess

import pytest

from conda_local import api


@pytest.mark.slow
@pytest.mark.parametrize("packages", [("python >=3.8,<3.9.0a0", "numpy >=1.20")])
def test_packages_are_installable(tmp_path_factory, packages):
    print(packages)


@pytest.mark.slow
def test_sync_installable_packages(tmp_path, subdirs):
    print(tmp_path)
    api.sync("conda-forge", tmp_path, subdirs=subdirs, specs=["python =3.9.10"])
    records = api.iterate(tmp_path.resolve().as_uri(), subdirs=subdirs)
    failed_installs = []
    for record in sorted(records, key=lambda rec: rec.fn):
        cmd = (
            "conda create -n fake-testing-environment "
            f'"{record.name}={record.version}={record.build}" '
            "--override-channels "
            f"-c {tmp_path.resolve().as_uri()} "
            "--dry-run"
        )

        result = subprocess.run(shlex.split(cmd), capture_output=True)
        if result.returncode != 0:
            print("Failed:", record.fn)
            failed_installs.append(record.fn)
        else:
            print("Passed:", record.fn)

    assert not failed_installs
