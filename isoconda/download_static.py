import concurrent.futures
import functools
import pathlib
import threading
import time

from conda.exports import PackageRecord
import requests
from tqdm import tqdm

BLOCK_SIZE = 1024
# thread_local = threading.local()

def join_url(parts):
    urls = []
    for part in parts:
        urls.append(part.rstrip('/'))
    return '/'.join(urls)


def download_package(location, package, session):
    package_url = join_url([package.url, package.fn])
    subdir = pathlib.Path(location) / package.subdir
    subdir.mkdir(parents=True, exist_ok=True)
    filepath = subdir / package.fn
    with session.get(package_url, stream=True) as response:
        with open(filepath , 'wb') as download:
            for data in response.iter_content(BLOCK_SIZE):
                download.write(data)


def download_all_packages(location, url):
    packages = get_packages(url)
    with requests.Session() as session:
        for package in tqdm(packages, ascii=True, desc=url):
            download_package(location, package, session)


def get_packages(url):
    repodata_url = join_url([url, 'repodata.json'])
    repodata = requests.get(repodata_url).json()
    packages = set()
    for key in ['packages', 'packages.conda']:
        for fn, data in repodata[key].items():
            packages.add(PackageRecord(fn=fn, url=url, **data))
    return sorted(packages, key=lambda package: package.name)


if __name__ == "__main__":
    start_time = time.time()
    url = "https://repo.anaconda.com/pkgs/main/noarch/"
    download_all_packages("./test_channel", url)
    duration = time.time() - start_time
    print(f"Downloaded in {duration} seconds")
