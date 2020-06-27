"""Contains the models fro the representation of Anaconda repositories."""
from __future__ import annotations
import collections
import copy
from typing import (
    Any,
    Dict,
    Iterable,
    Iterator,
    List,
    Mapping,
    Tuple
)

from isoconda.errors import InvalidRepo


class PackageRecord:
    """Individual record within Anaconda repository index.

    Refer directly to elements in the repodata.json sub-dictionaries: 'packages' and
    'packages.conda'. Package records are developed for use with the ``conda`` executable.
    The structure of these records are dictated by the Anaconda organization and therefore
    are subject to change. In order to minimize breaking changes, this class only interacts
    with a small number of records fields and propagates all other fields when saving.
    """

    def __init__(self, filename: str, data: Dict[str, Any]):
        """Initialize object instance from record data.

        Args:
            filename: Package filename (on disk or as a download)
            data: Dictionary representation of record fields.
        """
        self._filename = filename
        self._data: Dict[str, Any] = copy.deepcopy(data)
        self._pkey = (self.subdir, self.name, self.version,
                      self.build_number, self.build)
        self._hash = hash(self._pkey)

    @property
    def build(self) -> str:
        """Package build identifier."""
        return self._data['build']

    @property
    def build_number(self) -> int:
        """Incremental number for new builds of the same build identifier."""
        return self._data['build_number']

    @property
    def filename(self) -> str:
        """The package filename, contains name, build and build number."""
        return self._filename

    @property
    def depends(self) -> Iterable[str]:
        """An interable package dependencies as package specification strings."""
        return self._data['depends']

    @property
    def name(self) -> str:
        """The package name."""
        return self._data['name']

    @property
    def subdir(self) -> str:
        """Repository sub-directory (platfrom architecture)."""
        return self._data['subdir']

    @property
    def version(self) -> str:
        """The package version."""
        return self._data['version']

    def __eq__(self, other):
        return self._pkey == other._pkey

    def __hash__(self):
        return self._hash

    def __repr__(self):
        return f'{type(self).__name__}({self.filename!r}, {self._data!r})'


class RepoData:
    """Represents an Anaconda repository index (repodata.json).

    The Anaconda repository index contains records for each packages in a platfrom
    specific sub-directory.

    """

    VERSION = 1

    def __init__(self, subdir: str, package_groups: Mapping[str, Iterable[PackageRecord]]):
        """Initializes data from the basic repository components.

        Args:
            subdir: Anaconda repository sub-directory (platfrom architecture)
            package_groups: ``PackageRecords`` grouped by generic package name.
        """
        self._subdir = subdir
        self._package_groups = {k: list(v) for k, v in package_groups.items()}

    @classmethod
    def from_data(cls, repodata: Dict[str, Any], prefer_conda: bool = False) -> RepoData:
        """Creates object instance from data within an anaconda repository.

        Args:
            repodata: Dictionary representation of anaconda repository data.
            prefer_conda: Determines if *.conda files are preferred over *.tar.bz2 files.
        """
        # The simplest check of the repodata.json schema version
        repodata_version = repodata['repodata_version']
        if repodata_version != cls.VERSION:
            raise InvalidRepo(f'Unknown repodata version: {repodata_version}')

        subdir = repodata['info']['subdir']
        package_groups: Dict[str, List[PackageRecord]] = collections.defaultdict(list)

        keys = ['packages', 'packages.conda']
        if prefer_conda:
            keys = list(reversed(keys))

        for key in keys:
            for filename, data in repodata[key].items():
                package = PackageRecord(filename, data)
                package_groups[package.name].append(package)

        return cls(subdir, package_groups)

    @property
    def subdir(self) -> str:
        """Repository sub-directory (platfrom architecture)."""
        return self._subdir

    def get(self, key, default=None) -> Iterator[PackageRecord]:
        """Yields all records of a given package type (name).

        Args:
            key: Package type to retrieve.
            default: Default value if package type (name) does not exist.
        """
        yield from self._package_groups.get(key, default)

    def items(self) -> Iterator[Tuple[str, Iterator[PackageRecord]]]:
        """Yields a tuple of package type (name) and record."""
        for name, package in self._package_groups.items():
            yield (name, iter(package))

    def keys(self) -> Iterator[str]:
        """Yields all existing package type (name)."""
        return iter(self)

    def values(self) -> Iterator[PackageRecord]:
        """Yields all existing package records in a flatten iterator."""
        for packages in self._package_groups.values():
            yield from packages

    def __contains__(self, key) -> bool:
        """Checks for membership of a generic package type."""
        return key in self._package_groups.keys()

    def __getitem__(self, key) -> Iterator[PackageRecord]:
        """Yields all records of given package type (name)."""
        return iter(self._package_groups[key])

    def __iter__(self) -> Iterator[str]:
        """Yields all package types (names)."""
        yield from self._package_groups.keys()

    def __len__(self) -> int:
        """Returns the number of package types (names)."""
        return len(self._package_groups.keys())
