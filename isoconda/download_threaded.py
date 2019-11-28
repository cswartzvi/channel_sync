from concurrent.futures import as_completed, ThreadPoolExecutor
import functools
import pathlib
import threading
import time

from conda.exports import PackageRecord
import requests
from tqdm import tqdm

BLOCK_SIZE = 1024 * 1024
thread_local = threading.local()


def get_session():
    if not hasattr(thread_local, "session"):
        thread_local.session = requests.Session()
    return thread_local.session


def download_package(location, package):
    package_url = join_url([package.url, package.fn])
    subdir = pathlib.Path(location) / package.subdir
    subdir.mkdir(parents=True, exist_ok=True)
    filepath = subdir / package.fn
    session = get_session()
    with session.get(package_url, stream=True) as response:
        with open(filepath , 'wb') as download:
            for data in response.iter_content(BLOCK_SIZE):
                download.write(data)


def download_all_packages(location, url):
    packages = get_packages(url)
    downloader = functools.partial(download_package, location)
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(downloader, p) for p in packages]
        for _ in tqdm(as_completed(futures), ascii=True, desc=url):
            pass


def get_packages(url):
    repodata_url = join_url([url, 'repodata.json'])
    repodata = requests.get(repodata_url).json()
    packages = set()
    for key in ['packages', 'packages.conda']:
        for fn, data in repodata[key].items():
            packages.add(PackageRecord(fn=fn, url=url, **data))
    return sorted(packages, key=lambda package: package.name)


def join_url(parts):
    urls = []
    for part in parts:
        urls.append(part.rstrip('/'))
    return '/'.join(urls)


if __name__ == "__main__":
    start_time = time.time()
    url = "https://repo.anaconda.com/pkgs/main/noarch/"
    download_all_packages("./test_channel2", url)
    duration = time.time() - start_time
    print(f"Downloaded in {duration} seconds")
