![Conda](https://img.shields.io/conda/v/conda-forge/conda-replicate?label=conda-forge)
![GitHub](https://img.shields.io/github/license/cswartzvi/conda-replicate)


![# conda-synthesize](./assets/logo.png)

# What is this?
`conda-replicate` is a command line tool for creating and updating local mirrored anaconda channels.

### Notable features
* Uses the standard [match specification syntax](https://docs.conda.io/projects/conda-build/en/latest/resources/package-spec.html#package-match-specifications) to identify packages
* Resolves all necessary dependencies of specified packages
* Allows for channel evolution via direct updates or transferable patches
* Synchronizes upstream package hotfixes with local channels


### Does this violate Anaconda's terms-of-service?
Disclaimer: I am an analyst, not a lawyer. The Anaconda [terms-of-service](https://legal.anaconda.com/policies/en/?name=terms-of-service) expressly forbids mirroring of the default anaconda repository on [repo.anaconda.com](https://repo.anaconda.com/). However, as explained in a [post](https://conda-forge.org/blog/posts/2020-11-20-anaconda-tos/#:~:text=The%20TOS%20change%20does%20not,on%20repo.anaconda.com.) on the conda-forge blog, this does not apply to conda-forge or any other channel hosted on [anaconda.org](https://anaconda.org/). Therefore, `conda-replicate` uses conda-forge as it's default upstream channel. You are of course welcome to specify another channel, but please be respectful of Anaconda's terms-of-service and do not mirror the default anaconda repository.

# Installation
Due to dependencies on modern versions of `conda` (for searching) and `conda-build` (for indexing), `conda-replicate` is currently only available on conda-forge:

```
conda install conda-replicate --channel conda-forge --override-channels
```

# Usage
1. [Creating a local channel](#1-creating-a-local-channel)
2. [Updating an existing local channel](#2-updating-an-existing-local-channel)

### 1. Creating a local channel
Suppose that you want to mirror all of the conda-forge python 3.9 micro releases (3.9.1, 3.9.2, ...) in a local channel called `my-custom-channel`, this can be accomplished by simply running the `update` sub-command:

```
> conda-replicate update "python >=3.9,<3.10" --target ./my-custom-channel
```

Because the number of command line arguments can quickly get out of hand, it is recommended that you use a [configuration file](#configuration-file):

```yaml
# config.yml
channel: conda-forge
requirements:
  - python >=3.9,<3.10
```

With this configuration file saved as `config.yml` one can re-run the above command:

```
> conda-replicate update --config ./config.yaml --target ./my-custom-channel
```

Once either of these commands has finished you will have a fully accessible local channel that `conda` can use to install packages. For example you can do the following:

```
> conda create -n conda-replicate-test --channel ./my-custom-channel --override-channels -y

> conda activate conda-replicate-test

> python --version
Python 3.9.13

> conda list
# packages in environment at /path/to/Anaconda3/envs/conda-local-test-env:
#
# Name                    Version                   Build  Channel
bzip2                     1.0.8                h8ffe710_4    file:///path/to/my-custom-channel
ca-certificates           2022.6.15            h5b45459_0    file:///path/to/my-custom-channel
libffi                    3.4.2                h8ffe710_5    file:///path/to/my-custom-channel
libsqlite                 3.39.2               h8ffe710_1    file:///path/to/my-custom-channel
libzlib                   1.2.12               h8ffe710_2    file:///path/to/my-custom-channel
openssl                   3.0.5                h8ffe710_1    file:///path/to/my-custom-channel
pip                       22.2.2             pyhd8ed1ab_0    file:///path/to/my-custom-channel
python                    3.9.13       hcf16a7b_0_cpython    file:///path/to/my-custom-channel
python_abi                3.9                      2_cp39    file:///path/to/my-custom-channel
setuptools                65..0           py39hcbf5309_0     file:///path/to/my-custom-channel
sqlite                    3.39.2               h8ffe710_1    file:///path/to/my-custom-channel
tk                        8.6.12               h8ffe710_0    file:///path/to/my-custom-channel
tzdata                    2022c                h191b570_0    file:///path/to/my-custom-channel
ucrt                      10.0.20348.0         h57928b3_0    file:///path/to/my-custom-channel
vc                        14.2                 hb210afc_6    file:///path/to/my-custom-channel
vs2015_runtime            14.29.30037          h902a5da_6    file:///path/to/my-custom-channel
wheel                     0.37.1             pyhd8ed1ab_0    file:///path/to/my-custom-channel
xz                        5.2.6                h8d14728_0    file:///path/to/my-custom-channel
```

Notice that it appears our local channel has all of the direct and transitive dependencies for python 3.9.13. In fact, it has the direct and transitive dependencies for **all of the micro versions of python 3.9**. We can see a summary of these dependencies by using the `query` sub-command, which will query conda-forge and determine what packages are needed to satisfy the python 3.9 specification.

```
> conda-replicate query --config ./config.yaml

  Packages to add    (26)   Number   Size [MB]
 ──────────────────────────────────────────────
  python                    35          659.94
  pypy3.9                   16          469.51
  openssl                   19          147.41
  setuptools                111         141.61
  pip                       38           48.08
  vs2015_runtime            15           32.38
  sqlite                    20           24.89
  tk                        3            11.67
  ca-certificates           30            5.73
  zlib                      17            2.64
  certifi                   15            2.28
  tzdata                    15            1.91
  pyparsing                 24            1.58
  xz                        3             1.35
  ucrt                      1             1.23
  bzip2                     5             0.76
  expat                     2             0.74
  libsqlite                 1             0.65
  libzlib                   6             0.40
  packaging                 8             0.28
  wheel                     9             0.27
  libffi                    6             0.25
  vc                        14            0.17
  wincertstore              6             0.09
  six                       3             0.04
  python_abi                3             0.01
  Total                     425        1555.88
```

Note that the `query` sub-command is most commonly used when a  `target` is included in the configuration file (or on the command line via `--target`). When a `target` is specified, the `query` sub-command *will calculate results relative the given target channel*. This also applies to other `conda-replicate` sub-commands such as `update` and `patch`. We will make use of this when we update our local channel below, but for now, we want the examine the complete, non-relative, results of `query`.

As you can see the original update installed quite a few packages, and they take up quite a bit of space! This result may prompt a few questions.

#### How are dependencies determined?
`conda-replicate` uses the `conda.api` to recursively examine the dependencies of user-supplied "root" specifications (like `python>=3.9,<3.10` given above) and constructs a directed dependency graph. After this graph is completed, unsatisfied nodes (specifications that have no connected packages) are pruned. Additionally, nodes that have no possible connecting path to at least one of the root specifications are pruned as well. What is left are packages that satisfy either a root specification, a direct dependency of a root specification, or a transitive dependency further down the graph. Note that if a root specification is unsatisfied an `UnsatisfiedRequirementsError` exception is raised.

As a quick aside, you can use the `conda query --info` command to look at the dependencies of individual conda packages (where ⋮ indicates hidden output):

```
> conda search python==3.9.13 --info --channel conda-forge  --override-channels

⋮
python 3.9.13 hcf16a7b_0_cpython
--------------------------------
⋮
dependencies:
  - bzip2 >=1.0.8,<2.0a0
  - libffi >=3.4.2,<3.5.0a0
  - libzlib >=1.2.11,<1.3.0a0
  - openssl >=3.0.3,<4.0a0
  - sqlite >=3.38.5,<4.0a0
  - tk >=8.6.12,<8.7.0a0
  - tzdata
  - vc >=14.1,<15
  - vs2015_runtime >=14.16.27033
  - xz >=5.2.5,<5.3.0a0
  - pip

> conda search pip==22.2.2 -c conda-forge  --override-channels --info

⋮
pip 22.2.2 pyhd8ed1ab_0
-----------------------
⋮
dependencies:
  - python >=3.7
  - setuptools
  - wheel
```

#### Why are there so many "extra" packages?
Predominantly, board specifications are the usual the culprit for "extra" packages. Specifically, lets look at the following:
* 35 different packages of python. This can be traced back to our root specification of `python>=3.9,<3.10`. This specification includes not only all of the micro versions, but all of the conda-forge [builds](https://docs.conda.io/projects/conda-build/en/latest/resources/package-spec.html?highlight=build_number#package-metadata) for those packages as well.
* 111 packages of setuptools and 38 of pip. Python has a dependency on `pip` which in turn has a dependency on `setuptools` (both seen in the aside above). These specifications do not include version numbers and therefore match *all packages* of setuptools and pip.
* 16 packages of pypy3.9. In this case some packages depend on the `python_abi 3.9-2`. There is special build of this package that depends on the `pypy3.8` interpreter. Therefore, the relevant pypy packages (and their dependencies) are included in our local channel.

#### Can we exclude these "extra" packages?
Yes, by using `exclusions` in the configuration file (or `--exclude` on the command line option) . Let's assume that you are repeating the process of creating `my-custom-channel` from above. However instead of jumping right to the `update` sub-command you do the following:

1. Run the `query` sub-command in _summary_ mode (the default mode used above) to see the overall package distribution

      ```
      > conda-replicate query --config ./config.yaml
      ```

2. If we find some unexpected packages we can re-run `query` in _list_ mode to zero in on the individual version of those packages. As you can see below there is a wide range of package versions for python, pip, setuptools, pyp3.9.

    ```
    > python -m conda_local query --config ./config.yaml --output list

    Packages to add:
    ⋮
    pip-20.0.2-py_2.tar.bz2
    pip-20.1-pyh9f0ad1d_0.tar.bz2
    pip-20.1.1-py_1.tar.bz2
    ⋮
    pip-22.2-pyhd8ed1ab_0.tar.bz2
    pip-22.2.1-pyhd8ed1ab_0.tar.bz2
    pip-22.2.2-pyhd8ed1ab_0.tar.bz2
    ⋮
    pypy3.9-7.3.8-h1738a25_0.tar.bz2
    pypy3.9-7.3.8-h1738a25_1.tar.bz2
    pypy3.9-7.3.8-h1738a25_2.tar.bz2
    pypy3.9-7.3.8-hc3b0203_0.tar.bz2
    pypy3.9-7.3.8-hc3b0203_1.tar.bz2
    pypy3.9-7.3.8-hc3b0203_2.tar.bz2
    pypy3.9-7.3.9-h1738a25_0.tar.bz2
    pypy3.9-7.3.9-h1738a25_1.tar.bz2
    pypy3.9-7.3.9-h1738a25_2.tar.bz2
    pypy3.9-7.3.9-h1738a25_3.tar.bz2
    pypy3.9-7.3.9-h1738a25_4.tar.bz2
    pypy3.9-7.3.9-hc3b0203_0.tar.bz2
    pypy3.9-7.3.9-hc3b0203_1.tar.bz2
    pypy3.9-7.3.9-hc3b0203_2.tar.bz2
    pypy3.9-7.3.9-hc3b0203_3.tar.bz2
    pypy3.9-7.3.9-hc3b0203_4.tar.bz2
    ⋮
    python-3.9.0-h408a966_4_cpython.tar.bz2
    python-3.9.1-h7840368_0_cpython.tar.bz2
    ⋮
    python-3.9.12-hcf16a7b_1_cpython.tar.bz2
    python-3.9.13-h9a09f29_0_cpython.tar.bz2
    ⋮
    setuptools-49.6.0-py39h467e6f4_2.tar.bz2
    setuptools-49.6.0-py39hcbf5309_3.tar.bz2
    setuptools-57.4.0-py39h0d475fb_1.tar.bz2
    ⋮
    setuptools-65.1.1-py39hcbf5309_0.tar.bz2
    setuptools-65.2.0-py39h0d475fb_0.tar.bz2
    setuptools-65.3.0-py39hcbf5309_0.tar.bz2
    ⋮
    ```

3. Having identified the version ranges of theses packages we can refine our call to the `update` sub-command by tightening our root specification and making use of `exclusions` in the configuration file. The entire process is updatable, so we don't need to loss sleep over our ranges right now:

      ```yaml
      # config.yml
      channel: conda-forge
      requirements:
        - python >=3.9.8,<3.10  # updated line
      exclusions:
        - setuptools <=60.0     # new line
        - pip <=21.0            # new line
        - pypy3.9               # new line
      ```

      ```
       > conda-replicate query --config ./config.yml

       Packages to add    (21)   Number   Size [MB]
       ──────────────────────────────────────────────
       python                    14          258.60
       openssl                   14          117.20
       setuptools                53           69.28
       vs2015_runtime            15           32.38
       pip                       22           30.10
       sqlite                    10           12.51
       tk                        3            11.67
       ca-certificates           30            5.73
       tzdata                    15            1.91
       pyparsing                 24            1.58
       xz                        3             1.35
       ucrt                      1             1.23
       bzip2                     5             0.76
       libsqlite                 1             0.65
       libzlib                   6             0.40
       packaging                 8             0.28
       wheel                     9             0.27
       libffi                    6             0.25
       vc                        14            0.17
       six                       3             0.04
       python_abi                2             0.01
       Total                     230         546.38

      ```
   This brings the number of packages and overall size down to a more reasonable level.

4. Finally we can re-run the `update` sub-command (as we did above):

   ```
   conda-replicate update --config ./config.yaml --target ./my-custom-channel
   ```


It should be mentioned that sometimes the reasons for _why_ a package was included require a more detailed dependency investigation. In those cases calls to `conda search --info`,  `conda-replicate query --output json`, or as a last resort `conda-replicate query --debug`, are very useful.

### 2. Updating an existing local channel

Once a local channel has been created it can be updated at any time. Updates preform the following actions:
1. Add, delete, or revoke packages in response to changes in our specifications or the upstream channel

2. Synchronize local package hotfixes with those in the upstream channel

3. Refresh the package index in response to package and/or hotfix changes (via `conda_build.api`)

There are two ways that local channels can be updated, either *directly* or through *patches*. Lets examine both options starting from `my-custom-channel` in the previous section. We ended up with a configuration file that looked like the following:

```yaml
# config.yml
channel: conda-forge
requirements:
  - python >=3.9.8,<3.10
exclusions:
  - setuptools <=60.0
  - pip <=21.0
  - pypy3.9
```

Now, let's assume that after creating `my-custom-channel` we want to further tighten our python and setuptools requirements, and add a new requirement for `pydantic` (note that this example will only simulate changes to *our* specifications, not changes to upstream channel). We would also like to include the `target` field in the configuration file:

```yaml
#config.yml
channel: conda-forge
target: ./my-custom-channel   # new line
requirements:
  - python >=3.9.10,<3.10     # updated line
  - pydantic                  # new line
exclusions:
  - setuptools <=62.0         # updated line
  - pip <=21.0
  - pypy3.9
```

Remembering the lessons from the last section, we first run the `query` sub-command. Because our new configuration file defines a `target`, we we will see the results of the query *relative* `my-custom-channel`. This effectively describes what packages will be added and removed when we run the update:

```
> conda-replicate query --config ./config.yml

  Packages to add    (4)   Number   Size [MB]
 ─────────────────────────────────────────────
  pydantic                 17           11.87
  typing_extensions        10            0.28
  typing-extensions        10            0.08
  dataclasses              3             0.02
  Total                    40           12.25


  Packages to remove (2)   Number   Size [MB]
 ─────────────────────────────────────────────
  python                   2            36.44
  setuptools               28           33.54
  Total                    30           69.98
```

#### How do we perform a direct update?

At this point performing the direct update is simple:

```
> conda-replicate update --config ./config.yml
```

#### How do we perform a patched update?

Patched updates are accomplished by using two different sub-commands: `patch` and `merge`. The first of these, `patch`, works similar to `update`, in that it will calculate the packages to add or remove relative our target. It will then download the packages and hotfixes into a *separate patch directory* (controlled by the `--parent` and `--name` command line options). It is important to note that the package index of the patch directory **is not updated** and therefore **cannot** be used by `conda` to install packages!

```
> conda-replicate patch --config ./config.yml --parent ./patch-archive --name patch_20220824
```

This patch directory can then be merged into an existing channel using the `merge` sub-command. The merging process not only copies the packages and modified hotfixes form the patch directory, but it also updates the package index. Note that those packages `patch` determined should be removed are passed to `merge` via the hotfixes.

```
> conda-replicate merge ./patch-archive/patch_20220824 my-air-gapped-channel
```

The `patch` and `merge` commands are particularly well suited for updating air-gapped systems, however there are some things to consider:

1. You must be able to transfer files to the air-gapped system from a network facing system (via a bridge or manual drive).
2. You need to maintain a parallel channel on your network facing system that is used generate the patches.
3. The very first transfer to the air-gapped system *must be an indexed conda channel*. This means that you need to use the `update` sub-command to create a channel on your network facing system and then transfer the entire channel to the air gapped system. All subsequent transfers can be updated via the `patch` and `merge` sub-commands.
4. Your configuration needs to include `conda-replicate` as a requirement. If not, you will not be able install `conda-replicate` on the air-gapped system, which means you cannot run the `merge` sub-command.

## Commands
The following commands are available in `conda-replicate`:

#### query
```
 Usage: conda-replicate query [OPTIONS] [REQUIREMENTS]...

 Search an upstream channel for the specified package REQUIREMENTS and report results.

  • Resulting packages are reported to the user in the specified output form (see --output)
  • Include both direct and transitive dependencies of required packages

 Package requirement notes:

  • Requirements are constructed using the anaconda package query syntax
  • Unsatisfied requirements will raise an error by default (see --no-validate)
  • Requirements specified on the command line augment those specified in a configuration file

┌─ Options ────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                                  │
│  --channel   -c   TEXT     Upstream anaconda channel. Can be specified using the canonical       │
│                            channel name on anaconda.org (conda-forge), a fully qualified URL     │
│                            (https://conda.anaconda.org/conda-forge/), or a local directory       │
│                            path.                                                                 │
│                            [default: conda-forge]                                                │
│                                                                                                  │
│  --target    -t   TEXT     Target anaconda channel. When specified, this channel will act as a   │
│                            baseline for the package search process - only package differences    │
│                            (additions or deletions) will be reported to the user.                │
│                                                                                                  │
│  --exclude        TEXT     Packages excluded from the search process. Specified using the        │
│                            anaconda package query syntax. Multiple options may be passed at one  │
│                            time.                                                                 │
│                                                                                                  │
│  --dispose        TEXT     Packages that are used in the search process but not included in the  │
│                            final results. Specified using the anaconda package query syntax.     │
│                            Multiple options may be passed at one time.                           │
│                                                                                                  │
│  --subdir         SUBDIR   Selected platform sub-directories. Multiple options may be passed at  │
│                            one time. Allowed values: {linux-32, linux-64, linux-aarch64,         │
│                            linux-armv6l, linux-armv7l, linux-ppc64, linux-ppc64le, linux-s390x,  │
│                            noarch, osx-64, osx-arm64, win-32, win-64, zos-z}.                    │
│                            [default: win-64, noarch]                                             │
│                                                                                                  │
│  --output         OUTPUT   Specifies the format of the search results. Allowed values: {table,   │
│                            list, json}.                                                          │
│                                                                                                  │
│  --config         FILE     Path to the yaml configuration file.                                  │
│                                                                                                  │
│  --quiet                   Quite mode. suppress all superfluous output.                          │
│                                                                                                  │
│  --debug     -d            Enable debugging logs. Can be repeated to increase log level          │
│                                                                                                  │
│  --help                    Show this message and exit.                                           │
│                                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```
#### update
```
 Usage: conda-replicate update [OPTIONS] [REQUIREMENTS]...

 Update a local channel based on specified upstream package REQUIREMENTS.

  • Packages are downloaded or removed from the local channel prior to re-indexing
  • Includes both direct and transitive dependencies of required packages
  • Includes update to the platform specific patch instructions (hotfixes)

 Package requirement notes:

  • Requirements are constructed using the anaconda package query syntax
  • Unsatisfied requirements will raise an error by default (see --no-validate)
  • Requirements specified on the command line augment those specified in a configuration file

┌─ Options ────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                                  │
│  *   --target    -t   TEXT     Local anaconda channel where the update will occur. If this       │
│                                local channel already exists it will act as a baseline for the    │
│                                package search process - only package differences (additions or   │
│                                deletions) will be updated.                                       │
│                                [required]                                                        │
│                                                                                                  │
│      --channel   -c   TEXT     Upstream anaconda channel. Can be specified using the canonical   │
│                                channel name on anaconda.org (conda-forge), a fully qualified     │
│                                URL (https://conda.anaconda.org/conda-forge/), or a local         │
│                                directory path.                                                   │
│                                [default: conda-forge]                                            │
│                                                                                                  │
│      --exclude        TEXT     Packages excluded from the search process. Specified using the    │
│                                anaconda package query syntax. Multiple options may be passed at  │
│                                one time.                                                         │
│                                                                                                  │
│      --dispose        TEXT     Packages that are used in the search process but not included in  │
│                                the final results. Specified using the anaconda package query     │
│                                syntax. Multiple options may be passed at one time.               │
│                                                                                                  │
│      --subdir         SUBDIR   Selected platform sub-directories. Multiple options may be        │
│                                passed at one time. Allowed values: {linux-32, linux-64,          │
│                                linux-aarch64, linux-armv6l, linux-armv7l, linux-ppc64,           │
│                                linux-ppc64le, linux-s390x, noarch, osx-64, osx-arm64, win-32,    │
│                                win-64, zos-z}.                                                   │
│                                [default: win-64, noarch]                                         │
│                                                                                                  │
│      --config         FILE     Path to the yaml configuration file.                              │
│                                                                                                  │
│      --quiet                   Quite mode. suppress all superfluous output.                      │
│                                                                                                  │
│      --debug     -d            Enable debugging logs. Can be repeated to increase log level      │
│                                                                                                  │
│      --help                    Show this message and exit.                                       │
│                                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

#### patch
```
 Usage: conda-replicate patch [OPTIONS] [REQUIREMENTS]...

 Create a patch from an upstream channel based on specified package REQUIREMENTS.

  • Packages are downloaded to a local patch directory (see --name and --parent)
  • Patches can be merged into existing local channels (see merge sub-command)
  • Includes both direct and transitive dependencies of required packages
  • Includes update to the platform specific patch instructions (hotfixes)

 Package requirement notes:

  • Requirements are constructed using the anaconda package query syntax
  • Unsatisfied requirements will raise an error by default (see --no-validate)
  • Requirements specified on the command line augment those specified in a configuration file

┌─ Options ────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                                  │
│  --target    -t   TEXT     Target anaconda channel. When specified, this channel will act as a   │
│                            baseline for the package search process - only package differences    │
│                            (additions or deletions) will be included in the patch.               │
│                                                                                                  │
│  --name           TEXT     Name of the patch directory. [patch_%Y%m%d_%H%M%S]                    │
│                                                                                                  │
│  --parent         PATH     Parent directory of the patch. [current directory]                    │
│                                                                                                  │
│  --channel   -c   TEXT     Upstream anaconda channel. Can be specified using the canonical       │
│                            channel name on anaconda.org (conda-forge), a fully qualified URL     │
│                            (https://conda.anaconda.org/conda-forge/), or a local directory       │
│                            path.                                                                 │
│                            [default: conda-forge]                                                │
│                                                                                                  │
│  --exclude        TEXT     Packages excluded from the search process. Specified using the        │
│                            anaconda package query syntax. Multiple options may be passed at one  │
│                            time.                                                                 │
│                                                                                                  │
│  --dispose        TEXT     Packages that are used in the search process but not included in the  │
│                            final results. Specified using the anaconda package query syntax.     │
│                            Multiple options may be passed at one time.                           │
│                                                                                                  │
│  --subdir         SUBDIR   Selected platform sub-directories. Multiple options may be passed at  │
│                            one time. Allowed values: {linux-32, linux-64, linux-aarch64,         │
│                            linux-armv6l, linux-armv7l, linux-ppc64, linux-ppc64le, linux-s390x,  │
│                            noarch, osx-64, osx-arm64, win-32, win-64, zos-z}.                    │
│                            [default: win-64, noarch]                                             │
│                                                                                                  │
│  --config         FILE     Path to the yaml configuration file.                                  │
│                                                                                                  │
│  --quiet                   Quite mode. suppress all superfluous output.                          │
│                                                                                                  │
│  --debug     -d            Enable debugging logs. Can be repeated to increase log level          │
│                                                                                                  │
│  --help                    Show this message and exit.                                           │
│                                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```
#### merge
```
 Usage: conda-replicate merge [OPTIONS] PATCH CHANNEL

 Merge a PATCH into a local CHANNEL and update the local package index.

┌─ Options ────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                                  │
│  --quiet           Quite mode. suppress all superfluous output.                                  │
│                                                                                                  │
│  --debug   -d      Enable debugging logs. Can be repeated to increase log level                  │
│                                                                                                  │
│  --help            Show this message and exit.                                                   │
│                                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```
#### index
```
 Usage: conda-replicate index [OPTIONS] CHANNEL

 Update the package index of a local CHANNEL.

┌─ Options ────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                                  │
│  --quiet           Quite mode. suppress all superfluous output.                                  │
│                                                                                                  │
│  --debug   -d      Enable debugging logs. Can be repeated to increase log level                  │
│                                                                                                  │
│  --help            Show this message and exit.                                                   │
│                                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Configuration File

The YAML configuration file can be used to specify any of the following:

* **channel** (string)
* **target** (string)
* **requirements** (list)
* **exclusions** (list)
* **disposables** (list)
* **subdirs** (list)

## Thanks
* Folder icons created by Freepik - [Flaticon](https://www.flaticon.com/free-icons/folder)
