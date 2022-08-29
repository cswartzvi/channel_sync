import pytest
from conda.exports import PackageRecord

from conda_replicate.adapters.specification import CondaSpecification
from conda_replicate.adapters.specification import InvalidCondaSpecification


def test_conda_specification_with_invalid_parameters():
    with pytest.raises(InvalidCondaSpecification):
        _ = CondaSpecification("python >>3.10")


def test_conda_specification_name_property():
    spec = CondaSpecification("python >=3.10")
    assert isinstance(spec.name, str)
    assert spec.name == "python"


def test_conda_specification_value_property():
    spec = CondaSpecification("python >=3.10")
    assert isinstance(spec.name, str)
    assert spec.name == "python"


def test_conda_specification_valid_match():
    record = PackageRecord(
        name="python",
        version="3.8.12",
        build="001_0",
        build_number=0,
        channel="conda-forge",
    )
    spec = CondaSpecification("python >=3.8,<=3.9")
    assert spec.match(record)


def test_conda_specification_invalid_match():
    record = PackageRecord(
        name="python",
        version="3.8.12",
        build="001_0",
        build_number=0,
        channel="conda-forge",
    )
    spec = CondaSpecification("python >=3.9,<=3.10")
    assert not spec.match(record)


def test_conda_package_repr_method():
    spec = CondaSpecification("python >=3.9,<=3.10")
    expected = "<CondaSpecification: value='python >=3.9,<=3.10'>"
    assert repr(spec) == expected


def test_conda_package_str_method():
    spec = CondaSpecification("python >=3.9,<=3.10")
    assert str(spec) == "python >=3.9,<=3.10"
