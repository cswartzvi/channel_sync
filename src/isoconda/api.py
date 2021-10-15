# -*- coding: utf-8 -*-

from collections import defaultdict
from urllib.parse import urljoin

import requests

from isoconda._typing import Grouping
from isoconda.models import PackageRecord


def fetch_packages(url: str) -> Grouping[PackageRecord]:
    """Fetches package records from an anaconda repository url.

    Args:
        url: Anaconda packages repository url (where repodata.json resides).

    Returns:
        Package record objects grouped by package name.
    """
    grouped = defaultdict(set)
    repodata_url = urljoin(url, "repodata.json")
    data = requests.get(repodata_url).json()
    for file_name, package_data in data["packages"].items():
        record = PackageRecord(file_name=file_name, **package_data)
        grouped[record.name].add(record)
    return grouped
