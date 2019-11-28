# import itertools

from isoconda.repo import CondaRepo


SIZES = {'B': 1, 'KB': 10 ** 3, 'MB': 10 ** 6, 'GB': 10 ** 9}


class TestRepo:
    def test_get_packages(self):
        repo = CondaRepo('https://repo.continuum.io/pkgs/main/win-64/repodata.json')
        assert len(list(repo.packages())) > 0

    def test_get_packages_size(self):
        repo = CondaRepo('https://repo.continuum.io/pkgs/main/win-64/repodata.json')
        assert sum(package.size for package in repo.packages()) > 0

    # repo.save("./temp.out")
    # packages = repo.get_packages(python_versions=[3.7], use_conda_files=True)
    # total_size = 0
    # for file_name, package in packages:
    #     total_size += package.size
    #     if package.name == 'python':
    #         print(f'{package.name}-{package.version}')
    # print(f"Total size: {total_size / SIZES['GB']:.2f} GB")