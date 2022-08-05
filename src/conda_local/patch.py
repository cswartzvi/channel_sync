import hashlib
import json
import tarfile
from pathlib import Path
from typing import Iterable, Optional

import requests

from conda_local import CondaLocalException
from conda_local.group import groupby
from conda_local.models import PATCH_INSTRUCTIONS_FILE
from conda_local.models.channel import CondaChannel
from conda_local.models.package import CondaPackage


def fetch_package(patch: Path, package: CondaPackage) -> None:
    response = requests.get(package.url)
    path = patch / package.subdir / package.fn

    if path.exists():
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() == package.sha256:
            return

    data = response.content

    if len(data) != package.size:
        raise BadPackageDownload(f"{package.fn} has incorrect size")
    if package.sha256 != hashlib.sha256(data).hexdigest():
        raise BadPackageDownload(f"{package.fn} has incorrect sha256")

    path.parent.mkdir(exist_ok=True, parents=True)
    with path.open("wb") as file:
        file.write(data)


def create_patch_instructions(
    patch: Path,
    subdir: str,
    source: Optional[CondaChannel] = None,
):
    path = patch / subdir / PATCH_INSTRUCTIONS_FILE
    path.parent.mkdir(exist_ok=True, parents=True)

    if source:
        data = source.read_patch_instructions(subdir)
    else:
        data = {}

    with path.open("wt") as file:
        json.dump(data, file, indent=2)


def update_patch_instructions(patch: Path, removals: Iterable[CondaPackage]) -> None:
    removals_by_subdir = groupby(removals, lambda pkg: pkg.subdir)

    for subdir, packages in removals_by_subdir.items():
        path = patch / subdir / PATCH_INSTRUCTIONS_FILE
        path.parent.mkdir(exist_ok=True, parents=True)

        with path.open("rt") as file:
            data = json.load(file)
        data.get("remove", []).extend(package.fn for package in packages)

        with path.open("wt") as file:
            json.dump(data, file, indent=2)


def create_patch_generator(patch: Path) -> None:
    tarball = patch / "patch_generator.tar.bz2"
    tarball.parent.mkdir(exist_ok=True, parents=True)

    with tarfile.open(tarball, "w:bz2") as tar:
        for instructions in patch.glob("**/" + PATCH_INSTRUCTIONS_FILE):
            tar.add(instructions, arcname=instructions.relative_to(patch))


def merge_patch(patch: Path, channel: CondaChannel) -> None:
    pass


class BadPackageDownload(CondaLocalException):
    pass
