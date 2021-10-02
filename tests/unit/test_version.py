import pytest

from isoconda.version import VersionOrder


@pytest.mark.parametrize(
    "left, right",
    [
        ("0.4.0", "0.4.1.rc"),
        ("0.4.1.rc", "0.4.1"),
        ("0.4.1", "0.5a1"),
        ("0.5a1", "0.5b3"),
        ("0.5b3", "0.5C1"),
        ("0.5C1", "0.5"),
        ("0.5", "0.9.6"),
        ("0.9.6", "0.960923"),
        ("0.960923", "1.0"),
        ("1.0", "1.1dev1"),
        ("1.1dev1", "1.1a1"),
        ("1.1a1", "1.10dev1"),
        ("1.1.0dev1", "1.1.a1"),
        ("1.1.a1", "1.1.0rc1"),
        ("1.1.0rc1", "1.1.0"),
        ("1.1.0", "1.1.0post1"),
        ("1.1.post1", "1996.07.12"),
        ("1996.07.12", "1!0.4.1"),
        ("1!0.4.1", "1!3.1.1.6"),
        ("1!3.1.1.6", "2!0.4.1"),
    ]
)
def test_left_is_less_than_right(left: str, right: str) -> None:
    left_order = VersionOrder(left)
    right_order = VersionOrder(right)
    assert left_order < right_order


@pytest.mark.parametrize(
    "left, right",
    [
        ("0.4", "0.4.0"),
        ("0.4.1rc", "0.4.1RC"),
        ("1.1.0dev1", "1.1.dev1"),
        ("1.1", "1.1.0"),
        ("1.1.0post1", "1.1.post1"),
    ]
)
def test_left_is_equal_to_right(left: str, right: str) -> None:
    left_order = VersionOrder(left)
    right_order = VersionOrder(right)
    assert left_order == right_order


def test_total_ordering_with_case_insensitive_comparisons():
    versions = [
        "0.4",
        "0.4.0",
        "0.4.1.rc",
        "0.4.1.RC",
        "0.4.1",
        "0.5a1",
        "0.5b3",
        "0.5C1",
        "0.5",
        "0.9.6",
        "0.960923",
        "1.0",
        "1.1dev1",
        "1.1a1",
        "1.1.0dev1",
        "1.1.dev1",
        "1.1.a1",
        "1.1.0rc1",
        "1.1.0",
        "1.1",
        "1.1.0post1",
        "1.1.post1",
        "1.1post1",
        "1996.07.12",
        "1!0.4.1",
        "1!3.1.1.6",
        "2!0.4.1",
    ]

    version_tuples = [(version, VersionOrder(version)) for version in versions]
    assert sorted(version_tuples, key=lambda x: x[1]) == version_tuples


def test_total_version_ordering_without_case_insensitive_comparisons():
    versions = [
        "0.4",
        "0.4.1.rc",
        "0.4.1",
        "0.5a1",
        "0.5b3",
        "0.5C1",
        "0.5",
        "0.9.6",
        "0.960923",
        "1.0",
        "1.1dev1",
        "1.1a1",
        "1.1.0dev1",
        "1.1.a1",
        "1.1.0rc1",
        "1.1.0",
        "1.1.0post1",
        "1.1post1",
        "1996.07.12",
        "1!0.4.1",
        "1!3.1.1.6",
        "2!0.4.1",
    ]

    version_tuples = [(version, VersionOrder(version)) for version in versions]
    reversed_tuples = reversed(version_tuples)
    assert sorted(reversed_tuples, key=lambda x: x[1]) == version_tuples
