"""Contains the models fro the representation of Anaconda repositories."""
from __future__ import annotations
import collections
import copy
import itertools
import reprlib
import weakref
from typing import (
    Any,
    Dict,
    Iterable,
    Iterator,
    List,
    Mapping,
    MutableSet
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
        self._conda = filename.endswith('conda')

    @property
    def build(self) -> str:
        """The package build identifier."""
        return self._data['build']

    @property
    def build_number(self) -> int:
        """An incremental number for new builds of the same build identifier."""
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
        """The name of the package type (generic; different than filename)."""
        return self._data['name']

    @property
    def sha256(self) -> str:
        """The sha256 hash code of the package."""
        return self._data['sha256']

    @property
    def subdir(self) -> str:
        """Repository sub-directory (platfrom architecture)."""
        return self._data['subdir']

    @property
    def timestamp(self) -> int:
        """The timestap of the package."""
        return self._data['timestamp']

    @property
    def version(self) -> str:
        """The package version."""
        return self._data['version']

    def is_conda(self) -> bool:
        """Returns True if the package is in the conda format."""
        return self._conda

    def dump(self) -> Dict[str, Any]:
        """Converts data into a dictionary representation."""
        return copy.deepcopy(self._data)

    def __eq__(self, other):
        return self._pkey == other._pkey

    def __hash__(self):
        return self._hash

    def __repr__(self):
        return f'{type(self).__name__}({self.filename!r}, {self._data!r})'


class RepoData(Mapping[str, Iterable[PackageRecord]]):
    """An Anaconda repository index (repodata.json) implementing the Mapping protocol.

    The Anaconda repository index contains records for each packages in a platfrom
    specific sub-directory.
    """

    VERSION = 1

    def __init__(self, subdir: str, package_groups: Mapping[str, Iterable[PackageRecord]]):
        """Initializes data from basic repository components.

        Args:
            subdir: Anaconda repository sub-directory (platfrom architecture)
            package_groups: ``PackageRecords`` grouped by generic package name.
        """
        self._subdir = subdir
        self._package_groups = {k: list(v) for k, v in package_groups.items()}

    @classmethod
    def from_data(cls, repodata: Dict[str, Any], prefer_conda: bool = False) -> RepoData:
        """Creates an object instance from data within an anaconda repository.

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
        packages: MutableSet[PackageRecord] = weakref.WeakSet()

        keys = ['packages', 'packages.conda']
        if prefer_conda:
            keys = list(reversed(keys))

        for key in keys:
            for filename, data in repodata[key].items():
                package = PackageRecord(filename, data)
                if package not in packages:
                    package_groups[package.name].append(package)
                    packages.add(package)

        return cls(subdir, package_groups)

    @property
    def subdir(self) -> str:
        """Repository sub-directory (platfrom architecture)."""
        return self._subdir

    def dump(self) -> Dict[str, Any]:
        """Converts data into a dictionary representation."""
        data: Dict[str, Any] = {}
        data['info'] = {'subdir': self.subdir}

        packages: Dict[str, Any] = {}
        conda_packages: Dict[str, Any] = {}
        for package in itertools.chain.from_iterable(self.values()):
            if package.is_conda():
                conda_packages[package.filename] = package.dump()
            else:
               packages[package.filename] = package.dump()

        data['packages'] = packages
        data['packages.conda'] = conda_packages
        data['removed'] = []
        data['repodata_version'] = self.VERSION

        return data

    def merge(self, other: RepoData) -> RepoData:
        if self.subdir != other.subdir:
            subdirs = ','.join([self.subdir, other.subdir])
            raise ValueError(f"Merged subdirs must match: {subdirs})")

        package_groups: Dict[str, List[PackageRecord]] = {}
        keys = set(self.keys()).union(other.keys())
        for key in keys:
            packages = set(self.get(key, [])) | set(other.get(key, []))
            package_groups[key] = sorted(packages, key=lambda pkg: pkg.filename)

        return RepoData(self.subdir, package_groups)


    def __contains__(self, key) -> bool:
        return key in self._package_groups.keys()

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return ((self.subdir==other.subdir) and
                    (self._package_groups==other._package_groups))

    def __getitem__(self, key) -> Iterable[PackageRecord]:
        return iter(self._package_groups[key])

    def __iter__(self) -> Iterator[str]:
        yield from self._package_groups.keys()

    def __len__(self) -> int:
        return len(self._package_groups.keys())

    def __repr__(self) -> str:
        return f'{type(self).__name__}({self.subdir!r}, ...)'
