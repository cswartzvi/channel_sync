from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def subdirs():
    return ["noarch", "linux-64"]


@pytest.fixture()
def datadir(request):
    file_path = Path(request.module.__file__)
    return file_path.parent / "data"
