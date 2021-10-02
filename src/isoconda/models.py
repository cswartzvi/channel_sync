# -*- coding: utf-8 -*-

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class PackageRecord(BaseModel):
    """Package record for an individual anaconda package.

    See the following for more details:
    1. The anaconda package metadata specification:
    https://docs.conda.io/projects/conda/en/latest/user-guide/concepts/pkg-specs.html#package-metadata  # noqa
    2. The PackageRecord object from github:
    https://github.com/conda/conda/blob/master/conda/models/records.py

    Attributes:
        name: Common name of the package (installable name).
        file_name: Name of the file on the anaconda server.
        version: Complete version specification string.
        build: build specification (example: python version)
        build_number: Build number (for multiple builds of the same version).
        md5: md5 string associated with the package file.
        sha256: sha256 string associated with the package file.
        depends: A list of package dependencies (optional).
        timestamp: Creation date of the package (optional).
        license: Package license identifier (optional).
    """

    name: str
    file_name: str
    version: str
    build: str
    build_number: int
    md5: str
    sha256: str
    depends: List[str] = Field(default_factory=list)
    timestamp: Optional[datetime]
    subdir: Optional[str]
    license: Optional[str]

    class Config:
        allow_mutation = False

    @property
    def _key(self):
        """Primary key for the package record (does not depend on file name)."""
        return (self.name, self.version, self.build, self.build_number)

    def __hash__(self) -> int:
        return hash(self._key)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self._key == other._key
