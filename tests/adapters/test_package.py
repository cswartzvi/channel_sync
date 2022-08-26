from hashlib import sha256
from typing import Dict

import pytest
from conda.exports import PackageRecord

from conda_replicate.adapters.package import CondaPackage

DATA: Dict = {
    "name": "numpy",
    "version": "1.20.1",
    "build": "py38_1",
    "build_number": 1,
    "license": "BSD-3",
    "sha256": "567f0c41296c3dddac13ac88012b73ab16110b7233a217e3aabf61dd2f7fa1e1",
    "url": "https://its.a.fake.com/numpy",
    "subdir": "linux-64",
    "depends": ("python >=3.8,<3.9.0a0",),
    "size": 15000,
    "channel": "conda-forge",
    "fn": "numpy-1.20.1-py38_1",  # Filename does NOT include extension!
}


@pytest.fixture
def record(scope="module"):
    return PackageRecord(**DATA)


def test_conda_package_build_property(record):
    package = CondaPackage(record)
    assert isinstance(package.build, str)
    assert package.build == DATA["build"]


def test_conda_package_build_number_property(record):
    package = CondaPackage(record)
    assert isinstance(package.build_number, int)
    assert package.build_number == DATA["build_number"]


def test_conda_package_channel_property(record):
    package = CondaPackage(record)
    assert isinstance(package.channel, str)
    assert package.channel == DATA["channel"]


def test_conda_package_depends_property(record):
    package = CondaPackage(record)
    assert isinstance(package.depends, tuple)
    assert all(isinstance(depend, str) for depend in package.depends)
    assert package.depends == DATA["depends"]


def test_conda_package_fn_property(record):
    package = CondaPackage(record)
    assert isinstance(package.fn, str)
    assert package.fn == DATA["fn"]


def test_conda_package_name_property(record):
    package = CondaPackage(record)
    assert isinstance(package.name, str)
    assert package.name == DATA["name"]


def test_conda_package_size_property(record):
    package = CondaPackage(record)
    assert isinstance(package.size, int)
    assert package.size == DATA["size"]


def test_conda_package_sha256_property(record):
    package = CondaPackage(record)
    assert isinstance(package.sha256, str)
    actual = sha256(package.sha256.encode("utf-8")).hexdigest()
    expected = sha256(DATA["sha256"].encode("utf-8")).hexdigest()
    assert actual == expected


def test_conda_package_subdirs_property(record):
    package = CondaPackage(record)
    assert isinstance(package.subdir, str)
    assert package.subdir == DATA["subdir"]


def test_conda_package_url_property(record):
    package = CondaPackage(record)
    assert isinstance(package.url, str)
    assert package.url == DATA["url"]


def test_conda_package_version_property(record):
    package = CondaPackage(record)
    assert isinstance(package.version, str)
    assert package.version == DATA["version"]


def test_conda_package_equality():
    record1 = PackageRecord(
        name="python",
        version="3.8.12",
        build="001_0",
        build_number=0,
        channel="conda-forge",
    )
    package1 = CondaPackage(record1)

    record2 = PackageRecord(
        name="python",
        version="3.8.12",
        build="001_0",
        build_number=0,
        channel="conda-forge",
    )
    package2 = CondaPackage(record2)

    assert package1 == package2


def test_conda_package_equality_with_different_channels():
    record1 = PackageRecord(
        name="python",
        version="3.8.12",
        build="001_0",
        build_number=0,
        channel="conda-forge",
    )
    package1 = CondaPackage(record1)

    record2 = PackageRecord(
        name="python",
        version="3.8.12",
        build="001_0",
        build_number=0,
        channel="main",  # different!
    )
    package2 = CondaPackage(record2)

    assert package1 == package2


def test_conda_package_hash():
    record1 = PackageRecord(
        name="python",
        version="3.8.12",
        build="001_0",
        build_number=0,
        channel="conda-forge",
    )
    package1 = CondaPackage(record1)

    record2 = PackageRecord(
        name="python",
        version="3.8.12",
        build="001_0",
        build_number=0,
        channel="conda-forge",
    )
    package2 = CondaPackage(record2)

    assert hash(package1) == hash(package2)


def test_conda_package_hash_with_different_channels():
    record1 = PackageRecord(
        name="python",
        version="3.8.12",
        build="001_0",
        build_number=0,
        channel="conda-forge",
    )
    package1 = CondaPackage(record1)

    record2 = PackageRecord(
        name="python",
        version="3.8.12",
        build="001_0",
        build_number=0,
        channel="main",  # different!
    )
    package2 = CondaPackage(record2)

    assert hash(package1) == hash(package2)


def test_conda_package_repr_method(record):
    package = CondaPackage(record)
    class_name = package.__class__.__name__
    expected = (
        f"<{class_name}: "
        + ", ".join(f"{key}: {value}" for key, value in sorted(DATA.items()))
        + ">"
    )
    assert repr(package) == expected


def test_conda_package_str_method(record):
    package = CondaPackage(record)
    assert str(package) == DATA["fn"]
