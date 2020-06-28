
from isoconda.channel import ChannelGroupInfo

NAME = 'numpy'
GROUP_DATA = {
    'activate.d': False,
    'binary_prefix': True,
    'deactivate.d': False,
    'description': 'NumPy is the fundamental package needed for scientific computing with Python.',
    'dev_url': 'https://github.com/numpy/numpy',
    'doc_source_url': None,
    'doc_url': 'https://docs.scipy.org/doc/numpy-1.18.5/reference/',
    'home': 'http://numpy.scipy.org/',
    'icon_hash': None,
    'icon_url': None,
    'identifiers': None,
    'keywords': None,
    'license': 'BSD 3-Clause',
    'post_link': False,
    'pre_link': False,
    'pre_unlink': False,
    'recipe_origin': None,
    'run_exports': {},
    'source_git_url': 'https://github.com/numpy/numpy',
    'source_url': 'https://pypi.io/packages/source/n/numpy/numpy-1.15.3.zip',
    'subdirs': [
        'linux-32',
        'linux-64',
        'linux-ppc64le',
        'osx-64',
        'win-32',
        'win-64'
    ],
    'summary': 'Array processing for numbers, strings, records, and objects.',
    'tags': None,
    'text_prefix': True,
    'timestamp': 1593012453,
    'version': '1.18.5'
}


def test_dump_returns_identical_dictionary():
    info = ChannelGroupInfo(NAME, GROUP_DATA)
    assert info.dump() == GROUP_DATA


def test_tarball_package_record_parsing():
    info = ChannelGroupInfo(NAME, GROUP_DATA)
    assert info.name == NAME
    assert info.timestamp == GROUP_DATA['timestamp']
    assert info.version == GROUP_DATA['version']


def test_package_hashes_do_not_include_file_extension():
    info1 = ChannelGroupInfo(NAME, GROUP_DATA)
    info2 = ChannelGroupInfo(NAME, GROUP_DATA)
    assert info1 == info2
    assert hash(info1) == hash(info2)
