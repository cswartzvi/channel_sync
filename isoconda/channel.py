

class ChannelGroupInfo:
    """Information realted to a group of packages in a Anaconda channel.

    Refers directly to elements in the channeldata.json sub-dictionaries: 'packages'.
    Channel groups are developed for use with the ``conda`` executable. The structure of
    these groups are dictated by the Anaconda organization and therefore are subject to
    change. In order to minimize breaking changes, this class only interacts with a small
    number of records fields and propagates all other fields when saving.
    """

    def __init__(self, name: str, data: Dict[str, Any]):
        """Initialize object instance from record data.

        Args:
            filename: Package filename (on disk or as a download)
            data: Dictionary representation of record fields.
        """