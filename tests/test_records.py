
from isoconda.repo import PackageRecord

NAME_CONDA = 'numpy-1.9.3-py37hd5b3723_7.conda'
NAME_TARBALL = 'numpy-1.9.3-py37hd5b3723_7.tar.bz2'
PACKAGE_DATA = {
    'build': 'py37hd5b3723_7',
    'build_number': 7,
    'depends': [
        'icc_rt >=16.0.4',
        'numpy-base 1.9.3 py37h5c71026_7',
        'python >=3.7,<3.8.0a0',
        'vc 14.*'
    ],
    'license': 'BSD 3-Clause',
    'md5': '6e1059ab90013eb7c3f6587cb7dad3ea',
    'name': 'numpy',
    'sha256': '65d3642589a6ab008941d52b4671ff4a58b8f83a145723e44c15d2774b3553fa',
    'size': 10469,
    'subdir': 'win-64',
    'timestamp': 1530551215747,
    'version': '1.9.3'
}


def test_dump_returns_identical_dictionary():
    package = PackageRecord(NAME_TARBALL, PACKAGE_DATA)
    assert package.dump() == PACKAGE_DATA


def test_tarball_package_record_parsing():
    package = PackageRecord(NAME_TARBALL, PACKAGE_DATA)
    assert package.filename == NAME_TARBALL
    assert not package.is_conda
    assert package.build == PACKAGE_DATA['build']
    assert package.build_number == PACKAGE_DATA['build_number']
    assert package.depends == PACKAGE_DATA['depends']
    assert package.name == PACKAGE_DATA['name']
    assert package.sha256 == PACKAGE_DATA['sha256']
    assert package.subdir == PACKAGE_DATA['subdir']
    assert package.timestamp == PACKAGE_DATA['timestamp']
    assert package.version == PACKAGE_DATA['version']



def test_conda_package_record_parsing():
    package = PackageRecord(NAME_CONDA, PACKAGE_DATA)
    assert package.filename == NAME_CONDA
    assert package.is_conda
    assert package.build == PACKAGE_DATA['build']
    assert package.build_number == PACKAGE_DATA['build_number']
    assert package.depends == PACKAGE_DATA['depends']
    assert package.name == PACKAGE_DATA['name']
    assert package.sha256 == PACKAGE_DATA['sha256']
    assert package.subdir == PACKAGE_DATA['subdir']
    assert package.timestamp == PACKAGE_DATA['timestamp']
    assert package.version == PACKAGE_DATA['version']



def test_package_hashes_do_not_include_file_extension():
    package = PackageRecord(NAME_TARBALL, PACKAGE_DATA)
    package_conda = PackageRecord(NAME_CONDA, PACKAGE_DATA)
    assert package == package_conda
    assert hash(package) == hash(package_conda)
