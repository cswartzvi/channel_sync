"""Contains the models fro the representation of Anaconda repositories."""
from __future__ import annotations
import collections
import copy
import itertools
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

import isoconda.errors as errors
import isoconda.matching as matching

PYTHON = 'python'


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
    def is_conda(self) -> bool:
        """Returns True if the package is in the conda format."""
        return self._conda

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
        """The timestamp of the package. Defaults to zero rather than None."""
        return self._data.get('timestamp', 0)

    @property
    def version(self) -> str:
        """The package version."""
        return self._data['version']

    def dump(self) -> Dict[str, Any]:
        """Converts data into a dictionary representation."""
        return copy.deepcopy(self._data)

    def __eq__(self, other):
        return self._pkey == other._pkey

    def __hash__(self):
        return self._hash

    def __repr__(self):
        return f'{type(self).__name__}(filename={self.filename!r}, data={self._data!r})'


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
            raise errors.InvalidRepo(f'Unknown repodata version: {repodata_version}')

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

    def difference(self, other: RepoData) -> RepoData:
        """Takes the difference of the this repository with another.

        Args:
            repodata: Second Anaconda repository object.

        Returns:
            Filtered anaconda repository.
        """
        groups: Dict[str, Iterable[PackageRecord]] = dict(self.items())  # all packages
        for name, packages in self.items():
            if name in other:
                groups[name] = sorted(set(packages) - set(other[name]),
                                      key=lambda p: p.filename)
            else:
                groups[name] = list(packages)

        return RepoData(self.subdir, groups)

    def dump(self) -> Dict[str, Any]:
        """Converts data into a dictionary representation."""
        data: Dict[str, Any] = {}
        data['info'] = {'subdir': self.subdir}

        packages: Dict[str, Any] = {}
        conda_packages: Dict[str, Any] = {}
        for package in itertools.chain.from_iterable(self._package_groups.values()):
            if package.is_conda:
                conda_packages[package.filename] = package.dump()
            else:
                packages[package.filename] = package.dump()

        data['packages'] = packages
        data['packages.conda'] = conda_packages
        data['removed'] = []
        data['repodata_version'] = self.VERSION

        return data

    def filter_matches(self, strings: Iterable[str]) -> RepoData:
        """Filters out all matching packages from an Anaconda repository.

        Args:
            repodata: An Anaconda repository object.
            strings: An iterable of Anaconda package specification strings.

        Returns:
            Filtered anaconda repository.
        """
        specs = matching.create_specs(strings)
        groups: Dict[str, Iterable[PackageRecord]] = dict(self.items())  # all packages

        for spec in specs:
            packages: List[PackageRecord] = []
            for package in groups.get(spec.name, []):
                if not matching.match_spec(package.name, package.version, spec):
                    packages.append(package)
            if packages:
                groups[spec.name] = packages
            else:
                groups.pop(spec.name, '')

        return RepoData(self.subdir, groups)

    def filter_mismatches(self, strings: Iterable[str]) -> RepoData:
        """Filters out all non-matching packages from an Anaconda repository.

        Args:
            repodata: An Anaconda repository object.
            strings: An iterable of Anaconda package specification strings.

        Returns:
            Filtered anaconda repository.
        """
        if not strings:
            return self

        groups: Dict[str, List[PackageRecord]] = collections.defaultdict(list)

        for spec in matching.create_specs(strings):
            for package in self.get(spec.name, []):
                if matching.match_spec(package.name, package.version, spec):
                    groups[spec.name].append(package)
        return type(self)(self.subdir, groups)

    def filter_python(self, versions: Iterable[float]) -> RepoData:
        """Filters an Anaconda repository based on python versions.

        Individual python interperter packages are filtered along with packages with
        python interperter dependencies.

        Args:
            repodata: An Anaconda repository object.
            versions: An iterable of python versions (as floats).

        Returns:
            Filtered anaconda repository.
        """

        if not versions:
            return self

        groups: Dict[str, List[PackageRecord]] = collections.defaultdict(list)
        specs = matching.create_specs(f'{PYTHON} {version:0.1f}*' for version in versions)
        version_strings = [str(version) for version in versions]

        for package in itertools.chain.from_iterable(self.values()):
            include = True
            if package.name == PYTHON:  # Python interpreters
                include = matching.match_specs(package.name, package.version, specs)
            else:  # Python dependencies
                for depend in matching.create_specs(package.depends):
                    if depend.name == PYTHON:
                        include = matching.match_versions(version_strings, depend)
                        break
            if include:
                groups[package.name].append(package)

        return type(self)(self.subdir, groups)

    def merge(self, other: RepoData) -> RepoData:
        """Merges current repository with another repository."""
        if self.subdir != other.subdir:
            subdirs = ','.join([self.subdir, other.subdir])
            raise ValueError(f"Merged subdirs must match: {subdirs})")

        package_groups: Dict[str, List[PackageRecord]] = {}
        keys = set(self.keys()) | set(other.keys())
        for key in sorted(keys):
            packages = set(self.get(key, [])) | set(other.get(key, []))
            package_groups[key] = sorted(packages, key=lambda pkg: pkg.filename)

        return RepoData(self.subdir, package_groups)

    def __contains__(self, key) -> bool:
        return key in self._package_groups.keys()

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return ((self.subdir == other.subdir) and
                    (self._package_groups == other._package_groups))
        return False

    def __getitem__(self, key) -> Iterable[PackageRecord]:
        return iter(self._package_groups[key])

    def __iter__(self) -> Iterator[str]:
        yield from self._package_groups.keys()

    def __len__(self) -> int:
        return len(self._package_groups.keys())

    def __repr__(self) -> str:
        return f'{type(self).__name__}(subdir={self.subdir!r}, package_groups=...)'
